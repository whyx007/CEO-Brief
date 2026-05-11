#!/usr/bin/env python3
"""
中科天塔竞情分析周报 — CrewAI + DeepSeek 智能体
==================================================

搜索引擎: SearXNG + 百度新闻 + DuckDuckGo + 政采网定向
LLM:      DeepSeek

启动方式:
    1. cp .env.example .env  (填入 API Key)
    2. pip install -r requirements.txt
    3. python main.py

输出目录: output/<日期>_weekly/
    - CEO_OnePager.md        CEO一页式摘要
    - TOP15_Competitors.md   TOP15详情卡片
    - raw_data.json          原始数据
"""

import json
import logging
import os
import re
import sys
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from crewai import Crew, Process

# ──────────────────────────────────────
# 本地模块
# ──────────────────────────────────────
from config import OUTPUT_DIR, WINDOW_LABEL, PDF_NAME, OUTPUT_FORMAT, TZ, REPORT_END
from utils.scoring import parse_score, sort_cards_by_score
from checkpoint_manager import check_and_prompt_resume
from resumable_executor import should_skip_execution, save_crew_result

from agents import (
    intelligence_scout,
    talent_analyst,
    market_analyst,
    tech_analyst,
    bidding_funding_analyst,
    policy_analyst,
    ceo_advisor,
)

from tasks import (
    task_discover,
    task_talent,
    task_market,
    task_tech,
    task_bidding_funding,
    task_policy,
    task_global_tech,
    task_scoring,
    task_report,
)

from utils.report_renderer import (
    render_ceo_onepager,
    render_top15_cards,
    save_reports,
)

# helper to normalize data for the final report
from utils.report_renderer import prepare_report_data_for_render
from utils.json_parser import extract_json
from utils.pdf_generator import generate_pdf_from_markdown

# ──────────────────────────────────────
# 假 URL 过滤
# ──────────────────────────────────────
_FAKE_URL_PATTERNS = re.compile(
    r'https?://(www\.)?example\.com[^\s\]）)]*'
    r'|https?://placeholder[^\s\]）)]*'
    r'|https?://[^\s\]）)]*/(placeholder|fake|dummy|test-url|no-url)[^\s\]）)]*',
    re.IGNORECASE,
)

def _strip_fake_urls(md: str) -> str:
    """
    从 Markdown 报告中删除含假 URL 的参考文献条目，
    并同时删除正文中对应的引用标记 [N]。
    """
    if not md:
        return md

    lines = md.splitlines()
    fake_ref_nums: set[str] = set()
    clean_lines: list[str] = []

    # 第一遍：找出参考文献区域里含假 URL 的编号，跳过这些行
    for line in lines:
        # 参考文献行格式：[N] 来源 - URL - 日期
        ref_match = re.match(r'^\[(\d+)\]\s+', line)
        if ref_match and _FAKE_URL_PATTERNS.search(line):
            fake_ref_nums.add(ref_match.group(1))
            logging.getLogger(__name__).warning(
                "过滤假URL参考文献: %s", line[:120]
            )
            continue
        clean_lines.append(line)

    if not fake_ref_nums:
        return md

    # 第二遍：从正文中删除对应的引用标记 [N]
    result_lines: list[str] = []
    pattern = re.compile(
        r'\s*\[(' + '|'.join(re.escape(n) for n in fake_ref_nums) + r')\]'
    )
    for line in clean_lines:
        result_lines.append(pattern.sub('', line))

    logging.getLogger(__name__).info(
        "已过滤 %d 条假URL参考文献，编号: %s",
        len(fake_ref_nums), sorted(fake_ref_nums, key=int),
    )
    return '\n'.join(result_lines)

# ──────────────────────────────────────
# Logging & Console
# ──────────────────────────────────────
# 窗口外日期过滤
# ──────────────────────────────────────
from config import REPORT_START, REPORT_END

# 匹配参考文献行末尾的日期，格式：YYYY-MM-DD 或 YYYY-04-DD 等
_REF_DATE_RE = re.compile(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*$')

def _parse_ref_date(date_str: str):
    """把 YYYY-MM-DD 或 YYYY/MM/DD 解析为 date，失败返回 None"""
    from datetime import date
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None

def _strip_out_of_window(md: str) -> str:
    """
    从 Markdown 报告中删除参考文献区域里日期明显超出报告窗口的条目，
    并同时删除正文中对应的引用标记 [N]。

    策略：只过滤日期早于窗口开始 30 天以上的条目（政策/行业背景文件豁免），
    以及日期晚于窗口结束的条目。无日期的条目一律保留。
    """
    if not md:
        return md

    from datetime import timedelta
    win_start = REPORT_START.date()
    win_end = REPORT_END.date()
    # 宽松下界：窗口开始前 30 天内的引用（如本周前几天的新闻）也保留
    loose_start = win_start - timedelta(days=30)

    lines = md.splitlines()
    out_of_window_nums: set[str] = set()
    clean_lines: list[str] = []

    for line in lines:
        ref_match = re.match(r'^\[(\d+)\]\s+', line)
        if ref_match:
            date_match = _REF_DATE_RE.search(line)
            if date_match:
                ref_date = _parse_ref_date(date_match.group(1))
                if ref_date and not (loose_start <= ref_date <= win_end):
                    out_of_window_nums.add(ref_match.group(1))
                    logging.getLogger(__name__).warning(
                        "过滤窗口外参考文献 [%s] 日期=%s 窗口=%s~%s: %s",
                        ref_match.group(1), ref_date, win_start, win_end, line[:100],
                    )
                    continue
        clean_lines.append(line)

    if not out_of_window_nums:
        return md

    pattern = re.compile(
        r'\s*\[(' + '|'.join(re.escape(n) for n in out_of_window_nums) + r')\]'
    )
    result_lines = [pattern.sub('', l) for l in clean_lines]

    logging.getLogger(__name__).info(
        "已过滤 %d 条窗口外参考文献，编号: %s",
        len(out_of_window_nums), sorted(out_of_window_nums, key=int),
    )
    return '\n'.join(result_lines)

# ──────────────────────────────────────
# 创建日志目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 创建日志文件名（带时间戳）
log_filename = log_dir / f"tianta_ci_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tianta_ci")
console = Console()

# 记录日志文件位置
logger.info(f"日志文件: {log_filename}")
try:
    console.print(f"[dim]日志文件: {log_filename}[/dim]\n")
except UnicodeEncodeError:
    print(f"日志文件: {log_filename}\n")


# ──────────────────────────────────────
# 搜索引擎状态检查
# ──────────────────────────────────────
def check_search_engines() -> dict[str, bool]:
    """检查当前搜索入口配置状态（SearXNG 主链）"""
    from config import JINA_API_KEY

    searxng_base_url = os.getenv('SEARXNG_BASE_URL', '').strip()
    engines = {
        "SearXNG (主链)": bool(searxng_base_url),
        "DuckDuckGo (免费兜底)": True,
        "百度新闻 (定向补充)": True,
        "政采网 (招投标)": True,
        "Jina Reader (深读)": bool(JINA_API_KEY),
    }
    return engines


def validate_critical_search_engines() -> tuple[bool, str]:
    """验证 SearXNG 主搜索入口是否可用"""
    import requests

    base_url = os.getenv('SEARXNG_BASE_URL', '').strip().rstrip('/')
    verify_ssl = os.getenv('SEARXNG_VERIFY_SSL', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}
    if not base_url:
        return False, 'SEARXNG_BASE_URL 未配置'

    try:
        logger.info('正在验证 SearXNG ...')
        console.print('[dim]正在验证 SearXNG ...[/dim]')
        response = requests.get(
            f'{base_url}/search',
            params={
                'q': 'test',
                'format': 'json',
                'language': 'zh-CN',
                'categories': 'news',
                'time_range': 'week',
            },
            timeout=12,
            verify=verify_ssl,
        )
        if response.status_code == 200:
            logger.info('SearXNG 验证成功')
            console.print('[green][OK] SearXNG 验证成功[/green]')
            return True, ''
        return False, f'SearXNG 返回错误: {response.status_code}'
    except requests.exceptions.Timeout:
        return False, 'SearXNG 请求超时'
    except Exception as exc:
        return False, f'SearXNG 验证失败: {exc}'


def validate_llm_apis() -> tuple[bool, bool, str]:
    """
    验证大模型API是否可用

    Returns:
        tuple[bool, bool, str]: (deepseek_ok, qwen_ok, error_message)
    """
    import requests
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, QWEN_API_KEY, QWEN_BASE_URL

    deepseek_ok = False
    qwen_ok = False
    error_messages = []

    # 测试 DeepSeek
    if DEEPSEEK_API_KEY:
        try:
            logger.info("正在验证DeepSeek API...")
            console.print("[dim]正在验证DeepSeek API...[/dim]")
            response = requests.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10,
                },
                timeout=15,
            )
            if response.status_code == 200:
                deepseek_ok = True
                logger.info("DeepSeek API 验证成功")
                console.print("[green][OK] DeepSeek API 验证成功[/green]")
            elif response.status_code == 401:
                error_msg = "DeepSeek API Key 无效或已过期"
                logger.error(error_msg)
                error_messages.append(error_msg)
            elif response.status_code == 429:
                error_msg = "DeepSeek API 配额已用完或请求过于频繁"
                logger.error(error_msg)
                error_messages.append(error_msg)
            elif response.status_code == 402:
                error_msg = "DeepSeek API 余额不足"
                logger.error(error_msg)
                error_messages.append(error_msg)
            else:
                error_msg = f"DeepSeek API 返回错误: {response.status_code}"
                logger.error(error_msg)
                error_messages.append(error_msg)
        except requests.exceptions.Timeout:
            error_msg = "DeepSeek API 请求超时"
            logger.error(error_msg)
            error_messages.append(error_msg)
        except Exception as e:
            error_msg = f"DeepSeek API 验证失败: {str(e)}"
            logger.error(error_msg)
            error_messages.append(error_msg)
    else:
        error_msg = "DeepSeek API Key 未配置"
        logger.error(error_msg)
        error_messages.append(error_msg)

    # 测试 Qwen
    if QWEN_API_KEY:
        try:
            logger.info("正在验证阿里千问(Qwen) API...")
            console.print("[dim]正在验证阿里千问(Qwen) API...[/dim]")
            response = requests.post(
                f"{QWEN_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {QWEN_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen-plus",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10,
                },
                timeout=15,
            )
            if response.status_code == 200:
                qwen_ok = True
                logger.info("阿里千问(Qwen) API 验证成功")
                console.print("[green][OK] 阿里千问(Qwen) API 验证成功[/green]")
            elif response.status_code == 401:
                error_msg = "阿里千问(Qwen) API Key 无效或已过期"
                logger.error(error_msg)
                error_messages.append(error_msg)
            elif response.status_code == 429:
                error_msg = "阿里千问(Qwen) API 配额已用完或请求过于频繁"
                logger.error(error_msg)
                error_messages.append(error_msg)
            elif response.status_code == 402:
                error_msg = "阿里千问(Qwen) API 余额不足"
                logger.error(error_msg)
                error_messages.append(error_msg)
            else:
                error_msg = f"阿里千问(Qwen) API 返回错误: {response.status_code}"
                logger.error(error_msg)
                error_messages.append(error_msg)
        except requests.exceptions.Timeout:
            error_msg = "阿里千问(Qwen) API 请求超时"
            logger.error(error_msg)
            error_messages.append(error_msg)
        except Exception as e:
            error_msg = f"阿里千问(Qwen) API 验证失败: {str(e)}"
            logger.error(error_msg)
            error_messages.append(error_msg)
    else:
        error_msg = "阿里千问(Qwen) API Key 未配置"
        logger.warning(error_msg)
        error_messages.append(error_msg)

    error_message = "\n".join(error_messages) if error_messages else ""
    return deepseek_ok, qwen_ok, error_message


# ──────────────────────────────────────
# 主函数
# ──────────────────────────────────────
def main():
    console.print(Panel.fit(
        f"[bold cyan]中科天塔竞情分析周报[/bold cyan]\n\n"
        f"[dim]报告周期 : {WINDOW_LABEL}[/dim]\n"
        f"[dim]LLM     : DeepSeek[/dim]\n"
        f"[dim]搜索引擎 : SearXNG + 百度新闻 + DuckDuckGo + 政采网[/dim]\n"
        f"[dim]框架     : CrewAI Multi-Agent[/dim]",
        border_style="cyan",
    ))

    # ══════════════════════════════════
    # 0. 检查是否有未完成的任务（断点续传）
    # ══════════════════════════════════
    checkpoint_manager, should_resume = check_and_prompt_resume(OUTPUT_DIR)

    # 如果选择继续且有完整结果，直接跳到结果处理
    skip_execution, cached_result = should_skip_execution(checkpoint_manager)
    if skip_execution and cached_result:
        console.print("[green][OK] 使用缓存的执行结果，跳过Crew执行[/green]\n")
        raw_output = cached_result
        # 跳转到结果解析部分
        goto_result_parsing = True
    else:
        goto_result_parsing = False

    # ══════════════════════════════════
    # 1. 检查 API Key 与搜索主链
    # ══════════════════════════════════
    if not goto_result_parsing:
        logger.info('=' * 60)
        logger.info('开始API验证')
        logger.info('=' * 60)

        engines = check_search_engines()
        console.print("\n[bold]搜索链状态:[/bold]")
        logger.info('搜索链配置状态:')
        for name, status in engines.items():
            icon = '[OK]' if status else '[ ]'
            console.print(f'  {icon} {name}')
            logger.info(f"  {name}: {'已配置' if status else '未配置'}")

        console.print("\n[bold]验证大模型API可用性...[/bold]")
        logger.info('开始验证大模型API')
        deepseek_ok, qwen_ok, llm_error_message = validate_llm_apis()

        if not deepseek_ok:
            console.print("\n[bold red][ERROR] 严重错误：DeepSeek API 不可用！[/bold red]")
            console.print('[bold red]DeepSeek是主要的LLM，无法继续执行任务。[/bold red]\n')
            console.print('[bold yellow]错误详情：[/bold yellow]')
            for line in llm_error_message.split('\n'):
                if 'DeepSeek' in line:
                    console.print(f'  • {line}')
            console.print('\n[bold yellow]可能的原因：[/bold yellow]')
            console.print('  1. API Key 无效或已过期')
            console.print('  2. API 余额不足')
            console.print('  3. 网络连接问题')
            console.print('\n[bold cyan]解决方案：[/bold cyan]')
            console.print('  1. 检查 .env 文件中的 DEEPSEEK_API_KEY')
            console.print('  2. 登录 DeepSeek 控制台检查账户状态')
            console.print('  3. 确认网络连接正常')
            logger.error('DeepSeek API验证失败，程序终止')
            sys.exit(1)

        if not qwen_ok:
            console.print("\n[bold yellow][WARN] 阿里千问(Qwen) API 不可用[/bold yellow]")
            console.print('[dim]CEO参谋将使用DeepSeek，报告生成可能受影响[/dim]\n')
            logger.warning('阿里千问(Qwen) API不可用，将使用DeepSeek作为备选')
        else:
            console.print("\n[bold green][OK] 大模型API验证通过 — DeepSeek + Qwen 双引擎就绪[/bold green]\n")
            logger.info('大模型API验证通过')

        console.print("\n[bold]验证搜索链可用性...[/bold]")
        logger.info('验证搜索链')
        # 搜索链已升级：搜狗搜索（主力）→ 百度（备用）→ SearXNG（兜底）
        searxng_ok, search_error_message = validate_critical_search_engines()
        if searxng_ok:
            console.print("[green][OK] SearXNG 可用[/green]")
        else:
            console.print(f"[yellow][INFO] SearXNG 不可用（{search_error_message}），将使用搜狗搜索+百度搜索替代[/yellow]")
            logger.info('SearXNG not available, will use Sogou + Baidu fallback')
        console.print("")

    logger.info('=' * 60)
    logger.info('API验证完成，开始执行任务')
    logger.info('=' * 60)

    # ══════════════════════════════════
    # 2. 构建 Crew（7 个 Task 完整链路）
    # ══════════════════════════════════
    console.print("[bold green]正在初始化 CrewAI 智能体团队...[/bold green]\n")
    logger.info("开始初始化CrewAI智能体团队")

    crew = Crew(
        agents=[
            intelligence_scout,         # 情报侦察员
            talent_analyst,             # 人才分析师
            market_analyst,             # 市场分析师
            tech_analyst,               # 技术分析师
            bidding_funding_analyst,    # 竞标融资分析师
            policy_analyst,             # 政策分析师
            ceo_advisor,                # CEO 参谋
        ],
        tasks=[
            task_discover,              # Step 1: 发现竞争对手
            task_talent,                # Step 2: 人才分析     (依赖 1)
            task_market,                # Step 3: 市场分析     (依赖 1)
            task_tech,                  # Step 4: 技术分析     (依赖 1)
            task_bidding_funding,       # Step 5: 竞标+融资    (依赖 1)
            task_policy,                # Step 6: 政策环境分析 (独立)
            task_global_tech,           # Step 6.5: 全球技术趋势 (独立)
            task_scoring,               # Step 7: 综合评分     (依赖 2-5)
            task_report,                # Step 8: CEO周报    (依赖 6,6.5,7)
        ],
        process=Process.sequential,
        verbose=True,
        memory=False,
        max_rpm=30,     # DeepSeek rate limit friendly
    )

    console.print("[bold]智能体团队就绪，开始执行竞情收集与分析...[/bold]")
    console.print("[dim]任务链: 发现对手 → 人才/市场/技术/竞标融资 → 政策/全球技术 → 评分 → CEO报告[/dim]")
    console.print("[dim]预计运行 20-35 分钟，取决于搜索响应速度...[/dim]\n")
    logger.info("智能体团队初始化完成")
    logger.info("开始执行任务链")

    # ══════════════════════════════════
    # 3. 启动 Crew
    # ══════════════════════════════════
    start_time = datetime.now()
    logger.info(f"任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    CREW_TIMEOUT_SECONDS = 1800  # 20 分钟整体超时
    result_container = []
    exception_container = []

    def _run_crew():
        try:
            result_container.append(crew.kickoff())
        except Exception as e:
            exception_container.append(e)

    crew_thread = threading.Thread(target=_run_crew, daemon=True)
    crew_thread.start()
    crew_thread.join(timeout=CREW_TIMEOUT_SECONDS)

    if crew_thread.is_alive():
        console.print(f"\n[bold red][ERROR] Crew 执行超时（{CREW_TIMEOUT_SECONDS}s），强制终止[/bold red]")
        logger.error(f"Crew execution timed out after {CREW_TIMEOUT_SECONDS}s")
        sys.exit(1)

    if exception_container:
        raise exception_container[0]

    result = result_container[0]
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"任务完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"总耗时: {duration}")

    # 保存checkpoint
    save_crew_result(checkpoint_manager, result)

    # ══════════════════════════════════
    # 4. 解析结果
    # ══════════════════════════════════
    console.print("\n[bold green][OK] 智能体执行完成，正在解析结果...[/bold green]\n")
    logger.info("开始解析结果")

    # 从 CrewAI 结果中提取原始文本
    if hasattr(result, "raw"):
        raw_output = result.raw
    elif hasattr(result, "output"):
        raw_output = result.output
    else:
        raw_output = str(result)

# 从这里开始，无论是否跳过执行，都会执行结果解析和报告生成

    # ── 调试输出（帮助排查解析问题） ──
    console.print(f"[dim]原始输出长度: {len(raw_output)} 字符[/dim]")

    # 尝试提取 JSON
    report_data = extract_json(raw_output)

    # 如果 Crew 返回的是仅包含文件名的 JSON（{"onepager": "CEO_OnePager.md", "top15": "TOP15_Competitors.md"})，
    # 常见情况是后续文本中还原有两个 Markdown 代码块。尝试从原始输出中提取这两个代码块并优先使用。
    extracted_ceo_md = None
    extracted_top15_md = None
    extracted_satellite_md = None
    extracted_laser_md = None
    extracted_summary_md = None

    # 首先尝试使用新的分隔符格式提取
    import re
    # 使用更宽松的正则表达式来匹配分隔符（允许额外的空白字符）
    main_report_match = re.search(r"===\s*主报告开始\s*===\s*(.*?)\s*===\s*主报告结束\s*===", raw_output, re.S)
    satellite_match = re.search(r"===\s*商业航天测运控备份文件开始\s*===\s*(.*?)\s*===\s*商业航天测运控备份文件结束\s*===", raw_output, re.S)
    laser_match = re.search(r"===\s*激光通讯终端备份文件开始\s*===\s*(.*?)\s*===\s*激光通讯终端备份文件结束\s*===", raw_output, re.S)
    summary_match = re.search(r"===\s*汇总备份文件开始\s*===\s*(.*?)\s*===\s*汇总备份文件结束\s*===", raw_output, re.S)

    # 兼容旧格式
    top15_match = re.search(r"===\s*TOP15备份文件开始\s*===\s*(.*?)\s*===\s*TOP15备份文件结束\s*===", raw_output, re.S)

    if main_report_match:
        extracted_ceo_md = main_report_match.group(1).strip()
    elif re.search(r"===\s*主报告开始\s*===", raw_output):
        # 如果找到开始标记但没有结束标记，提取从开始到文件末尾的内容
        main_report_match = re.search(r"===\s*主报告开始\s*===\s*(.*)", raw_output, re.S)
        if main_report_match:
            content = main_report_match.group(1).strip()
            # 移除可能的其他备份文件标记
            content = re.sub(r"===\s*商业航天测运控备份文件开始\s*===.*", "", content, flags=re.S)
            content = re.sub(r"===\s*激光通讯终端备份文件开始\s*===.*", "", content, flags=re.S)
            content = re.sub(r"===\s*汇总备份文件开始\s*===.*", "", content, flags=re.S)
            extracted_ceo_md = content.strip()
    if satellite_match:
        extracted_satellite_md = satellite_match.group(1).strip()
    if laser_match:
        extracted_laser_md = laser_match.group(1).strip()
    if summary_match:
        extracted_summary_md = summary_match.group(1).strip()
    if top15_match:
        extracted_top15_md = top15_match.group(1).strip()

    # 如果新格式没有找到，尝试旧格式
    if isinstance(report_data, dict) and set(report_data.keys()) == {"onepager", "top15"}:
        import re
        # 抽取所有 markdown 代码块
        md_blocks = re.findall(r"```(?:markdown)?\n(.*?)\n```", raw_output, re.S)
        blocks = [b.strip() for b in md_blocks if b and b.strip()]
        if blocks:
            if len(blocks) >= 1:
                extracted_ceo_md = blocks[0]
            if len(blocks) >= 2:
                extracted_top15_md = blocks[1]

        # 备选：根据带标签的段落提取
        if not extracted_ceo_md:
            m = re.search(r"CEO_OnePager.md 文件内容如下：\s*```markdown\s*(.*?)\s*```", raw_output, re.S)
            if m:
                extracted_ceo_md = m.group(1).strip()
        if not extracted_top15_md:
            m = re.search(r"TOP15_Competitors.md 文件内容如下：\s*```markdown\s*(.*?)\s*```", raw_output, re.S)
            if m:
                extracted_top15_md = m.group(1).strip()

    # 如果提取到了内容，回写到结构化数据中
    if extracted_ceo_md or extracted_top15_md or extracted_satellite_md or extracted_laser_md or extracted_summary_md:
        if report_data is None:
            report_data = {}
        # 将完整文本回写到结构化数据中，方便保存与调试
        report_data.setdefault("onepager_text", extracted_ceo_md or "")
        # 优先使用新格式的三个备份文件
        report_data.setdefault("satellite_backup_text", extracted_satellite_md or "")
        report_data.setdefault("laser_backup_text", extracted_laser_md or "")
        report_data.setdefault("summary_backup_text", extracted_summary_md or "")
        # 兼容旧格式
        report_data.setdefault("top15_text", extracted_top15_md or "")
        report_data.setdefault("executive_summary", (extracted_ceo_md or "")[:3000])
        report_data.setdefault("competitor_cards", [])

    # ── 调试输出 ──
    if report_data is not None:
        console.print(f"[dim]解析后数据类型: {type(report_data).__name__}[/dim]")
        if isinstance(report_data, dict):
            console.print(f"[dim]报告数据键: {list(report_data.keys())}[/dim]")
        elif isinstance(report_data, list):
            console.print(f"[dim]列表长度: {len(report_data)}[/dim]")
            if report_data and isinstance(report_data[0], dict):
                console.print(f"[dim]第一个元素键: {list(report_data[0].keys())}[/dim]")
    else:
        console.print("[dim]JSON解析失败，将使用原始文本[/dim]")

    # ── Fallback 处理 ──
    if report_data is None:
        logger.warning("Could not parse JSON from crew output, using raw text")
        report_data = {
            "onepager_text": raw_output,  # preserve original text for renderer
            "executive_summary": raw_output,  # 使用完整输出，不截断
            "top3_threats": [],
            "radar_summary": {},
            "action_items": [],
            "competitor_cards": [],
        }

    if isinstance(report_data, list):
        # 如果输出是纯竞争对手卡片数组
        sorted_cards = sort_cards_by_score(report_data)
        report_data = {
            "executive_summary": "（自动生成：请查看 TOP15 详情卡片）",
            "top3_threats": [
                {
                    "company": c.get("company", ""),
                    "score": c.get("score_total", 0),
                    "threat_reason": "; ".join(c.get("risk_flags", [])[:3]),
                    "what_at_risk": "; ".join(
                        c.get("highlights", {}).get("market", [])[:2]
                    ),
                    "suggested_action": "; ".join(
                        c.get("highlights", {}).get("tech", [])[:1]
                    ),
                }
                for c in sorted_cards[:3]
            ],
            "radar_summary": {},
            "action_items": [],
            "competitor_cards": report_data,
        }

    # ══════════════════════════════════
    # 5. 渲染 Markdown 报告
    # ══════════════════════════════════
    console.print("[bold]正在渲染报告...[/bold]")

    # 先规范化/填充 report_data，确保渲染函数能生成与样例一致的结构
    report_data = prepare_report_data_for_render(report_data)

    # 如果已经从原始输出中抽取到 Markdown 内容，则直接使用；否则按结构化数据渲染
    ceo_md = extracted_ceo_md or render_ceo_onepager(report_data)

    # 处理备份文件：优先使用新格式的三个备份文件
    satellite_backup_md = extracted_satellite_md or ""
    laser_backup_md = extracted_laser_md or ""
    summary_backup_md = extracted_summary_md or ""
    # 兼容旧格式
    top15_md = extracted_top15_md or render_top15_cards(report_data.get("competitor_cards", []))

    # ── 过滤假 URL（example.com / placeholder 等）──
    ceo_md = _strip_fake_urls(ceo_md)
    satellite_backup_md = _strip_fake_urls(satellite_backup_md)
    laser_backup_md = _strip_fake_urls(laser_backup_md)
    summary_backup_md = _strip_fake_urls(summary_backup_md)
    top15_md = _strip_fake_urls(top15_md)

    # ── 过滤时间窗口外的参考文献 ──
    ceo_md = _strip_out_of_window(ceo_md)
    satellite_backup_md = _strip_out_of_window(satellite_backup_md)
    laser_backup_md = _strip_out_of_window(laser_backup_md)
    summary_backup_md = _strip_out_of_window(summary_backup_md)
    top15_md = _strip_out_of_window(top15_md)

    # ══════════════════════════════════
    # 6. 保存所有文件
    # ══════════════════════════════════
    out_path = save_reports(ceo_md, top15_md, report_data, satellite_backup_md, laser_backup_md, summary_backup_md)

    # 额外保存原始输出（便于调试）
    raw_path = os.path.join(out_path, "crew_raw_output.txt")
    try:
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(raw_output)
    except Exception:
        pass

    # ══════════════════════════════════
    # 7. 生成PDF报告
    # ══════════════════════════════════
    pdf_generated = False
    if OUTPUT_FORMAT in ("pdf", "both"):
        console.print("[bold]正在生成PDF报告...[/bold]")
        md_report_name = f"天塔竞情战略周报({REPORT_END.strftime('%Y%m%d')}).md"
        md_report_path = os.path.join(out_path, md_report_name)
        pdf_report_path = os.path.join(out_path, PDF_NAME)

        try:
            pdf_generated = generate_pdf_from_markdown(md_report_path, pdf_report_path)
            if pdf_generated:
                console.print(f"[green][OK] PDF生成成功: {pdf_report_path}[/green]")
            else:
                console.print("[yellow][WARN] PDF生成失败，请检查日志[/yellow]")
        except Exception as e:
            console.print(f"[red][ERROR] PDF生成异常: {e}[/red]")
            logger.error(f"PDF generation error: {e}", exc_info=True)

    # ══════════════════════════════════
    # 8. 上传到飞书
    # ══════════════════════════════════
    try:
        from feishu_uploader import upload_report
        console.print("[bold]正在上传报告到飞书...[/bold]")
        logger.info("开始上传报告到飞书")
        feishu_result = upload_report(out_path, WINDOW_LABEL)
        console.print(
            f"[green][OK] 飞书上传成功 — 文件已入库，写入竞情记录 {feishu_result['records_written']} 条[/green]"
        )
        logger.info(f"飞书上传成功: file_token={feishu_result['file_token']}, records={feishu_result['records_written']}")
    except Exception as e:
        console.print(f"[yellow][WARN] 飞书上传失败（不影响本地报告）: {e}[/yellow]")
        logger.warning(f"飞书上传失败: {e}")

    # 构建输出说明
    md_lines = []
    if OUTPUT_FORMAT in ("md", "both"):
        md_lines = [
            f"  ├── 天塔竞情战略周报({REPORT_END.strftime('%Y%m%d')}).md  ← 完整报告",
            "  ├── All_Companies_Data_Backup.md  ← 所有公司数据备份",
        ]
    pdf_line = []
    if OUTPUT_FORMAT in ("pdf", "both") and pdf_generated:
        pdf_line = [f"  ├── {PDF_NAME}          ← PDF报告"]

    other_lines = [
        "  ├── raw_data.json            ← 结构化数据",
        "  └── crew_raw_output.txt      ← 原始输出（调试用）",
    ]

    console.print(Panel.fit(
        f"[bold green]报告生成完毕！[/bold green]\n\n"
        f"输出目录: [cyan]{out_path}[/cyan]\n"
        + "\n".join(md_lines + pdf_line + other_lines) + "\n\n"
        f"[dim]报告周期: {WINDOW_LABEL}[/dim]",
        border_style="green",
    ))

    logger.info("="*60)
    logger.info("报告生成完毕")
    logger.info(f"输出目录: {out_path}")
    logger.info("="*60)

    # ══════════════════════════════════
    # 8. 终端预览 CEO 摘要
    # ══════════════════════════════════
    console.print("\n")
    preview = ceo_md[:3000]
    if len(ceo_md) > 3000:
        preview += "\n\n... (完整版请查看文件)"
    console.print(Panel(
        preview,
        title="[bold]CEO 一页式摘要预览[/bold]",
        border_style="cyan",
    ))

    # 统计信息
    cards = report_data.get("competitor_cards", [])
    console.print(f"\n[dim]统计: 分析了 {len(cards)} 家竞争对手[/dim]")
    logger.info(f"统计: 分析了 {len(cards)} 家竞争对手")
    if cards:
        top = sort_cards_by_score(cards, limit=5)
        console.print("[dim]威胁分 TOP5:[/dim]")
        logger.info("威胁分 TOP5:")
        for i, c in enumerate(top, 1):
            score_val = parse_score(c.get("score_total", 0))
            name = c.get("company", "未知")
            console.print(f"[dim]  {i}. {name}: {score_val:.1f}分[/dim]")
            logger.info(f"  {i}. {name}: {score_val:.1f}分")

    logger.info("="*60)
    logger.info("程序执行完成")
    logger.info(f"日志文件: {log_filename}")
    logger.info("="*60)
    console.print(f"\n[dim]完整日志已保存至: {log_filename}[/dim]\n")


if __name__ == "__main__":
    main()