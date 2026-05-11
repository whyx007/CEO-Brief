from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from modules.company_query.config import COMPANY_INFO_DIR
from modules.company_query.services import build_company_result, load_xlsx_rows, search_company_rows


BROWSE_LIMIT = 1000

router = APIRouter()


def resolve_workbook_path():
    preferred = COMPANY_INFO_DIR / 'company-info_with_url.xlsx'
    if preferred.exists():
        return preferred
    fallback = COMPANY_INFO_DIR / 'company-info.xlsx'
    return fallback


def now_iso() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz=tz).replace(microsecond=0).isoformat()


@router.get('/api/company-query/status')
def company_query_status() -> dict[str, Any]:
    files = []
    if COMPANY_INFO_DIR.exists():
        files = [p.name for p in COMPANY_INFO_DIR.iterdir() if p.is_file()]

    workbook_path = resolve_workbook_path()
    row_count = 0
    columns: list[str] = []
    if workbook_path.exists():
        rows = load_xlsx_rows(str(workbook_path))
        row_count = len(rows)
        if rows:
            columns = list(rows[0].keys())

    return {
        'ok': True,
        'module': 'company-query',
        'ready': workbook_path.exists(),
        'companyInfoDir': str(COMPANY_INFO_DIR),
        'fileCount': len(files),
        'files': files[:20],
        'rowCount': row_count,
        'columns': columns[:20],
        'message': '企业查询模块已接入本地 Excel，可按企业名或关键词检索。' if workbook_path.exists() else '未找到 company-info.xlsx，请先放入 company-info 目录。',
    }


@router.get('/api/company-query/browse')
def company_query_browse(limit: int = BROWSE_LIMIT) -> dict[str, Any]:
    workbook_path = resolve_workbook_path()
    if not workbook_path.exists():
        raise HTTPException(status_code=404, detail='company_info_xlsx_not_found')

    rows = load_xlsx_rows(str(workbook_path))
    picked = rows[: max(1, min(limit, len(rows) or 1))]
    items = [build_company_result(row) for row in picked]
    for item in items:
        if not item.get('publishedAt'):
            item['publishedAt'] = now_iso()

    return {
        'ok': True,
        'count': len(items),
        'items': items,
        'meta': {
            'module': 'company-query',
            'mode': 'browse',
            'companyInfoDir': str(COMPANY_INFO_DIR),
            'workbook': str(workbook_path),
            'availableRows': len(rows),
        },
    }


@router.post('/api/company-query/search')
def company_query_search(payload: dict[str, Any]) -> dict[str, Any]:
    query = str((payload or {}).get('query') or '').strip()
    if not query:
        raise HTTPException(status_code=400, detail='query_required')

    limit = max(1, min(1000, int((payload or {}).get('limit') or 500)))

    workbook_path = resolve_workbook_path()
    if not workbook_path.exists():
        raise HTTPException(status_code=404, detail='company_info_xlsx_not_found')

    searched = search_company_rows(str(workbook_path), query, limit=limit)
    results = [build_company_result(row) for row in searched['rows']]

    if not results:
        results = [{
            'title': f'未找到匹配企业：{query}',
            'summary': '当前 Excel 企业库中没有命中结果。你可以尝试输入公司全称、简称、技术关键词、应用场景或客户/供应商关键词。',
            'source': 'company-info.xlsx',
            'publishedAt': now_iso(),
            'url': '',
            'matchedTargets': ['企业查询'],
            'relevanceReason': '本次查询已扫描本地 company-info.xlsx，但没有找到匹配记录。',
        }]

    for item in results:
        if not item.get('publishedAt'):
            item['publishedAt'] = now_iso()

    return {
        'ok': True,
        'query': query,
        'count': len(results),
        'results': results,
        'meta': {
            'module': 'company-query',
            'mode': 'xlsx-search',
            'companyInfoDir': str(COMPANY_INFO_DIR),
            'workbook': str(workbook_path),
            'availableRows': searched['total'],
            'matchedRows': searched['matched'],
        },
    }
