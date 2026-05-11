from __future__ import annotations

from typing import Any


def _matched_tokens(text: str, tokens: list[Any]) -> list[str]:
    matched: list[str] = []
    seen: set[str] = set()
    for token in tokens or []:
        original = str(token).strip()
        token_text = original.lower()
        if token_text and token_text in text and token_text not in seen:
            seen.add(token_text)
            matched.append(original)
    return matched


def score_news_item(item: dict[str, Any], target_settings: dict[str, Any]) -> dict[str, Any]:
    text = ' '.join([
        str(item.get('title') or ''),
        str(item.get('content') or ''),
        str(item.get('articleText') or ''),
        str(item.get('source') or ''),
        str(item.get('query') or ''),
    ]).lower()

    company_hits = _matched_tokens(text, target_settings.get('companies', []))
    industry_hits = _matched_tokens(text, target_settings.get('industries', []))
    keyword_hits = _matched_tokens(text, target_settings.get('keywords', []))
    region_hits = _matched_tokens(text, target_settings.get('regions', []))
    competitor_hits = _matched_tokens(text, target_settings.get('competitors', []))
    chain_hits = _matched_tokens(text, target_settings.get('upstreamDownstream', []))

    score = 0
    score += len(company_hits) * 8
    score += len(industry_hits) * 6
    score += len(keyword_hits) * 3
    score += len(region_hits) * 1
    score += len(competitor_hits) * 6
    score += len(chain_hits) * 4

    strong_hits = len(company_hits) + len(industry_hits) + len(competitor_hits) + len(chain_hits)
    weak_hits = len(keyword_hits) + len(region_hits)

    if strong_hits == 0:
        if keyword_hits:
            score = min(score, 2)
        else:
            score = 0

    if strong_hits == 0 and weak_hits < 2:
        score = 0

    if strong_hits > 0 and keyword_hits:
        score += 2

    matched_targets = company_hits + industry_hits + competitor_hits + chain_hits + keyword_hits + region_hits
    parts: list[str] = []
    if company_hits:
        parts.append(f"公司命中：{', '.join(company_hits[:3])}")
    if industry_hits:
        parts.append(f"行业命中：{', '.join(industry_hits[:3])}")
    if competitor_hits:
        parts.append(f"竞对命中：{', '.join(competitor_hits[:3])}")
    if chain_hits:
        parts.append(f"产业链命中：{', '.join(chain_hits[:3])}")
    if keyword_hits:
        parts.append(f"关键词命中：{', '.join(keyword_hits[:4])}")
    if region_hits:
        parts.append(f"地域命中：{', '.join(region_hits[:3])}")

    return {
        'score': score,
        'matchedTargets': matched_targets,
        'relevanceReason': '；'.join(parts) if parts else None,
        'strongHitCount': strong_hits,
        'weakHitCount': weak_hits,
    }


def rank_news_items(items: list[dict[str, Any]], target_settings: dict[str, Any], top_k: int = 8) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for item in items:
        result = score_news_item(item, target_settings)
        scored.append({
            **item,
            'relevanceScore': result['score'],
            'matchedTargets': result['matchedTargets'],
            'relevanceReason': result['relevanceReason'],
            'strongHitCount': result['strongHitCount'],
            'weakHitCount': result['weakHitCount'],
        })
    scored.sort(key=lambda x: (x.get('relevanceScore', 0), x.get('publishedDate') or ''), reverse=True)
    return [item for item in scored if item.get('relevanceScore', 0) >= 6][:top_k]
