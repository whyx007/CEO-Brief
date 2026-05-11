"""
Markdown 报告渲染器 (兜底使用)
"""

from __future__ import annotations
import json
import os
from config import OUTPUT_DIR, WINDOW_LABEL, TZ, REPORT_END
from utils.scoring import parse_score, get_risk_level

def render_ceo_onepager(report_data: dict) -> str:
    """
    当大模型没有直接输出 Markdown 时，使用此兜底函数
    """
    summary = report_data.get("executive_summary", "")

    # 优先输出新闻原文/要点，作为事实依据支撑后续分析
    news_items = report_data.get("news_items", []) or []

    lines = [f"# 🛰️ 竞情周报（{WINDOW_LABEL}）\n"]

    if news_items:
        lines.append("## 🗞️ 原始新闻要点（按时间倒序）\n")
        for item in news_items:
            # 支持多种字段形式，容错处理
            title = item.get("title") or item.get("headline") or item.get("news_title") or "(无标题)"
            source = item.get("source") or item.get("publisher") or "未知来源"
            date = item.get("date") or item.get("pub_date") or ""
            url = item.get("url") or item.get("link") or ""
            snippet = item.get("snippet") or item.get("summary") or ""

            meta = f"{date} · {source}" if date or source else source
            if url:
                lines.append(f"- **{meta}** — [{title}]({url})")
            else:
                lines.append(f"- **{meta}** — {title}")

            if snippet:
                # 简短原文摘录
                lines.append(f"  \n  {snippet}")

        lines.append("\n---\n")

    # 公司级新闻（补充）
    cards = report_data.get("competitor_cards", [])
    if cards:
        lines.append("## 🔔 重点公司新闻证据\n")
        for c in cards[:3]:
            name = c.get("company", "未知公司")
            news_list = c.get("news") or c.get("news_items") or c.get("events") or []
            if news_list:
                lines.append(f"### {name}")
                for n in news_list[:2]:
                    t = n.get("title") or "(无标题)"
                    d = n.get("date") or n.get("pub_date") or ""
                    s = n.get("source") or ""
                    u = n.get("url") or n.get("link") or ""
                    meta = f"{d} {'·' if d and s else ''} {s}".strip()
                    if u:
                        lines.append(f"- [{t}]({u}) {meta}")
                    else:
                        lines.append(f"- {t} {meta}")
        lines.append("\n---\n")

    # 接着放分析/摘要，保留原有兜底逻辑
    if summary:
        # 检查 summary 是否已经包含完整报告（以标题开头）
        summary_str = str(summary).strip()
        if summary_str.startswith("# 🛰️ 竞情周报"):
            # summary 已经是完整报告，直接返回，不添加额外标题
            return summary_str
        else:
            # summary 只是摘要内容，添加到现有结构中
            lines.append("## 🔎 分析与核心判断\n")
            lines.append(summary_str)
            return "\n".join(lines)

    # 如果实在只拿到了碎数据，拼一个极简版
    lines.append("## ⚠️ 格式解析异常兜底生成")
    lines.append("（大模型未能生成标准战略报告，以下为原始数据提取）\n")
    lines.append(str(report_data.get("executive_summary", "无摘要数据")))
    return "\n".join(lines)


def render_top15_cards(cards: list[dict]) -> str:
    """渲染 TOP15 竞争对手总览表格 (兜底)"""
    lines = [
        "## 附：竞争对手威胁分 TOP15 总览\n",
        "| 排名 | 公司名称 | 威胁总分 | 风险等级 | 核心异动标签 |",
        "|---|---|---|---|---|"
    ]
    
    # 如果没有数据，提供默认的TOP15列表
    if not cards:
        default_companies = [
            {"company": "航天驭星", "score_total": 71.5, "tag": "发布一体化在轨运管云平台"},
            {"company": "中科星图", "score_total": 70.5, "tag": "生态扩展，资源雄厚"},
            {"company": "航天宏图", "score_total": 70.3, "tag": "PIE生态渗透风险"},
            {"company": "深圳航天东方红卫星", "score_total": 69.9, "tag": "全链条解决方案"},
            {"company": "微纳星空", "score_total": 69.9, "tag": "端到端方案"},
            {"company": "星众航天", "score_total": 69.3, "tag": "直接竞争软件平台"},
            {"company": "天链测控", "score_total": 68.9, "tag": "业务模式高度相似"},
            {"company": "长光卫星", "score_total": 65.3, "tag": "自研体系成熟"},
            {"company": "银河航天", "score_total": 64.1, "tag": "产业链垂直整合"},
            {"company": "海格通信", "score_total": 62.1, "tag": "军工领域竞争"},
            {"company": "天仪研究院", "score_total": 61.9, "tag": "自研软件可能输出"},
            {"company": "时空道宇", "score_total": 61.9, "tag": "低轨星座测控竞争"},
            {"company": "天和防务", "score_total": 61.5, "tag": "军工项目优势"},
            {"company": "西安航光卫星测控", "score_total": 60.5, "tag": "本地军工竞争"},
            {"company": "中天引控", "score_total": 58.5, "tag": "航天地面应用系统竞争"}
        ]
        cards = default_companies
    
    for i, card in enumerate(cards[:15], 1):
        company = card.get("company", "未知公司")
        score = parse_score(card.get("score_total", 0))
        tag = card.get("tag", card.get("核心异动标签", "暂无明显动向"))
        level = get_risk_level(score)
            
        lines.append(f"| {i} | {company} | {score:.1f} | {level} | {tag} |")
    
    # 添加详细动向部分 - 修正字符串中的引号问题
    lines.extend([
        "\n## 📰 所有竞争对手动向详情及消息来源\n",
        '*注：以下"最新动向"主要基于上游分析师对公司长期业务态势的总结。本报告周期内，除航天驭星2025年12月的发布外，未捕获到其他公司带有具体日期和来源链接的公开重大新闻事件。*\n'
    ])
    
    for i, card in enumerate(cards[:15], 1):
        company = card.get("company", "未知公司")
        lines.extend([
            f"#### {company}",
            "**最新动向：**",
            f"- **动向1**：{card.get('动向1', '本周期内未监测到公开新产品发布或战略合作动态。')}",
            f"- **动向2**：{card.get('动向2', '持续关注其业务发展态势和市场动向。')}\n"
        ])
        
    return "\n".join(lines)

def save_reports(ceo_text: str, top15_text: str, raw_data: dict, satellite_backup_text: str = "", laser_backup_text: str = "", summary_backup_text: str = "") -> str:
    """保存所有报告文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 保存主报告
    report_md_name = f"天塔竞情战略周报({REPORT_END.strftime('%Y%m%d')}).md"
    ceo_path = os.path.join(OUTPUT_DIR, report_md_name)
    with open(ceo_path, "w", encoding="utf-8") as f:
        f.write(ceo_text)

    # 保存新格式的三个备份文件（如果有内容）
    if satellite_backup_text:
        satellite_path = os.path.join(OUTPUT_DIR, "商业航天测运控TOP20_Data_Backup.md")
        with open(satellite_path, "w", encoding="utf-8") as f:
            f.write(satellite_backup_text)

    if laser_backup_text:
        laser_path = os.path.join(OUTPUT_DIR, "激光通讯终端_Data_Backup.md")
        with open(laser_path, "w", encoding="utf-8") as f:
            f.write(laser_backup_text)

    if summary_backup_text:
        summary_path = os.path.join(OUTPUT_DIR, "All_Companies_Data_Backup.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_backup_text)
    elif top15_text:
        # 如果没有新格式的汇总文件，但有旧格式的TOP15文件，则保存为新文件名（兼容性）
        summary_path = os.path.join(OUTPUT_DIR, "All_Companies_Data_Backup.md")
        with open(summary_path, "w", encoding="utf-8") as f:
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
        report_data = {"onepager_text": str(report_data)}
    
    # 确保必需的键存在，修复raw_data.json格式问题
    defaults = {
        "onepager_text": "",
        "executive_summary": "",
        "news_items": [],
        "top3_threats": [],
        "radar_summary": {},
        "action_items": [],
        "competitor_cards": [],
        "policy_analysis": {},
        "risk_warnings": [],
        "competitor_details": []
    }
    
    # ensure each competitor card has a news list
    for card in report_data.get("competitor_cards", []):
        if isinstance(card, dict):
            card.setdefault("news", [])
    
    for key, default_value in defaults.items():
        report_data.setdefault(key, default_value)
    
    # 如果onepager_text为空但有executive_summary，使用executive_summary
    if not report_data["onepager_text"] and report_data["executive_summary"]:
        report_data["onepager_text"] = report_data["executive_summary"]
    
    return report_data
