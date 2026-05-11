"""
Markdown 报告渲染器 (兜底使用)
"""

from __future__ import annotations
import json
import os
from config import OUTPUT_DIR, WINDOW_LABEL, TZ
from utils.scoring import parse_score, get_risk_level, sort_cards_by_score

def render_ceo_onepager(report_data: dict) -> str:
    """
    当大模型没有直接输出 Markdown 时，使用此兜底函数
    按照新的三部分结构生成报告
    """
    summary = report_data.get("executive_summary", "")
    cards = report_data.get("competitor_cards", [])

    lines = [f"# 🛰️ 竞情半月报（{WINDOW_LABEL}）\n"]

    # 第一部分：宏观环境与行业趋势分析
    lines.append("## 第一部分：宏观环境与行业趋势分析\n")
    
    lines.append("### 🏛️ 宏观政策面影响分析")
    lines.append("**对中科天塔有影响的政策动向（3-5条）：**")

    # 尝试从 report_data 中提取政策信息
    policy_data = report_data.get("policy_analysis", {})
    policy_trends = policy_data.get("policy_trends", [])

    if policy_trends:
        for i, policy in enumerate(policy_trends[:5], 1):
            policy_name = policy.get("policy_name", "政策动向")
            authority = policy.get("issuing_authority", "")
            content = policy.get("key_content", "")
            impact = policy.get("impact_on_tianta", "")
            url = policy.get("url", "")
            ref_mark = f"[{i}]" if url else ""
            lines.append(f"- {authority} - {policy_name}：{content} {impact} {ref_mark}")
    else:
        lines.append("- 政策分析1：（基于搜索结果的政策影响分析）")
        lines.append("- 政策分析2：（基于搜索结果的政策影响分析）")
        lines.append("- 政策分析3：（基于搜索结果的政策影响分析）")
    lines.append("")

    lines.append("### 🚀 技术、产业、市场动态发展趋势")
    lines.append("**国际技术动向（重点关注）：**")
    lines.append("- SpaceX及国外卫星测运控技术动向：（基于搜索结果的国际技术分析）")
    lines.append("- 激光通讯终端国际动向：（基于搜索结果的国际激光通讯分析）")
    lines.append("")

    lines.append("**国内技术发展趋势：**")
    lines.append("- 国内卫星测运控技术：（基于搜索结果的国内技术发展分析）")
    lines.append("- 国内激光通讯终端：（基于搜索结果的国内激光通讯分析）")
    lines.append("- AI与航天融合：（基于搜索结果的AI技术应用分析）")
    lines.append("")

    lines.append("**产业发展趋势：**")
    lines.append("- 产业趋势1：（基于搜索结果的产业变化分析）")
    lines.append("- 产业趋势2：（基于搜索结果的产业变化分析）\n")

    lines.append("**市场发展趋势：**")
    lines.append("- 市场趋势1：（基于搜索结果的市场变化分析）")
    lines.append("- 市场趋势2：（基于搜索结果的市场变化分析）\n")

    lines.append("---\n")

    # 第二部分：主要竞争对手分析与应对策略
    lines.append("## 第二部分：主要竞争对手分析与应对策略\n")
    
    lines.append("### 🎯 核心判断：竞争格局重构")
    lines.append("本周期监测显示，行业竞争态势发生结构性变化。主要竞争对手均在加强自身生态建设，对第三方服务商构成挤压。\n")

    lines.append("### 🏢 主要竞争对手动向分析（TOP5）\n")

    # 分析前5名竞争对手
    top_cards = sort_cards_by_score(cards, limit=5)
    
    for i, card in enumerate(top_cards, 1):
        company = card.get("company", f"竞争对手{i}")
        score = card.get("score_total", 0)
        highlights = card.get("highlights", {})
        
        lines.append(f"#### {['一', '二', '三', '四', '五'][i-1]}、{company}：主要威胁")
        lines.append("**关键动向：**")
        
        # 从highlights中提取关键动向
        market_highlights = highlights.get("market", [])
        tech_highlights = highlights.get("tech", [])
        
        if market_highlights:
            lines.append(f"- {market_highlights[0] if market_highlights else '市场动向分析'}")
        if tech_highlights:
            lines.append(f"- {tech_highlights[0] if tech_highlights else '技术动向分析'}")
        
        lines.append("\n**对我们的影响：**")
        lines.append("- 影响分析1：（基于动向的影响评估）")
        lines.append("- 影响分析2：（基于动向的影响评估）")
        
        lines.append("\n**我们应该做的举措：**")
        lines.append("- 应对举措1：（针对性的应对策略）")
        lines.append("- 应对举措2：（针对性的应对策略）\n")

    # 风险预警表格
    lines.append("### ⚠️ 三大风险预警\n")
    lines.append("| 风险类型 | 概率 | 影响 | 时间窗口 | 关键指标 |")
    lines.append("|----------|------|------|----------|----------|")
    lines.append("| 生态锁定加速 | 高 | 大 | 60-120天 | 头部公司自建体系完善度 |")
    lines.append("| 价格战升级 | 中高 | 中 | 30-90天 | 主要对手降价策略 |")
    lines.append("| 核心人才虹吸 | 中 | 大 | 90-180天 | 对手扩招关键岗位 |\n")

    lines.append("---\n")

    # 第三部分：附录
    lines.append("## 第三部分：附录 - 所有竞争对手动向详情\n")
    
    # TOP15总览表格
    lines.append("### 📋 竞争对手威胁分 TOP15 总览")
    lines.append("| 排名 | 公司名称 | 威胁总分 | 风险等级 | 核心异动标签 |")
    lines.append("|---|---|---|---|---|")
    
    sorted_cards = sort_cards_by_score(cards, limit=15)

    for i, card in enumerate(sorted_cards, 1):
        company = card.get("company", "未知公司")
        score = parse_score(card.get("score_total", 0))
        level = get_risk_level(score)
        
        risk_flags = card.get("risk_flags", [])
        tag = risk_flags[0] if risk_flags else "暂无明显动向"
        
        lines.append(f"| {i} | {company} | {score:.1f} | {level} | {tag} |")

    lines.append("\n### 📰 所有竞争对手动向详情及消息来源\n")

    # 详细动向列表
    for card in sorted_cards:
        company = card.get("company", "未知公司")
        highlights = card.get("highlights", {})
        
        lines.append(f"#### {company}")
        lines.append("**最新动向：**")
        
        # 从各维度highlights中提取动向
        all_highlights = []
        for category, items in highlights.items():
            if items:
                all_highlights.extend(items[:2])  # 每个维度最多取2条
        
        if all_highlights:
            for j, highlight in enumerate(all_highlights[:3], 1):  # 最多显示3条
                lines.append(f"- 动向{j}：{highlight}")
                lines.append("  - **来源**：（搜索工具获取的来源）")
                lines.append("  - **链接**：（真实可查的URL链接）")
                lines.append("  - **日期**：（具体日期）")
        else:
            lines.append("- 暂无重要动向")
            lines.append("  - **来源**：监测结果")
            lines.append("  - **链接**：N/A")
            lines.append("  - **日期**：监测周期内")
        
        lines.append("")

    lines.append("---\n")

    # 添加参考文献与信息来源
    lines.append("## 📚 参考文献与信息来源\n")

    # 收集所有引用
    references = []
    ref_index = 1

    # 从政策数据中收集引用
    policy_data = report_data.get("policy_analysis", {})
    policy_trends = policy_data.get("policy_trends", [])
    for policy in policy_trends[:5]:
        url = policy.get("url", "")
        source = policy.get("source", "")
        date = policy.get("date", "")
        if url:
            references.append(f"[{ref_index}] {source} - {url} - {date}")
            ref_index += 1

    # 从竞争对手卡片中收集引用
    for card in sorted_cards:
        highlights = card.get("highlights", {})
        for category, items in highlights.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        url = item.get("url", "")
                        source = item.get("source", "")
                        date = item.get("date", "")
                        if url:
                            references.append(f"[{ref_index}] {source} - {url} - {date}")
                            ref_index += 1

    if references:
        for ref in references:
            lines.append(ref)
    else:
        lines.append("（本报告基于公开信息搜索整理，具体来源见各条目标注）")

    lines.append("\n---\n")
    lines.append("**报送对象**：公司决策层")
    lines.append("**报送周期**：半月报")
    lines.append(f"**下次报送**：下期时间")

    return "\n".join(lines)


def render_top15_cards(cards: list[dict]) -> str:
    """渲染 TOP15 竞争对手总览表格 (兜底)"""
    lines = [
        "## 附：竞争对手威胁分 TOP15 总览\n",
        "| 排名 | 公司名称 | 威胁总分 | 风险等级 |",
        "|---|---|---|---|"
    ]
    
    for i, card in enumerate(cards, 1):
        company = card.get("company", "未知公司")
        score = parse_score(card.get("score_total", 0))
        level = get_risk_level(score)
            
        lines.append(f"| {i} | {company} | {score:.1f} | {level} |")
        
    return "\n".join(lines)


def save_reports(ceo_text: str, top15_text: str, raw_data: dict) -> str:
    """保存所有报告文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 在新版结构中，我们把 CEO报告和TOP15列表合并到了一个文件里
    # 为了兼容之前的代码结构，我们将完整报告写入 CEO_OnePager，附带一份单独的 TOP15 表格
    
    ceo_path = os.path.join(OUTPUT_DIR, "天塔竞情战略半月报.md")
    with open(ceo_path, "w", encoding="utf-8") as f:
        f.write(ceo_text)

    top15_path = os.path.join(OUTPUT_DIR, "TOP15_Data_Backup.md")
    with open(top15_path, "w", encoding="utf-8") as f:
        f.write(top15_text)

    data_path = os.path.join(OUTPUT_DIR, "raw_data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    return OUTPUT_DIR

def prepare_report_data_for_render(report_data):
    """
    为最终报告标准化数据的辅助函数
    """
    # 根据需求添加实现
    if not isinstance(report_data, dict):
        report_data = {"data": report_data}
    
    # 确保必需的键存在
    defaults = {
        "executive_summary": "",
        "news_items": [],
        "top3_threats": [],
        "radar_summary": {},
        "action_items": [],
        "competitor_cards": []
    }
    # ensure each competitor card has a news list
    for card in report_data.get("competitor_cards", []):
        if isinstance(card, dict):
            card.setdefault("news", [])
    
    for key, default_value in defaults.items():
        report_data.setdefault(key, default_value)
    
    return report_data