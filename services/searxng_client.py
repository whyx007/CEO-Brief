from __future__ import annotations

import os
from typing import Any

import requests


class SearXNGClient:
    def __init__(self) -> None:
        self.base_url = os.getenv('SEARXNG_BASE_URL', '').strip().rstrip('/')
        self.timeout_seconds = int(os.getenv('SEARXNG_TIMEOUT_SECONDS', '20'))
        self.default_language = os.getenv('SEARXNG_LANGUAGE', 'zh-CN').strip()
        self.default_time_range = os.getenv('SEARXNG_TIME_RANGE', 'day').strip()
        self.default_categories = os.getenv('SEARXNG_CATEGORIES', 'news').strip()

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def search(self, query: str, *, page: int = 1, categories: str | None = None, time_range: str | None = None, language: str | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError('searxng_not_configured')

        response = requests.get(
            f'{self.base_url}/search',
            params={
                'q': query,
                'format': 'json',
                'pageno': page,
                'language': language or self.default_language,
                'time_range': time_range or self.default_time_range,
                'categories': categories or self.default_categories,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()
