from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import Any

from modules.company_query.config import COMPANY_INFO_DIR

NS = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
SUMMARY_ROOT = Path('/data/company-summary')


def _col_to_index(ref: str) -> int:
    letters = ''.join(ch for ch in ref if ch.isalpha()).upper()
    result = 0
    for ch in letters:
        result = result * 26 + (ord(ch) - 64)
    return max(result - 1, 0)


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get('t', '')
    # Inline string: text is in <is><t>, not <v>
    if cell_type == 'inlineStr':
        parts = [node.text or '' for node in cell.findall('.//a:t', NS)]
        return ''.join(parts).strip()
    # Shared string reference or plain text
    value = cell.find('a:v', NS)
    if value is None or not value.text:
        return ''
    txt = value.text.strip()
    if cell_type == 's':
        idx = int(txt)
        if 0 <= idx < len(shared_strings):
            return shared_strings[idx].strip()
    return txt


def _normalize(value: Any) -> str:
    text = str(value or '').strip()
    text = re.sub(r'\s+', ' ', text)
    return text


@lru_cache(maxsize=4)
def load_xlsx_rows(xlsx_path: str) -> list[dict[str, str]]:
    path = Path(xlsx_path)
    if not path.exists():
        return []

    with zipfile.ZipFile(path) as zf:
        # Load shared strings
        shared_strings: list[str] = []
        if 'xl/sharedStrings.xml' in zf.namelist():
            ss_xml = ET.fromstring(zf.read('xl/sharedStrings.xml'))
            for si in ss_xml.findall('.//a:si', NS):
                t = si.find('a:t', NS)
                shared_strings.append(t.text or '' if t is not None else '')

        # Find first actual worksheet
        sheet_xml = None
        for candidate in sorted([n for n in zf.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]):
            sheet_xml = ET.fromstring(zf.read(candidate))
            break
        if sheet_xml is None:
            return []

    rows: list[list[str]] = []
    max_cols = 0
    for row in sheet_xml.findall('.//a:sheetData/a:row', NS):
        values: list[str] = []
        for cell in row.findall('a:c', NS):
            ref = cell.attrib.get('r', '')
            idx = _col_to_index(ref)
            while len(values) <= idx:
                values.append('')
            values[idx] = _cell_text(cell, shared_strings)
        max_cols = max(max_cols, len(values))
        rows.append(values)

    if not rows:
        return []

    headers = [(_normalize(item) or f'字段{i + 1}') for i, item in enumerate(rows[0] + [''] * (max_cols - len(rows[0])))]
    records: list[dict[str, str]] = []
    for raw in rows[1:]:
        padded = raw + [''] * (max_cols - len(raw))
        record = {headers[i]: _normalize(padded[i]) for i in range(max_cols)}
        if any(record.values()):
            records.append(record)
    return records


def search_company_rows(xlsx_path: str, query: str, limit: int = 10) -> dict[str, Any]:
    rows = load_xlsx_rows(xlsx_path)
    q = _normalize(query).lower()
    if not q:
        return {'rows': [], 'total': len(rows), 'matched': 0}

    scored: list[tuple[int, dict[str, str]]] = []
    for row in rows:
        company = row.get('公司名称', '')
        text_blob = ' | '.join(v for v in row.values() if v)
        company_l = company.lower()
        blob_l = text_blob.lower()
        score = 0
        if q == company_l:
            score += 200
        elif q in company_l:
            score += 120
        # "中科" only matches company name to avoid false positives (e.g. 中科院)
        if q != '中科' and q in blob_l:
            score += 40
        for token in [part for part in re.split(r'[\s,，、;；/]+', q) if part]:
            if token and token in company_l:
                score += 30
            elif token and token != '中科' and token in blob_l:
                score += 8
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: (-item[0], item[1].get('公司名称', '')))
    return {
        'rows': [row for _, row in scored[:limit]],
        'total': len(rows),
        'matched': len(scored),
    }


def _summary_images_for_company(title: str) -> list[str]:
    name = _normalize(title)
    if not name or not SUMMARY_ROOT.exists():
        return []

    matched_dir: Path | None = None
    for entry in SUMMARY_ROOT.iterdir():
        if not entry.is_dir():
            continue
        entry_name = _normalize(entry.name)
        if entry_name == name or entry_name in name or name in entry_name:
            matched_dir = entry
            break

    if matched_dir is None:
        return []

    all_files = {p.name: p for p in matched_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp', '.pdf'}}
    # prefer _fixed version of PDFs if available
    selected = []
    for name, path in sorted(all_files.items(), key=lambda x: x[0].lower()):
        if name.lower().endswith('.pdf') and not name.endswith('_fixed.pdf'):
            fixed_name = path.stem + '_fixed' + path.suffix
            if fixed_name in all_files:
                continue  # skip original, _fixed will be picked up instead
        selected.append(path)
    return [f"/company-summary/{matched_dir.name}/{img.name}" for img in selected]


def build_company_result(row: dict[str, str]) -> dict[str, Any]:
    title = row.get('公司名称') or '未命名企业'
    summary_parts = [
        row.get('核心技术', ''),
        row.get('产品', ''),
        row.get('产品应用行业', ''),
    ]
    summary = '；'.join(part for part in summary_parts if part)[:360] or '已命中 company-info 企业记录。'

    tags = []
    for key in ['技术成熟度', '商务模式', '交付能力']:
        value = row.get(key, '')
        if value:
            tags.append(value[:28])

    details = []
    for key in ['客户', '供应商', '应用场景', '可能应用场景', '认证/资质/知识产权', '当前最需要的资源类型', '近三年营收及利润', '竞对及技术差异']:
        value = row.get(key, '')
        if value:
            details.append(f'{key}：{value[:180]}')

    summary_images = _summary_images_for_company(title)

    return {
        'title': title,
        'summary': summary,
        'source': 'company-info.xlsx',
        'publishedAt': '',
        'url': row.get('官网URL', '') or '',
        'matchedTargets': ['企业查询', title] + tags[:2],
        'relevanceReason': ' | '.join(details[:3]) or '已命中 company-info 本地企业数据库。',
        'summaryImages': summary_images,
        'raw': row,
    }
