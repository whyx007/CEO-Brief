from __future__ import annotations

import re
from html import unescape
from typing import Any


def _clean_text(value: Any) -> str:
    text = unescape(str(value or ''))
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _render_news_section(title: str, items: list[dict[str, Any]]) -> list[str]:
    lines = [f'## {title}']
    if not items:
        lines.append('（今日无）')
        lines.append('')
        return lines
    for idx, item in enumerate(items, start=1):
        lines.append(f'{idx}. **{_clean_text(item.get("title", "未命名")) }**')
        if item.get('source'):
            lines.append(f'   - 来源：{_clean_text(item.get("source"))}')
        if item.get('publishedAt'):
            lines.append(f'   - 时间：{_clean_text(item.get("publishedAt"))}')
        if item.get('summary'):
            lines.append(f'   - 摘要：{_clean_text(item.get("summary"))}')
        if item.get('url'):
            lines.append(f'   - 链接：{_clean_text(item.get("url"))}')
    lines.append('')
    return lines


def build_brief_markdown(brief: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f'# CEO参阅 - {brief.get("date", "") }')
    lines.append('')
    lines.append(f'- 生成时间：{brief.get("generatedAt", "") }')
    lines.append(f'- 状态：{brief.get("status", "") }')
    lines.append('')

    if brief.get('llmSummary'):
        lines.append('## 今日摘要')
        lines.append(_clean_text(brief.get('llmSummary')))
        lines.append('')

    policy_news = brief.get('policyNews') or []
    lines.extend(_render_news_section('时政 / 政策新闻', policy_news))

    macro_news = brief.get('macroEconomicNews') or []
    lines.extend(_render_news_section('宏观经济新闻', macro_news))

    industry_focus_news = brief.get('industryFocusNews') or []
    lines.extend(_render_news_section('商业航天产业新闻', industry_focus_news))

    competitor_news = brief.get('competitorNews') or []
    if competitor_news:
        lines.extend(_render_news_section('竞争对手 / 上下游动态', competitor_news))

    target_updates = brief.get('targetUpdates') or []
    lines.extend(_render_news_section('目标相关更新', target_updates))

    todo_items = brief.get('todoItems') or []
    lines.append('## 今日动作建议')
    if todo_items:
        for idx, item in enumerate(todo_items, start=1):
            if isinstance(item, dict):
                lines.append(f'{idx}. {_clean_text(item.get("content", "")) }')
                if item.get('reason'):
                    lines.append(f'   - 原因：{_clean_text(item.get("reason"))}')
            else:
                lines.append(f'{idx}. {_clean_text(item)}')
    else:
        lines.append('（今日无）')
    lines.append('')

    weather = brief.get('weather') or {}
    if weather:
        lines.append('## 天气')
        for key, value in weather.items():
            lines.append(f'- {_clean_text(key)}: {_clean_text(value)}')
        lines.append('')

    return '\n'.join(lines).strip() + '\n'
