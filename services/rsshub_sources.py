from __future__ import annotations

import os
from typing import Any


def _base_url() -> str:
    return os.getenv('RSSHUB_BASE_URL', 'https://rss.whyx.site:8443').rstrip('/')


def build_rsshub_sources() -> list[dict[str, Any]]:
    base = _base_url()
    return [
        # 科技 / 创投
        {'name': 'RSSHub 36Kr 快讯', 'url': f'{base}/36kr/newsflashes'},
        {'name': 'RSSHub 36Kr 主题', 'url': f'{base}/36kr/motif/1'},
        {'name': 'RSSHub 虎嗅 24小时', 'url': f'{base}/huxiu/moment'},
        {'name': 'RSSHub 虎嗅文章', 'url': f'{base}/huxiu/article'},
        {'name': 'RSSHub 极客公园快讯', 'url': f'{base}/geekpark/breakingnews'},
        {'name': 'RSSHub 少数派', 'url': f'{base}/sspai/index'},
        {'name': 'RSSHub V2EX', 'url': f'{base}/v2ex/topics'},
        {'name': 'RSSHub 知乎热榜', 'url': f'{base}/zhihu/hotlist'},
        # 财经
        {'name': 'RSSHub 华尔街见闻', 'url': f'{base}/wallstreetcn/news'},
        {'name': 'RSSHub 华尔街见闻热门', 'url': f'{base}/wallstreetcn/hot'},
        {'name': 'RSSHub 财联社电报', 'url': f'{base}/cls/telegraph'},
        # 国际
        {'name': 'RSSHub 路透 World', 'url': f'{base}/reuters/world'},
        {'name': 'RSSHub 联合早报 即时', 'url': f'{base}/zaobao/realtime/china'},
        {'name': 'RSSHub 联合早报 国际', 'url': f'{base}/zaobao/realtime/world'},
        {'name': 'RSSHub BBC中文', 'url': f'{base}/bbci/zhongwen'},
        {'name': 'RSSHub BBC World', 'url': f'{base}/bbc/world'},
        {'name': 'RSSHub 纽约时报', 'url': f'{base}/nytimes'},
        {'name': 'RSSHub 观察者网', 'url': f'{base}/guancha/index'},
    ]
