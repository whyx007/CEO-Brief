from __future__ import annotations

import os
import urllib.parse
from pathlib import Path
from typing import Any

import feedparser
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')


DEFAULT_RSS_SOURCES = [
    {'name': '36Kr', 'url': 'https://36kr.com/feed'},
    {'name': 'Reuters Business', 'url': 'https://feeds.reuters.com/reuters/businessNews'},
    {'name': 'Reuters World', 'url': 'https://feeds.reuters.com/Reuters/worldNews'},
    {'name': 'TechCrunch', 'url': 'https://techcrunch.com/feed/'},
    {'name': 'VentureBeat AI', 'url': 'https://venturebeat.com/category/ai/feed/'},
]


class RSSClient:
    def __init__(self) -> None:
        self.max_items = int(os.getenv('RSS_MAX_ITEMS', '20'))
        self.timeout_seconds = float(os.getenv('RSS_REQUEST_TIMEOUT_SECONDS', '6'))

    def parse_feed(self, url: str, source_name: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        try:
            response = requests.get(
                url,
                timeout=self.timeout_seconds,
                headers={'User-Agent': 'CEOBriefBot/0.2 (+rss-reader)'},
            )
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
        except Exception:
            return []

        items: list[dict[str, Any]] = []
        for entry in parsed.entries[: limit or self.max_items]:
            title = (entry.get('title') or '').strip()
            link = (entry.get('link') or '').strip()
            content = (entry.get('summary') or entry.get('description') or '').strip()
            if not title or not link:
                continue
            items.append({
                'source': source_name or parsed.feed.get('title') or url,
                'title': title,
                'url': link,
                'content': content[:1200],
                'publishedDate': entry.get('published') or entry.get('updated'),
            })
        return items

    def google_news_rss_url(self, query: str, lang: str = 'zh-CN', country: str = 'CN') -> str:
        encoded_query = urllib.parse.quote(query)
        return f'https://news.google.com/rss/search?q={encoded_query}&hl={lang}&gl={country}&ceid={country}:{lang}'

    def parse_google_news(self, query: str, limit: int | None = None, lang: str = 'zh-CN', country: str = 'CN') -> dict[str, Any]:
        url = self.google_news_rss_url(query, lang=lang, country=country)
        items = self.parse_feed(url, source_name=f'Google News RSS: {query}', limit=limit)
        return {'query': query, 'feedUrl': url, 'items': items}
