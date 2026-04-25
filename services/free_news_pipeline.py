from __future__ import annotations

import os
from typing import Any

from services.filters import filter_business_items, filter_policy_items
from services.jina_client import JinaReaderClient
from services.llm_client import DeepSeekClient
from services.policy_sources import POLICY_RSS_SOURCES
from services.relevance import rank_news_items
from services.rss_client import DEFAULT_RSS_SOURCES, RSSClient
from services.rsshub_sources import build_rsshub_sources
from services.searxng_client import SearXNGClient
from services.space_sources import SPACE_QUERY_HINTS, SPACE_RSS_SOURCES


class FreeNewsPipeline:
    def __init__(self) -> None:
        self.rss = RSSClient()
        self.jina = JinaReaderClient()
        self.llm = DeepSeekClient()
        self.searxng = SearXNGClient()

    def build_queries(self, target_settings: dict[str, Any]) -> list[str]:
        companies = target_settings.get('companies', []) or []
        industries = target_settings.get('industries', []) or []
        keywords = target_settings.get('keywords', []) or []
        competitors = target_settings.get('competitors', []) or []
        upstream_downstream = target_settings.get('upstreamDownstream', []) or []

        result: list[str] = []

        for company in companies[:5]:
            result.append(company)
            for keyword in keywords[:4]:
                result.append(f'{company} {keyword}')

        for industry in industries[:5]:
            result.append(industry)
            result.append(f'{industry} 政策')
            result.append(f'{industry} 融资')
            result.append(f'{industry} 发射')
            result.append(f'{industry} 卫星')

        for competitor in competitors[:5]:
            result.append(competitor)
            for keyword in keywords[:2]:
                result.append(f'{competitor} {keyword}')

        for item in upstream_downstream[:5]:
            result.append(item)
            result.append(f'{item} 商业航天')

        space_hints = ['航天', '卫星', '火箭', '遥感', '测运控', '星座']
        if any(any(hint in str(v) for hint in space_hints) for v in (companies + industries + keywords + competitors + upstream_downstream)):
            result.extend(SPACE_QUERY_HINTS)

        seen: set[str] = set()
        dedup: list[str] = []
        for item in result:
            normalized = str(item or '').strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                dedup.append(normalized)
        return dedup[:24]

    def collect_rss(self, limit_per_feed: int = 5, extra_sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        source_stats: list[dict[str, Any]] = []

        use_rsshub = os.getenv('CEO_BRIEF_ENABLE_RSSHUB', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
        rsshub_sources = build_rsshub_sources() if use_rsshub else []
        sources = [*DEFAULT_RSS_SOURCES, *rsshub_sources, *(extra_sources or [])]

        import concurrent.futures

        def _fetch_one(source: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
            remote_timeout = float(os.getenv('RSS_REQUEST_TIMEOUT_SECONDS', '4'))
            if 'RSSHub ' in source.get('name', ''):
                remote_timeout = float(os.getenv('RSSHUB_TIMEOUT_SECONDS', '5'))
            try:
                self.rss.timeout_seconds = remote_timeout
                parsed = self.rss.parse_feed(source['url'], source_name=source['name'], limit=limit_per_feed)
            except Exception:
                parsed = []
            return source, parsed

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(_fetch_one, sources))

        for source, parsed_items in results:
            kept = 0
            for item in parsed_items:
                url = item.get('url') or ''
                title = item.get('title') or ''
                if not url or not title or url in seen_urls:
                    continue
                seen_urls.add(url)
                kept += 1
                items.append({**item, 'origin': 'rss', 'sourceType': 'rss'})
            source_stats.append({
                'name': source['name'],
                'url': source['url'],
                'origin': 'rsshub' if 'RSSHub ' in source['name'] else 'rss',
                'fetchedCount': len(parsed_items),
                'keptCount': kept,
            })
        return {'sources': sources, 'sourceStats': source_stats, 'items': items}

    def collect_google_news(self, target_settings: dict[str, Any], limit_per_query: int = 4) -> dict[str, Any]:
        queries = self.build_queries(target_settings)
        items: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        query_stats: list[dict[str, Any]] = []
        for query in queries:
            payload = self.rss.parse_google_news(query, limit=limit_per_query)
            kept = 0
            for item in payload['items']:
                url = item.get('url') or ''
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                kept += 1
                items.append({**item, 'query': query, 'origin': 'google-news-rss', 'sourceType': 'google-news-rss'})
            query_stats.append({'query': query, 'fetchedCount': len(payload['items']), 'keptCount': kept})
        return {'queries': queries, 'queryStats': query_stats, 'items': items}

    def collect_searxng_news(self, target_settings: dict[str, Any], limit_per_query: int = 3) -> dict[str, Any]:
        queries = self.build_queries(target_settings)
        items: list[dict[str, Any]] = []
        query_stats: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        if not self.searxng.enabled:
            return {'queries': queries, 'queryStats': [], 'items': [], 'enabled': False}

        for query in queries[:12]:
            try:
                payload = self.searxng.search(query)
                results = payload.get('results', [])[:limit_per_query]
                kept = 0
                for item in results:
                    link = item.get('url') or item.get('link') or ''
                    title = item.get('title') or ''
                    if not link or not title or link in seen_urls:
                        continue
                    seen_urls.add(link)
                    kept += 1
                    items.append({
                        'query': query,
                        'title': title,
                        'url': link,
                        'content': item.get('content') or item.get('snippet'),
                        'source': item.get('engine') or 'SearXNG',
                        'engine': item.get('engine'),
                        'publishedDate': item.get('publishedDate') or item.get('published_date'),
                        'origin': 'searxng',
                        'sourceType': 'search',
                    })
                query_stats.append({'query': query, 'fetchedCount': len(results), 'keptCount': kept, 'ok': True})
            except Exception as exc:
                query_stats.append({'query': query, 'fetchedCount': 0, 'keptCount': 0, 'ok': False, 'error': str(exc)})
        return {'queries': queries[:12], 'queryStats': query_stats, 'items': items, 'enabled': True}

    def collect_policy_news(self, target_settings: dict[str, Any], limit_per_query: int = 3) -> dict[str, Any]:
        queries = ['伊朗 冲突', '俄乌 冲突', '中东 局势', '国际 时政', '国务院 最新 政策']
        space_hints = ['航天', '卫星', '火箭', '遥感', '测运控', '星座']
        if any(any(hint in str(v) for hint in space_hints) for v in (
            (target_settings.get('companies', []) or [])
            + (target_settings.get('industries', []) or [])
            + (target_settings.get('keywords', []) or [])
            + (target_settings.get('competitors', []) or [])
            + (target_settings.get('upstreamDownstream', []) or [])
        )):
            queries.extend(['国家航天 政策', '卫星互联网 政策', '商业航天 政策', '遥感 政策'])
        items: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for source in POLICY_RSS_SOURCES:
            for item in self.rss.parse_feed(source['url'], source_name=source['name'], limit=limit_per_query):
                url = item.get('url') or ''
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    items.append({**item, 'origin': 'policy-rss', 'sourceType': 'policy-rss'})
        for query in queries:
            payload = self.rss.parse_google_news(query, limit=1)
            for item in payload['items']:
                url = item.get('url') or ''
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    items.append({**item, 'query': query, 'origin': 'policy-google-news-rss', 'sourceType': 'policy-google-news-rss'})
        filtered = filter_policy_items(items)
        return {'queries': queries, 'items': filtered}

    def collect_competitor_news(self, target_settings: dict[str, Any], limit_per_query: int = 2) -> dict[str, Any]:
        queries = []
        for name in target_settings.get('competitors', []) or []:
            queries.append(name)
        for name in target_settings.get('upstreamDownstream', []) or []:
            queries.append(name)
        items: list[dict[str, Any]] = []
        for query in queries[:10]:
            payload = self.rss.parse_google_news(query, limit=limit_per_query)
            for item in payload['items']:
                items.append({**item, 'query': query, 'origin': 'competitor-google-news-rss', 'sourceType': 'competitor-google-news-rss'})
        return {'queries': queries[:10], 'items': items}

    def merge_and_dedup(self, *item_groups: list[dict[str, Any]]) -> dict[str, Any]:
        merged: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        dropped_duplicates = 0
        for group in item_groups:
            for item in group or []:
                url = str(item.get('url') or '').strip()
                title = str(item.get('title') or '').strip()
                if not url or not title:
                    continue
                if url in seen_urls:
                    dropped_duplicates += 1
                    continue
                seen_urls.add(url)
                merged.append(item)
        return {'items': merged, 'droppedDuplicates': dropped_duplicates}

    def source_diagnostics(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for item in items:
            key = str(item.get('origin') or item.get('sourceType') or item.get('source') or 'unknown')
            counts[key] = counts.get(key, 0) + 1
        return {'countsByOrigin': counts, 'total': len(items)}

    def rank_for_targets(self, items: list[dict[str, Any]], target_settings: dict[str, Any], top_k: int = 8) -> list[dict[str, Any]]:
        filtered = filter_business_items(items)
        ranked = rank_news_items(filtered, target_settings, top_k=max(top_k * 4, 16))
        source_counts: dict[str, int] = {}
        diversified: list[dict[str, Any]] = []
        for item in ranked:
            source = str(item.get('origin') or item.get('source') or '').strip() or 'unknown'
            if source_counts.get(source, 0) >= 2:
                continue
            source_counts[source] = source_counts.get(source, 0) + 1
            diversified.append(item)
            if len(diversified) >= top_k:
                break
        return diversified

    def enrich_with_jina(self, items: list[dict[str, Any]], top_k: int = 3) -> list[dict[str, Any]]:
        if not self.jina.enabled or top_k <= 0:
            return items
        enriched: list[dict[str, Any]] = []
        for item in items[:top_k]:
            try:
                article = self.jina.read_url(item['url'])
                enriched.append({**item, 'articleText': article['content']})
            except Exception as exc:
                enriched.append({**item, 'articleText': None, 'jinaError': str(exc)})
        enriched.extend(items[top_k:])
        return enriched

    def summarize(self, items: list[dict[str, Any]], prompt: str | None = None) -> dict[str, Any]:
        if not self.llm.enabled:
            return {'enabled': False, 'provider': 'deepseek', 'summary': None, 'reason': 'deepseek_not_enabled'}
        system_prompt = prompt or (
            '你是投后CEO参阅助手。请严格基于提供的新闻事实输出中文摘要，不要写占位符，不要虚构未提供的信息。'
            '请输出三部分：1）今日最重要的3条变化；2）这些变化对CEO的影响；3）建议关注动作。每部分控制在简短可读范围。'
        )
        compact_items = [
            {
                'source': item.get('source'),
                'origin': item.get('origin'),
                'query': item.get('query'),
                'title': item.get('title'),
                'url': item.get('url'),
                'content': item.get('articleText') or item.get('content'),
                'publishedDate': item.get('publishedDate'),
                'matchedTargets': item.get('matchedTargets'),
                'relevanceReason': item.get('relevanceReason'),
                'relevanceScore': item.get('relevanceScore'),
            }
            for item in items[:10]
        ]
        result = self.llm.chat(system_prompt=system_prompt, user_prompt=str(compact_items), temperature=0.2)
        return {'enabled': True, 'provider': result['provider'], 'model': result['model'], 'summary': result['content']}
