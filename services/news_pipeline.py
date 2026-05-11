from __future__ import annotations

import json
from typing import Any

from services.llm_client import DeepSeekClient
from services.searxng_client import SearXNGClient


class NewsPipeline:
    def __init__(self) -> None:
        self.searxng = SearXNGClient()
        self.llm = DeepSeekClient()

    def build_queries(self, target_settings: dict[str, Any]) -> list[str]:
        companies = target_settings.get('companies', []) or []
        industries = target_settings.get('industries', []) or []
        keywords = target_settings.get('keywords', []) or []
        regions = target_settings.get('regions', []) or []

        queries: list[str] = []
        for company in companies[:5]:
            queries.append(f'{company} 最新进展')
            for keyword in keywords[:3]:
                queries.append(f'{company} {keyword}')
        for industry in industries[:5]:
            queries.append(f'{industry} 政策')
            queries.append(f'{industry} 供应链')
            for region in regions[:2]:
                queries.append(f'{region} {industry}')

        # 去重保序
        seen: set[str] = set()
        result: list[str] = []
        for query in queries:
            if query not in seen:
                seen.add(query)
                result.append(query)
        return result[:12]

    def collect_candidates(self, target_settings: dict[str, Any], top_k: int = 10) -> dict[str, Any]:
        queries = self.build_queries(target_settings)
        all_items: list[dict[str, Any]] = []
        seen_links: set[str] = set()

        for query in queries:
            payload = self.searxng.search(query)
            for item in payload.get('results', []):
                link = item.get('url') or item.get('link') or ''
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                all_items.append({
                    'query': query,
                    'title': item.get('title'),
                    'url': link,
                    'content': item.get('content') or item.get('snippet'),
                    'engine': item.get('engine'),
                    'publishedDate': item.get('publishedDate') or item.get('published_date'),
                })
                if len(all_items) >= top_k:
                    return {'queries': queries, 'items': all_items}

        return {'queries': queries, 'items': all_items}

    def summarize_candidates(self, candidates: dict[str, Any], prompt: str | None = None) -> dict[str, Any]:
        if not self.llm.enabled:
            return {
                'enabled': False,
                'provider': 'deepseek',
                'summary': None,
                'reason': 'deepseek_not_enabled',
            }

        system_prompt = prompt or '你是投后CEO参阅助手。请基于候选新闻，输出结构化中文摘要，突出重要变化、影响和建议关注点。'
        user_prompt = json.dumps(candidates, ensure_ascii=False)
        result = self.llm.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2)
        return {
            'enabled': True,
            'provider': result['provider'],
            'model': result['model'],
            'summary': result['content'],
        }
