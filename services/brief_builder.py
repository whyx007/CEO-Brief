from __future__ import annotations

import re
from html import unescape
from datetime import datetime, timezone, timedelta
from typing import Any


def now_iso() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz=tz).replace(microsecond=0).isoformat()


def _strip_html(value: str) -> str:
    text = unescape(value or '')
    text = text.replace('���', ' ').replace('�', ' ')
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _normalize_news_item(item: dict[str, Any], index: int, prefix: str) -> dict[str, Any] | None:
    title = _strip_html((item.get('title') or '').strip())
    url = (item.get('url') or '').strip()
    raw_summary = (item.get('articleText') or item.get('content') or '').strip()
    summary = _strip_html(raw_summary)
    if not title or not url:
        return None
    normalized = {
        'id': f'{prefix}_{index:03d}',
        'title': title,
        'source': item.get('source') or item.get('query') or 'unknown',
        'summary': summary[:500],
        'url': url,
        'publishedAt': item.get('publishedDate'),
        'imageUrl': item.get('imageUrl'),
    }
    if item.get('matchedTargets'):
        normalized['matchedTargets'] = item.get('matchedTargets')
    if item.get('relevanceReason'):
        normalized['relevanceReason'] = item.get('relevanceReason')
    if item.get('relevanceScore') is not None:
        normalized['relevanceScore'] = item.get('relevanceScore')
    return normalized


def _contains_chinese(text: str) -> bool:
    return any('\u4e00' <= ch <= '\u9fff' for ch in text or '')


def _prefer_chinese_first(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> tuple[int, int]:
        text = ' '.join([
            str(item.get('title') or ''),
            str(item.get('content') or ''),
            str(item.get('articleText') or ''),
        ])
        return (0 if _contains_chinese(text) else 1, 0)
    return sorted(items or [], key=sort_key)


def build_ceo_brief_from_free_news(*, items: list[dict[str, Any]], summary_text: str | None, existing_today: dict[str, Any] | None = None, policy_items: list[dict[str, Any]] | None = None, competitor_items: list[dict[str, Any]] | None = None, macro_items: list[dict[str, Any]] | None = None, industry_focus_items: list[dict[str, Any]] | None = None, target_updates_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    existing_today = existing_today or {}

    macro_news: list[dict[str, Any]] = []
    for index, item in enumerate(_prefer_chinese_first(macro_items or [])[:15], start=1):
        normalized = _normalize_news_item(item, index, 'macro_news')
        if normalized:
            macro_news.append(normalized)

    industry_focus_news: list[dict[str, Any]] = []
    for index, item in enumerate(_prefer_chinese_first(industry_focus_items or items or [])[:15], start=1):
        normalized = _normalize_news_item(item, index, 'industry_news')
        if normalized:
            industry_focus_news.append(normalized)

    policy_news: list[dict[str, Any]] = []
    for index, item in enumerate(_prefer_chinese_first(policy_items or [])[:15], start=1):
        normalized = _normalize_news_item(item, index, 'policy_news')
        if normalized:
            policy_news.append(normalized)

    competitor_news: list[dict[str, Any]] = []
    for index, item in enumerate(_prefer_chinese_first(competitor_items or [])[:15], start=1):
        normalized = _normalize_news_item(item, index, 'competitor_news')
        if normalized:
            competitor_news.append(normalized)

    todo_items = existing_today.get('todoItems') or [
        '复核今日重点新闻与被投企业/行业的关联度',
        '对高影响事件安排进一步人工核查',
        '确认是否需要生成面向CEO的专项提醒',
    ]

    weather = existing_today.get('weather') or {
        'location': '中科天塔所在地',
        'condition': '待接入真实天气数据',
        'temperatureMin': '--',
        'temperatureMax': '--',
        'advice': '默认使用目标公司所在地天气',
    }
    if not weather.get('location'):
        weather['location'] = '中科天塔所在地'

    if target_updates_items:
        target_updates = []
        for index, item in enumerate(target_updates_items[:10], start=1):
            normalized = _normalize_news_item(item, index, 'target_update')
            if normalized:
                target_updates.append(normalized)
    else:
        target_updates = []

    result = {
        'date': datetime.now().date().isoformat(),
        'generatedAt': now_iso(),
        'status': 'success',
        'macroEconomicNews': macro_news,
        'industryFocusNews': industry_focus_news,
        'targetUpdates': target_updates,
        'todoItems': todo_items,
        'weather': weather,
        'llmSummary': summary_text,
        'meta': {
            'mode': 'free-news-pipeline',
            'newsCount': len(macro_news) + len(industry_focus_news),
            'generatedBy': 'ceo-brief-fastapi-service',
        },
    }
    if policy_news:
        result['policyNews'] = policy_news
    if competitor_news:
        result['competitorNews'] = competitor_news
    return result
