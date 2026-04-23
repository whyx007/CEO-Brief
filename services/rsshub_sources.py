from __future__ import annotations

import os
from typing import Any


def _base_url() -> str:
    return os.getenv('RSSHUB_BASE_URL', 'https://rss.whyx.site:8443').rstrip('/')


def build_rsshub_sources() -> list[dict[str, Any]]:
    base = _base_url()
    return [
        {'name': 'RSSHub 36Kr 快讯', 'url': f'{base}/36kr/newsflashes'},
        {'name': 'RSSHub 华尔街见闻', 'url': f'{base}/wallstreetcn/news'},
        {'name': 'RSSHub 虎嗅 24小时', 'url': f'{base}/huxiu/moment'},
        {'name': 'RSSHub 路透 World', 'url': f'{base}/reuters/world'},
        {'name': 'RSSHub 联合早报 即时', 'url': f'{base}/zaobao/realtime/china'},
    ]
