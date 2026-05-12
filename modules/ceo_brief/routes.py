from __future__ import annotations

import json
import os
import socket
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from services.llm_client import DeepSeekClient
from services.news_pipeline import NewsPipeline
from services.free_news_pipeline import FreeNewsPipeline
from services.space_sources import SPACE_RSS_SOURCES
from services.filters import exclude_items, filter_macro_items, filter_policy_items, filter_space_industry_items
from services.brief_builder import build_ceo_brief_from_free_news
from services.markdown_builder import build_brief_markdown

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = ROOT.parents[1]
load_dotenv(ROOT / '.env')

MOCK_DIR = ROOT / 'mock'
DATA_DIR = ROOT / 'data'
TODAY_FILE = MOCK_DIR / 'ceo-brief-today.json'
TARGET_SETTINGS_FILE = MOCK_DIR / 'ceo-brief-target-settings.json'
PROMPT_SETTINGS_FILE = MOCK_DIR / 'ceo-brief-prompt-settings.json'
LATEST_RUN_FILE = DATA_DIR / 'latest-run.json'
LATEST_MD_FILE = DATA_DIR / 'latest-brief.md'
DEBUG_SNAPSHOT_FILE = DATA_DIR / 'latest-debug-snapshot.json'
TARGET_UPDATES_FALLBACK_FILE = ROOT / 'mock' / 'tianta_ceo_target_updates.json'
TARGET_WATCHLIST_FALLBACK_FILE = ROOT / 'mock' / 'tianta_target_watchlist.json'
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'deepseek').strip().lower()
LLM_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat').strip()
llm_client = DeepSeekClient()
news_pipeline = NewsPipeline()
free_news_pipeline = FreeNewsPipeline()

router = APIRouter()
FRONTEND_DIR = ROOT / 'frontend'

DEFAULT_TARGET_SETTINGS = {
    'companies': ['某被投企业'],
    'industries': ['新能源', '半导体'],
    'keywords': ['融资', '订单', '合作'],
    'regions': ['上海', '苏州'],
    'updatedAt': '2026-04-15T09:00:00+08:00',
}

DEFAULT_PROMPT_SETTINGS = {
    'newsFilterPrompt': '请从当天产经与财经信息中筛选最值得CEO关注的内容，优先保留与产业趋势、资本动向、供应链变化、政策影响相关的信息。',
    'newsSummaryPrompt': '请将新闻整理为适合CEO快速阅读的结构化摘要，要求简洁、明确、可决策，突出重点变化与关注理由。',
    'todoPrompt': '请基于目标信息与产经信息生成今日代办建议，要求行动导向、优先级明确、避免空泛表述。',
    'updatedAt': '2026-04-15T09:00:00+08:00',
}

MARKET_SYMBOLS = [
    {'symbol': '^DJI', 'name': '道指', 'stooq': ['^dji']},
    {'symbol': '^IXIC', 'name': '纳指', 'stooq': ['^ixic', '^ndq', '^ndx', '^ccmp', '^comp']},
    {'symbol': '^GSPC', 'name': '标普500', 'stooq': ['^gspc', '^spx']},
    {'symbol': '^HSI', 'name': '恒生', 'stooq': ['^hsi']},
    {'symbol': '000300.SS', 'name': '沪深300', 'stooq': ['^shc']},
    {'symbol': 'CL=F', 'name': 'WTI', 'stooq': ['cl.f']},
    {'symbol': 'BZ=F', 'name': '布油', 'stooq': ['cb.f']},
    {'symbol': 'GC=F', 'name': '黄金', 'stooq': ['gc.f']},
    {'symbol': 'USDCNY=X', 'name': 'USD/CNY', 'stooq': ['usdcny']},
    {'symbol': 'USDJPY=X', 'name': 'USD/JPY', 'stooq': ['usdjpy']},
    {'symbol': 'EURUSD=X', 'name': 'EUR/USD', 'stooq': ['eurusd']},
    {'symbol': 'GBPUSD=X', 'name': 'GBP/USD', 'stooq': ['gbpusd']},
]

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_json_file(path: Path, fallback: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    if not path.exists():
        path.write_text(json.dumps(fallback, ensure_ascii=False, indent=2), encoding='utf-8')


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def now_iso() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz=tz).replace(microsecond=0).isoformat()


def read_json_list(path: Path) -> list[Any]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    return data if isinstance(data, list) else []


def merge_target_fallbacks(today_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(today_payload or {})
    # Filter target updates: only keep items mentioning watchlist companies
    watchlist = read_json_list(TARGET_WATCHLIST_FALLBACK_FILE)
    existing_updates = payload.get('targetUpdates') if isinstance(payload.get('targetUpdates'), list) else []
    
    # Only keep items that mention a watchlist company (check title, summary, matchedTargets)
    if watchlist:
        existing_updates = [
            item for item in existing_updates
            if any(company in ' '.join([str(item.get(k) or '') for k in ['title','summary','content','matchedTargets','source']]) for company in watchlist)
        ]
    
    if len(existing_updates) < 3:
        fallback_updates = read_json_list(TARGET_UPDATES_FALLBACK_FILE)
        if fallback_updates:
            payload['targetUpdates'] = fallback_updates

    meta = payload.get('meta') if isinstance(payload.get('meta'), dict) else {}
    fallback_watchlist = read_json_list(TARGET_WATCHLIST_FALLBACK_FILE)
    if fallback_watchlist:
        meta['targetWatchlist'] = fallback_watchlist
    payload['meta'] = meta
    return payload


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def list_targets(target_settings: dict[str, Any]) -> list[str]:
    if isinstance(target_settings.get('targets'), list):
        return [item.get('name') for item in target_settings['targets'] if item.get('enabled') and item.get('name')]
    result: list[str] = []
    for key in ['companies', 'industries', 'keywords', 'regions']:
        result.extend(target_settings.get(key, []))
    return result


def build_llm_summary(today: dict[str, Any], targets: dict[str, Any], prompts: dict[str, Any]) -> dict[str, Any]:
    if LLM_PROVIDER != 'deepseek' or not llm_client.enabled:
        return {
            'enabled': False,
            'provider': LLM_PROVIDER,
            'model': LLM_MODEL,
            'summary': None,
            'reason': 'deepseek_not_enabled',
        }

    system_prompt = prompts.get('newsSummaryPrompt') or '请将输入整理成适合CEO快速阅读的中文摘要。'
    user_prompt = json.dumps(
        {
            'targets': targets,
            'today': today,
        },
        ensure_ascii=False,
    )
    result = llm_client.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2)
    return {
        'enabled': True,
        'provider': result['provider'],
        'model': result['model'],
        'summary': result['content'],
    }


def fetch_market_snapshot() -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    for config in MARKET_SYMBOLS:
        resolved = None
        for candidate in config['stooq']:
            try:
                url = f"https://stooq.com/q/l/?s={urllib.parse.quote(candidate)}&i=d"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    text = resp.read().decode('utf-8').strip()
                parts = text.split(',')
                if len(parts) >= 8 and parts[1] != 'N/D':
                    resolved = parts
                    break
            except Exception:
                continue

        if not resolved:
            items.append({
                'symbol': config['symbol'],
                'name': config['name'],
                'price': None,
                'change': None,
                'changePercent': None,
                'currency': None,
                'marketState': 'N/A',
            })
            continue

        open_price = float(resolved[3]) if resolved[3] not in {'N/D', ''} else None
        close_price = float(resolved[6]) if resolved[6] not in {'N/D', ''} else None
        change = (close_price - open_price) if open_price is not None and close_price is not None else None
        change_percent = ((change / open_price) * 100) if change is not None and open_price not in {None, 0} else None

        items.append({
            'symbol': config['symbol'],
            'name': config['name'],
            'price': close_price,
            'change': change,
            'changePercent': change_percent,
            'currency': None,
            'marketState': 'LIVE' if resolved[2] != '230000' else 'CLOSE',
        })

    return {
        'items': items,
        'updatedAt': now_iso(),
        'source': 'Stooq',
    }


def generate_brief() -> dict[str, Any]:
    today = read_json(TODAY_FILE)
    targets = read_json(TARGET_SETTINGS_FILE)
    prompts = read_json(PROMPT_SETTINGS_FILE)
    llm_summary = build_llm_summary(today, targets, prompts)
    generated = {
        **today,
        'date': datetime.now().date().isoformat(),
        'generatedAt': now_iso(),
        'status': 'success',
        'meta': {
            'mode': 'mock-regenerated-python',
            'usedTargets': list_targets(targets),
            'promptKeys': list(prompts.keys()),
            'generatedBy': 'ceo-brief-fastapi-service',
            'llm': {
                'provider': llm_summary.get('provider'),
                'model': llm_summary.get('model'),
                'enabled': llm_summary.get('enabled', False),
            },
        },
        'llmSummary': llm_summary.get('summary'),
    }
    write_json(TODAY_FILE, generated)
    latest = {
        'ok': True,
        'generatedAt': generated['generatedAt'],
        'date': generated['date'],
        'status': generated['status'],
        'mode': generated.get('meta', {}).get('mode'),
    }
    write_json(LATEST_RUN_FILE, latest)
    return generated


ensure_json_file(TARGET_SETTINGS_FILE, DEFAULT_TARGET_SETTINGS)
ensure_json_file(PROMPT_SETTINGS_FILE, DEFAULT_PROMPT_SETTINGS)


@router.get('/health')
def health() -> dict[str, Any]:
    return {
        'ok': True,
        'service': 'ceo-brief-fastapi-service',
        'port': 8000,
        'llmProvider': LLM_PROVIDER,
        'llmModel': LLM_MODEL,
        'deepseekEnabled': llm_client.enabled,
    }


@router.get('/api/ceo-brief/today')
def today() -> dict[str, Any]:
    try:
        return merge_target_fallbacks(read_json(TODAY_FILE))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'failed_to_read_today_brief: {exc}')


@router.get('/api/ceo-brief/market-snapshot')
def market_snapshot() -> dict[str, Any]:
    try:
        return fetch_market_snapshot()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'failed_to_fetch_market_snapshot: {exc}')


@router.post('/api/ceo-brief/generate')
def generate() -> dict[str, Any]:
    try:
        generated = generate_brief()
        return {
            'ok': True,
            'message': 'ceo brief regenerated from mock baseline',
            'generatedAt': generated['generatedAt'],
            'date': generated['date'],
            'status': generated['status'],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'failed_to_generate_brief: {exc}')


@router.post('/api/ceo-brief/jobs/generate')
def jobs_generate() -> dict[str, Any]:
    try:
        generated = generate_brief()
        return {
            'ok': True,
            'generatedAt': generated['generatedAt'],
            'date': generated['date'],
            'status': generated['status'],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'failed_to_run_generate_job: {exc}')


@router.get('/api/ceo-brief/latest-run')
def latest_run() -> dict[str, Any]:
    if not LATEST_RUN_FILE.exists():
        raise HTTPException(status_code=404, detail='latest_run_not_found')
    return read_json(LATEST_RUN_FILE)


@router.get('/api/ceo-brief/latest-brief')
def latest_brief() -> dict[str, Any]:
    if not LATEST_MD_FILE.exists():
        raise HTTPException(status_code=404, detail='latest_brief_not_found')
    return {
        'ok': True,
        'path': str(LATEST_MD_FILE),
        'content': LATEST_MD_FILE.read_text(encoding='utf-8'),
    }


@router.get('/api/ceo-brief/latest-debug-snapshot')
def latest_debug_snapshot() -> dict[str, Any]:
    if not DEBUG_SNAPSHOT_FILE.exists():
        raise HTTPException(status_code=404, detail='latest_debug_snapshot_not_found')
    return read_json(DEBUG_SNAPSHOT_FILE)


@router.get('/api/ceo-brief/settings/targets')
def get_targets() -> dict[str, Any]:
    settings = read_json(TARGET_SETTINGS_FILE)
    watchlist = read_json_list(TARGET_WATCHLIST_FALLBACK_FILE)
    if watchlist:
        settings['watchlist'] = watchlist
    return settings


@router.put('/api/ceo-brief/settings/targets')
def put_targets(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        payload = {}
    # Save watchlist to its own file if present
    watchlist = payload.pop('watchlist', None)
    if watchlist is not None:
        write_json(TARGET_WATCHLIST_FALLBACK_FILE, watchlist)
    write_json(TARGET_SETTINGS_FILE, payload)
    return {'ok': True}


@router.get('/api/ceo-brief/settings/prompts')
def get_prompts() -> dict[str, Any]:
    return read_json(PROMPT_SETTINGS_FILE)


@router.put('/api/ceo-brief/settings/prompts')
def put_prompts(payload: dict[str, Any]) -> dict[str, Any]:
    write_json(PROMPT_SETTINGS_FILE, payload or {})
    return {'ok': True}


@router.post('/api/ceo-brief/settings/prompts/reset')
def reset_prompts() -> dict[str, Any]:
    write_json(PROMPT_SETTINGS_FILE, DEFAULT_PROMPT_SETTINGS)
    return {'ok': True, 'data': DEFAULT_PROMPT_SETTINGS}


@router.get('/api/ceo-brief/llm/status')
def llm_status() -> dict[str, Any]:
    return {
        'ok': True,
        'provider': LLM_PROVIDER,
        'model': LLM_MODEL,
        'enabled': llm_client.enabled,
        'baseUrlConfigured': bool(os.getenv('DEEPSEEK_BASE_URL', '').strip()),
    }


@router.post('/api/ceo-brief/llm/test')
def llm_test() -> dict[str, Any]:
    if LLM_PROVIDER != 'deepseek' or not llm_client.enabled:
        raise HTTPException(status_code=400, detail='deepseek_not_enabled')
    try:
        result = llm_client.chat(
            system_prompt='你是投后CEO参阅助手。请简短回答。',
            user_prompt='请用一句中文确认你已连接成功，并说明你是 DeepSeek。',
            temperature=0.1,
        )
        return {
            'ok': True,
            'provider': result['provider'],
            'model': result['model'],
            'content': result['content'],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'llm_test_failed: {exc}')


@router.get('/api/ceo-brief/sources/searxng/status')
def searxng_status() -> dict[str, Any]:
    return {
        'ok': True,
        'enabled': news_pipeline.searxng.enabled,
        'baseUrlConfigured': bool(os.getenv('SEARXNG_BASE_URL', '').strip()),
        'defaultLanguage': os.getenv('SEARXNG_LANGUAGE', 'zh-CN').strip(),
        'defaultTimeRange': os.getenv('SEARXNG_TIME_RANGE', 'day').strip(),
        'defaultCategories': os.getenv('SEARXNG_CATEGORIES', 'news').strip(),
    }


@router.post('/api/ceo-brief/ingest/news')
def ingest_news() -> dict[str, Any]:
    if not news_pipeline.searxng.enabled:
        raise HTTPException(status_code=400, detail='searxng_not_enabled')
    try:
        targets = read_json(TARGET_SETTINGS_FILE)
        candidates = news_pipeline.collect_candidates(targets, top_k=10)
        return {
            'ok': True,
            'queries': candidates['queries'],
            'count': len(candidates['items']),
            'items': candidates['items'],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'ingest_news_failed: {exc}')


@router.post('/api/ceo-brief/ingest/news/summary')
def summarize_news() -> dict[str, Any]:
    if not news_pipeline.searxng.enabled:
        raise HTTPException(status_code=400, detail='searxng_not_enabled')
    try:
        targets = read_json(TARGET_SETTINGS_FILE)
        prompts = read_json(PROMPT_SETTINGS_FILE)
        candidates = news_pipeline.collect_candidates(targets, top_k=10)
        summary = news_pipeline.summarize_candidates(candidates, prompts.get('newsSummaryPrompt'))
        return {
            'ok': True,
            'queries': candidates['queries'],
            'count': len(candidates['items']),
            'items': candidates['items'],
            'summary': summary,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'summarize_news_failed: {exc}')


@router.get('/api/ceo-brief/sources/free/status')
def free_sources_status() -> dict[str, Any]:
    return {
        'ok': True,
        'rss': True,
        'googleNewsRss': True,
        'jinaEnabled': free_news_pipeline.jina.enabled,
        'deepseekEnabled': free_news_pipeline.llm.enabled,
        'searxngEnabled': free_news_pipeline.searxng.enabled,
        'rsshubEnabled': env_flag('CEO_BRIEF_ENABLE_RSSHUB', default=True),
        'rsshubBaseUrl': os.getenv('RSSHUB_BASE_URL', 'https://rss.whyx.site:8443').rstrip('/'),
    }


@router.post('/api/ceo-brief/ingest/free/rss')
def ingest_free_rss() -> dict[str, Any]:
    try:
        payload = free_news_pipeline.collect_rss(limit_per_feed=5)
        return {
            'ok': True,
            'sources': payload['sources'],
            'count': len(payload['items']),
            'items': payload['items'],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'ingest_free_rss_failed: {exc}')


@router.post('/api/ceo-brief/ingest/free/google-news')
def ingest_free_google_news() -> dict[str, Any]:
    try:
        targets = read_json(TARGET_SETTINGS_FILE)
        payload = free_news_pipeline.collect_google_news(targets, limit_per_query=4)
        return {
            'ok': True,
            'queries': payload['queries'],
            'count': len(payload['items']),
            'items': payload['items'],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'ingest_free_google_news_failed: {exc}')


@router.post('/api/ceo-brief/ingest/free/summary')
def ingest_free_summary() -> dict[str, Any]:
    try:
        targets = read_json(TARGET_SETTINGS_FILE)
        prompts = read_json(PROMPT_SETTINGS_FILE)
        rss_payload = free_news_pipeline.collect_rss(limit_per_feed=4)
        google_payload = free_news_pipeline.collect_google_news(targets, limit_per_query=3)
        merged_items = rss_payload['items'] + google_payload['items']
        enriched_items = free_news_pipeline.enrich_with_jina(merged_items, top_k=3)
        summary = free_news_pipeline.summarize(enriched_items, prompts.get('newsSummaryPrompt'))
        return {
            'ok': True,
            'count': len(enriched_items),
            'items': enriched_items,
            'summary': summary,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'ingest_free_summary_failed: {exc}')


@router.post('/api/ceo-brief/generate/free')
def generate_free_brief() -> dict[str, Any]:
    try:
        targets = read_json(TARGET_SETTINGS_FILE)
        prompts = read_json(PROMPT_SETTINGS_FILE)
        today_existing = read_json(TODAY_FILE)

        pipeline_mode = os.getenv('CEO_BRIEF_PIPELINE_MODE', 'stable').strip().lower()
        enable_google = env_flag('CEO_BRIEF_ENABLE_GOOGLE_NEWS', default=False) and pipeline_mode != 'stable'
        enable_policy_google = env_flag('CEO_BRIEF_ENABLE_POLICY_GOOGLE', default=False) and pipeline_mode != 'stable'
        enable_competitor_google = env_flag('CEO_BRIEF_ENABLE_COMPETITOR_GOOGLE', default=False) and pipeline_mode != 'stable'
        enable_llm_summary = env_flag('CEO_BRIEF_ENABLE_LLM_SUMMARY', default=True)
        jina_top_k = 0 if pipeline_mode == 'stable' else int(os.getenv('CEO_BRIEF_JINA_TOP_K', '1'))

        space_hints = ['航天', '卫星', '火箭', '遥感', '测运控', '星座']
        use_space_sources = any(any(hint in str(v) for hint in space_hints) for v in (
            (targets.get('companies', []) or [])
            + (targets.get('industries', []) or [])
            + (targets.get('keywords', []) or [])
            + (targets.get('competitors', []) or [])
            + (targets.get('upstreamDownstream', []) or [])
        ))

        rss_payload = free_news_pipeline.collect_rss(
            limit_per_feed=5 if pipeline_mode == 'stable' else 4,
            extra_sources=SPACE_RSS_SOURCES if use_space_sources else None,
        )

        if enable_google:
            google_payload = free_news_pipeline.collect_google_news(targets, limit_per_query=1)
        else:
            google_payload = {'queries': [], 'queryStats': [], 'items': []}

        enable_searxng = free_news_pipeline.searxng.enabled

        # Always search Watchlist companies via Google News (free RSS, no API key)
        watchlist_companies = read_json_list(TARGET_WATCHLIST_FALLBACK_FILE)
        google_watchlist_items: list[dict[str, Any]] = []
        if watchlist_companies:
            google_watchlist_seen: set[str] = set()
            for company in watchlist_companies[:16]:
                try:
                    result = free_news_pipeline.rss.parse_google_news(company, limit=2)
                    for item in result.get('items', []):
                        url = str(item.get('url') or '').strip()
                        if url and url not in google_watchlist_seen:
                            google_watchlist_seen.add(url)
                            google_watchlist_items.append({**item, 'sourceType': 'google-news-rss', 'matchedTargets': [company]})
                except Exception:
                    continue
        google_watchlist_payload = {'items': google_watchlist_items}

        if enable_searxng:
            searxng_targets = dict(targets)
            if watchlist_companies:
                searxng_targets['watchlist'] = watchlist_companies
            searxng_payload = free_news_pipeline.collect_searxng_news(searxng_targets, limit_per_query=2)
        else:
            searxng_payload = {'queries': [], 'queryStats': [], 'items': [], 'enabled': False}

        merged_payload = free_news_pipeline.merge_and_dedup(
            rss_payload['items'],
            google_payload['items'],
        )
        merged_items = merged_payload['items']
        searxng_items = searxng_payload.get('items', [])

        policy_payload = free_news_pipeline.collect_policy_news(targets, limit_per_query=4)
        policy_ranked = policy_payload['items'][:15]
        if len(policy_ranked) < 10:
            policy_ranked = free_news_pipeline.merge_and_dedup(
                policy_ranked,
                filter_policy_items(merged_items, hints=['政策', '国务院', '工信部', '发改委', '卫星互联网', '商业航天', '新华社', '外交', '国际', '冲突', '局势', '中东', '伊朗', '俄乌', '欧盟', '关税', '经贸'])[:15],
            ).get('items', [])[:15]

        if enable_competitor_google:
            competitor_payload = free_news_pipeline.collect_competitor_news(targets, limit_per_query=1)
            competitor_ranked = free_news_pipeline.rank_for_targets(competitor_payload['items'], targets, top_k=3)
        else:
            competitor_payload = {'queries': [], 'items': []}
            competitor_ranked = []

        industry_focus_candidates = filter_space_industry_items(merged_items)
        space_priority_terms = ['中科天塔', '星载', '激光通信', '通信终端', '天地一体', '卫星测控', '商业航天']
        space_priority_candidates = [
            item for item in merged_items
            if any(
                term in ' '.join([
                    str(item.get('title') or ''),
                    str(item.get('content') or ''),
                    str(item.get('articleText') or ''),
                    str(item.get('source') or ''),
                ])
                for term in space_priority_terms
            )
        ]
        industry_focus_candidates = free_news_pipeline.merge_and_dedup(
            space_priority_candidates,
            industry_focus_candidates,
        ).get('items', [])
        if len(industry_focus_candidates) < 15:
            industry_focus_candidates = free_news_pipeline.merge_and_dedup(
                industry_focus_candidates,
                [
                    item for item in merged_items
                    if str(item.get('source') or '').strip() in {'SpaceNews', 'NASA Breaking News', 'ESA Top News', 'Space.com'}
                ][:18],
            ).get('items', [])

        excluded_for_macro = free_news_pipeline.merge_and_dedup(policy_ranked, industry_focus_candidates).get('items', [])
        macro_candidates = exclude_items(filter_macro_items(merged_items), excluded_for_macro)
        if len(macro_candidates) < 15:
            excluded_urls = {str(item.get('url') or '').strip() for item in excluded_for_macro if item.get('url')}
            fallback_macro = [
                item for item in merged_items
                if str(item.get('url') or '').strip() not in excluded_urls
            ]
            macro_candidates = free_news_pipeline.merge_and_dedup(macro_candidates, fallback_macro[:24]).get('items', [])
        macro_items = macro_candidates[:15]
        if len(policy_ranked) < 15:
            policy_fallback = filter_policy_items(
                [item for item in merged_items if item not in macro_items]
            )[:12]
            policy_ranked = free_news_pipeline.merge_and_dedup(
                policy_ranked,
                policy_fallback,
            ).get('items', [])[:15]
        rss_target_matches = free_news_pipeline.rank_for_targets(merged_items, targets, top_k=8)
        searxng_target_matches = free_news_pipeline.rank_for_targets(searxng_items, targets, top_k=8)
        # Rank Google News watchlist results — these are already target-specific by design
        google_watchlist_items = google_watchlist_payload.get('items', [])
        # Rank Google News watchlist results — add all watchlist companies to ranking targets
        ranking_targets = dict(targets)
        if watchlist_companies:
            ranking_targets['watchlist_companies'] = watchlist_companies
            existing_competitors = list(ranking_targets.get('competitors', []))
            for c in watchlist_companies:
                if c not in existing_competitors:
                    existing_competitors.append(c)
            ranking_targets['competitors'] = existing_competitors
        google_watchlist_matches = free_news_pipeline.rank_for_targets(google_watchlist_items, ranking_targets, top_k=16)
        target_candidates = free_news_pipeline.merge_and_dedup(rss_target_matches, searxng_target_matches, google_watchlist_matches, max_days=7).get('items', [])
        enriched_items = free_news_pipeline.enrich_with_jina(target_candidates, top_k=jina_top_k)
        industry_focus_items = free_news_pipeline.enrich_with_jina(industry_focus_candidates[:15], top_k=jina_top_k)

        generated = build_ceo_brief_from_free_news(
            items=enriched_items,
            target_updates_items=enriched_items,
            summary_text=None,
            existing_today=today_existing,
            policy_items=policy_ranked,
            competitor_items=competitor_ranked,
            macro_items=macro_items,
            industry_focus_items=industry_focus_items,
        )

        if enable_llm_summary:
            free_summary_prompt = (
                '你是产业投资/投后场景里的 CEO 每日参阅助手。请严格根据输入新闻生成中文摘要。'
                '不要输出示例、占位符或模板说明。请聚焦产业、资本、供应链、技术落地和商业化影响。'
                '请输出三段：今日重点、影响判断、建议动作。'
            )
            summary_inputs = (macro_items[:2] + industry_focus_items[:2] + enriched_items[:2] + policy_ranked[:2] + competitor_ranked[:2])
            try:
                summary = free_news_pipeline.summarize(summary_inputs, free_summary_prompt)
                if summary.get('summary'):
                    generated['llmSummary'] = summary.get('summary')
            except Exception as summary_exc:
                generated.setdefault('meta', {})['summaryError'] = str(summary_exc)

        generated = merge_target_fallbacks(generated)

        generated.setdefault('meta', {})['targetMatchRssCount'] = len(rss_target_matches)
        generated['meta']['targetMatchSearxngCount'] = len(searxng_target_matches)
        generated['meta']['targetMatchGoogleCount'] = len(google_watchlist_matches)
        generated['meta']['targetMatchTotalCount'] = len(target_candidates)
        generated['meta']['policyMatchCount'] = len(policy_ranked)
        generated['meta']['competitorMatchCount'] = len(competitor_ranked)
        generated['meta']['strictMode'] = True
        diagnostics = free_news_pipeline.source_diagnostics(merged_items)

        generated['meta']['pipelineMode'] = pipeline_mode
        generated['meta']['googleEnabled'] = enable_google
        generated['meta']['searxngEnabled'] = enable_searxng
        generated['meta']['llmSummaryEnabled'] = enable_llm_summary
        generated['meta']['rsshubEnabled'] = env_flag('CEO_BRIEF_ENABLE_RSSHUB', default=True)
        generated['meta']['rsshubBaseUrl'] = os.getenv('RSSHUB_BASE_URL', 'https://rss.whyx.site:8443').rstrip('/')
        generated['meta']['mergedItemCount'] = len(merged_items)
        generated['meta']['droppedDuplicates'] = merged_payload.get('droppedDuplicates', 0)
        generated['meta']['countsByOrigin'] = diagnostics.get('countsByOrigin', {})
        generated['meta']['host'] = socket.gethostname()

        write_json(TODAY_FILE, generated)

        macro_news_generated = generated.get('macroEconomicNews') or []
        industry_focus_generated = generated.get('industryFocusNews') or []

        write_json(DEBUG_SNAPSHOT_FILE, {
            'generatedAt': generated.get('generatedAt'),
            'meta': generated.get('meta', {}),
            'rssSources': rss_payload.get('sources', []),
            'rssSourceStats': rss_payload.get('sourceStats', []),
            'googleQueryStats': google_payload.get('queryStats', []),
            'searxngQueryStats': searxng_payload.get('queryStats', []),
            'mergedItemsCount': len(merged_items),
            'droppedDuplicates': merged_payload.get('droppedDuplicates', 0),
            'macroEconomicNewsCount': len(macro_news_generated),
            'industryFocusNewsCount': len(industry_focus_generated),
            'policyNewsCount': len(generated.get('policyNews', [])),
            'competitorNewsCount': len(generated.get('competitorNews', [])),
            'rssTargetMatchesCount': len(rss_target_matches),
            'searxngTargetMatchesCount': len(searxng_target_matches),
            'macroItemsCount': len(macro_items),
            'industryFocusItemsCount': len(industry_focus_items),
            'policyRankedCount': len(policy_ranked),
            'competitorRankedCount': len(competitor_ranked),
            'firstRssTargetMatch': rss_target_matches[0] if rss_target_matches else None,
            'firstSearxngTargetMatch': searxng_target_matches[0] if searxng_target_matches else None,
            'firstMacroItem': macro_news_generated[0] if macro_news_generated else None,
            'firstIndustryFocusItem': industry_focus_generated[0] if industry_focus_generated else None,
        })

        write_json(LATEST_RUN_FILE, {
            'ok': True,
            'generatedAt': generated['generatedAt'],
            'date': generated['date'],
            'status': generated['status'],
            'mode': 'free-news-pipeline',
        })
        ensure_dir(LATEST_MD_FILE.parent)
        LATEST_MD_FILE.write_text(build_brief_markdown(generated), encoding='utf-8')

        return {
            'ok': True,
            'message': 'ceo brief generated from free news pipeline',
            'generatedAt': generated['generatedAt'],
            'date': generated['date'],
            'status': generated['status'],
            'newsCount': len(generated.get('macroEconomicNews', [])) + len(generated.get('industryFocusNews', [])),
            'policyNewsCount': len(generated.get('policyNews', [])),
            'competitorNewsCount': len(generated.get('competitorNews', [])),
            'targetMatchTotalCount': generated.get('meta', {}).get('targetMatchTotalCount', 0),
            'mergedItemCount': generated.get('meta', {}).get('mergedItemCount', 0),
            'countsByOrigin': generated.get('meta', {}).get('countsByOrigin', {}),
            'llmSummary': generated.get('llmSummary'),
            'markdownPath': str(LATEST_MD_FILE),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'generate_free_brief_failed: {exc}')



