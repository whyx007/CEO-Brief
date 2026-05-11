#!/usr/bin/env python3
"""
飞书上传模块 — 中科天塔竞情分析周报
========================================
功能：
  1. 将主报告 .md 文件上传到飞书指定文件夹
  2. 解析报告中各公司竞情信息，录入飞书多维表格

用法：
  # 作为模块调用（在 main.py 中）
  from feishu_uploader import upload_report
  upload_report(out_path, report_period_label)

  # 独立运行（读取最新或指定输出目录）
  python feishu_uploader.py
  python feishu_uploader.py output/20260317_weekly
"""

import os
import re
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("feishu_uploader")

# ── 飞书配置 ──────────────────────────────────────────────────────────────────
FEISHU_APP_ID        = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET    = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_FOLDER_TOKEN  = os.getenv("FEISHU_FOLDER_TOKEN", "")
FEISHU_BITABLE_APP_TOKEN = os.getenv("FEISHU_BITABLE_APP_TOKEN", "")
FEISHU_BITABLE_TABLE_ID  = os.getenv("FEISHU_BITABLE_TABLE_ID", "")

# 多维表格字段名（与飞书表格保持一致）
FIELD_COMPANY   = "公司名称"
FIELD_FUNDING   = "融资"
FIELD_BIDDING   = "招投标信息"
FIELD_OPERATION = "经营组织"
FIELD_TALENT    = "人才动向"
FIELD_IMPACT    = "对中科天塔影响"
FIELD_SOURCE    = "原文链接"


# ── Token 管理 ────────────────────────────────────────────────────────────────

def get_tenant_access_token() -> str:
    """获取飞书 tenant_access_token"""
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


# ── 文件上传 ──────────────────────────────────────────────────────────────────

def upload_md_to_folder(md_path: str, token: str, period_label: str = "") -> dict:
    """
    将 .md 文件上传到飞书文件夹（作为附件文件）。
    返回上传结果 dict，包含 file_token。
    """
    md_path = Path(md_path)
    if not md_path.exists():
        raise FileNotFoundError(f"报告文件不存在: {md_path}")

    file_name = md_path.name
    file_size = md_path.stat().st_size

    logger.info(f"上传文件: {file_name} ({file_size} bytes) → 飞书文件夹")

    with open(md_path, "rb") as f:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/drive/v1/files/upload_all",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "file_name": file_name,
                "parent_type": "explorer",
                "parent_node": FEISHU_FOLDER_TOKEN,
                "size": str(file_size),
            },
            files={"file": (file_name, f, "text/markdown")},
            timeout=60,
        )

    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 0:
        raise RuntimeError(f"文件上传失败: {result}")

    file_token = result["data"]["file_token"]
    logger.info(f"文件上传成功，file_token: {file_token}")
    return result["data"]


# ── 报告解析 ──────────────────────────────────────────────────────────────────

def parse_company_sections(md_content: str) -> list[dict]:
    """
    从报告 Markdown 中解析各公司的竞情信息。
    识别 #### 公司名称（类型）格式的段落，提取各维度信息。
    返回 list of dict，每个 dict 对应一家公司。
    """
    companies = []

    # 按 #### 公司段落分割
    # 格式：#### 公司名称（类型）
    sections = re.split(r'\n(?=####\s)', md_content)

    for section in sections:
        if not section.startswith("####"):
            continue

        # 提取公司名称（去掉类型标注）
        header_match = re.match(r'####\s+(.+?)(?:\s*\n|$)', section)
        if not header_match:
            continue
        raw_name = header_match.group(1).strip()
        # 去掉括号内的类型说明，如（竞争对手）（客户）
        company_name = re.sub(r'[（(][^）)]*[）)]', '', raw_name).strip()
        if not company_name:
            continue

        # 提取各维度内容
        funding   = _extract_items(section, r'融资动向\d*')
        bidding   = _extract_items(section, r'订单动向\d*')
        operation = _extract_items(section, r'经营动向\d*|组织动向\d*')
        talent    = _extract_items(section, r'人才动向\d*')
        impact    = _extract_impact(section)

        # 至少有一个字段有内容才录入
        if not any([funding, bidding, operation, talent, impact]):
            continue

        companies.append({
            FIELD_COMPANY:   company_name,
            FIELD_FUNDING:   funding,
            FIELD_BIDDING:   bidding,
            FIELD_OPERATION: operation,
            FIELD_TALENT:    talent,
            FIELD_IMPACT:    impact,
        })

    logger.info(f"解析到 {len(companies)} 家公司竞情数据")
    return companies


def _extract_items(section: str, label_pattern: str) -> str:
    """提取某类动向的所有条目，合并为字符串"""
    pattern = rf'-\s+{label_pattern}[：:]\s*(.+?)(?=\n-\s+|\n####|\n###|\Z)'
    matches = re.findall(pattern, section, re.S)
    items = []
    for m in matches:
        # 清理引用标记 [数字] 和多余空白
        text = re.sub(r'\s*\[\d+\]', '', m).strip()
        text = re.sub(r'\s+', ' ', text)
        if text:
            items.append(text)
    return "\n".join(items)


def _extract_impact(section: str) -> str:
    """提取'对公司的影响'段落"""
    # 匹配 --可能对公司的影响：-- 或类似格式
    match = re.search(
        r'--[^-]*(?:对公司|对中科天塔)[^-]*影响[^-]*--\s*(.*?)(?=\n####|\n###|\n--|\Z)',
        section, re.S
    )
    if match:
        text = match.group(1).strip()
        text = re.sub(r'\s*\[\d+\]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text
    return ""


# ── 多维表格写入 ──────────────────────────────────────────────────────────────

def write_to_bitable(companies: list[dict], token: str, period_label: str,
                     report_file_url: str = "") -> int:
    """
    将公司竞情数据批量写入飞书多维表格。
    返回成功写入的记录数。
    """
    if not companies:
        logger.warning("没有公司数据可写入")
        return 0

    source_text = f"竞情周报 {period_label}"
    if report_file_url:
        source_text += f"\n{report_file_url}"

    records = []
    for c in companies:
        fields = {
            FIELD_COMPANY:   c.get(FIELD_COMPANY, ""),
            FIELD_FUNDING:   c.get(FIELD_FUNDING, ""),
            FIELD_BIDDING:   c.get(FIELD_BIDDING, ""),
            FIELD_OPERATION: c.get(FIELD_OPERATION, ""),
            FIELD_TALENT:    c.get(FIELD_TALENT, ""),
            FIELD_IMPACT:    c.get(FIELD_IMPACT, ""),
            FIELD_SOURCE:    source_text,
        }
        # 过滤空字段（飞书不接受空字符串的必填字段）
        fields = {k: v for k, v in fields.items() if v}
        records.append({"fields": fields})

    # 飞书批量写入限制 500 条/次
    batch_size = 500
    total_written = 0

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        resp = requests.post(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_BITABLE_APP_TOKEN}"
            f"/tables/{FEISHU_BITABLE_TABLE_ID}/records/batch_create",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"records": batch},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            logger.error(f"写入多维表格失败: {result}")
            raise RuntimeError(f"写入多维表格失败: {result}")

        written = len(result.get("data", {}).get("records", []))
        total_written += written
        logger.info(f"批次 {i//batch_size + 1}: 写入 {written} 条记录")

    logger.info(f"多维表格写入完成，共 {total_written} 条")
    return total_written


# ── 主入口 ────────────────────────────────────────────────────────────────────

def upload_report(out_path: str, period_label: str = "") -> dict:
    """
    完整上传流程：
      1. 上传主报告 .md 到飞书文件夹
      2. 解析报告内容，写入多维表格

    Args:
        out_path: 报告输出目录路径（如 output/20260317_weekly）
        period_label: 报告周期标签（如 "2026.03.02 ~ 2026.03.17"）

    Returns:
        dict with keys: file_token, records_written, success
    """
    result = {"file_token": None, "records_written": 0, "success": False}

    # 验证配置
    missing = [k for k, v in {
        "FEISHU_APP_ID": FEISHU_APP_ID,
        "FEISHU_APP_SECRET": FEISHU_APP_SECRET,
        "FEISHU_FOLDER_TOKEN": FEISHU_FOLDER_TOKEN,
        "FEISHU_BITABLE_APP_TOKEN": FEISHU_BITABLE_APP_TOKEN,
        "FEISHU_BITABLE_TABLE_ID": FEISHU_BITABLE_TABLE_ID,
    }.items() if not v]
    if missing:
        logger.error(f"飞书配置缺失: {missing}")
        raise ValueError(f"飞书配置缺失，请检查 .env: {missing}")

    out_path = Path(out_path)

    # 找主报告 .md 文件
    md_files = list(out_path.glob("天塔竞情战略周报*.md"))
    if not md_files:
        md_files = list(out_path.glob("*.md"))
        # 排除备份文件
        md_files = [f for f in md_files if "Backup" not in f.name and "backup" not in f.name]
    if not md_files:
        raise FileNotFoundError(f"在 {out_path} 中未找到主报告 .md 文件")
    md_file = md_files[0]

    logger.info(f"=== 开始飞书上传 ===")
    logger.info(f"报告文件: {md_file}")
    logger.info(f"报告周期: {period_label}")

    token = get_tenant_access_token()

    # 1. 上传文件
    try:
        upload_result = upload_md_to_folder(str(md_file), token, period_label)
        result["file_token"] = upload_result.get("file_token")
        logger.info(f"✅ 文件上传成功: {md_file.name}")
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise

    # 2. 解析报告并写入多维表格
    try:
        md_content = md_file.read_text(encoding="utf-8")
        companies = parse_company_sections(md_content)

        if companies:
            written = write_to_bitable(companies, token, period_label)
            result["records_written"] = written
            logger.info(f"✅ 多维表格写入成功: {written} 条记录")
        else:
            logger.warning("未解析到公司竞情数据，跳过多维表格写入")
    except Exception as e:
        logger.error(f"多维表格写入失败: {e}")
        raise

    result["success"] = True
    logger.info(f"=== 飞书上传完成 ===")
    return result


def _find_latest_output_dir() -> Path:
    """查找最新的输出目录"""
    output_root = Path("output")
    if not output_root.exists():
        raise FileNotFoundError("output 目录不存在")
    dirs = sorted(
        [d for d in output_root.iterdir() if d.is_dir() and d.name.endswith("_weekly")],
        reverse=True
    )
    if not dirs:
        raise FileNotFoundError("未找到任何报告输出目录")
    return dirs[0]


# ── 独立运行 ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # 支持命令行指定目录
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1])
    else:
        target_dir = _find_latest_output_dir()
        print(f"自动选择最新报告目录: {target_dir}")

    if not target_dir.exists():
        print(f"错误：目录不存在: {target_dir}")
        sys.exit(1)

    # 从目录名推断报告周期（格式 YYYYMMDD_weekly）
    dir_name = target_dir.name
    date_match = re.match(r'(\d{8})_weekly', dir_name)
    if date_match:
        date_str = date_match.group(1)
        end_date = datetime.strptime(date_str, "%Y%m%d")
        from datetime import timedelta
        start_date = end_date - timedelta(days=6)
        period_label = f"{start_date.strftime('%Y.%m.%d')} ~ {end_date.strftime('%Y.%m.%d')}"
    else:
        period_label = dir_name

    print(f"报告周期: {period_label}")
    print(f"开始上传...")

    try:
        result = upload_report(str(target_dir), period_label)
        print("\n[OK] 上传完成")
        print(f"   文件 token : {result['file_token']}")
        print(f"   写入记录数 : {result['records_written']}")
    except Exception as e:
        print(f"\n[FAIL] 上传失败: {e}")
        sys.exit(1)
