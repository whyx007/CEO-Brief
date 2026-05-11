from __future__ import annotations

import os
import re
import urllib.parse
from html import unescape
from pathlib import Path
from typing import Any

import feedparser
import requests
from dotenv import load_dotenv

_IMAGE_CACHE: dict[str, str | None] = {}

load_dotenv(Path(__file__).resolve().parent.parent / '.env')


DEFAULT_RSS_SOURCES = [
    {'name': '36Kr', 'url': 'https://36kr.com/feed'},
    {'name': 'Reuters Business', 'url': 'https://feeds.reuters.com/reuters/businessNews'},
    {'name': 'Reuters World', 'url': 'https://feeds.reuters.com/Reuters/worldNews'},
    {'name': 'TechCrunch', 'url': 'https://techcrunch.com/feed/'},
    {'name': 'VentureBeat AI', 'url': 'https://venturebeat.com/category/ai/feed/'},
    {'name': '新华网时政', 'url': 'http://www.xinhuanet.com/politics/news_politics.xml'},
    {'name': '人民网时政', 'url': 'http://www.people.com.cn/rss/politics.xml'},
    {'name': '财新网', 'url': 'https://www.caixin.com/rss/rss.xml'},
    {'name': '界面新闻', 'url': 'https://a.jiemian.com/index.php?m=article&a=rss'},
    {'name': '虎嗅网', 'url': 'https://www.huxiu.com/rss/0.xml'},
    {'name': '证券时报', 'url': 'https://www.stcn.com/article/rss.html'},
    {'name': '第一财经', 'url': 'https://www.yicai.com/feed/32.html'},
    {'name': '每日经济新闻', 'url': 'https://www.nbd.com.cn/rss/rss.html'},
    {'name': '创业邦', 'url': 'https://www.cyzone.cn/feed/'},
    {'name': '投资界', 'url': 'https://www.pedaily.cn/rss/rss.xml'},
    {'name': '东方财富', 'url': 'https://np-c001-webp.np-d.com/rss?np_did=100005&np_userId=0&area_id=100002&type_id=100002&mode_id=2'},
    {'name': '新华社财经', 'url': 'http://www.news.cn/fortune/index.xml'},
    {'name': '人民日报财经', 'url': 'http://finance.people.com.cn/rss/finance.xml'},
    {'name': '新浪财经', 'url': 'http://finance.sina.com.cn/rss/rss.xml'},
    {'name': '凤凰网财经', 'url': 'https://finance.ifeng.com/rss/news.xml'},
]

BAD_IMAGE_PATTERNS = [
    'logo', 'icon', 'avatar', 'favicon', 'share.', 'share/', 'default', 'placeholder', 'sprite',
    '/_static/', '/static/share', 'app-icon', 'site-icon', 'apple-touch-icon',
    'img.36krcdn.com/20191024/v2_1571894049839_img_jpg'
]


def _is_probably_content_image(url: str | None) -> bool:
    link = str(url or '').strip().lower()
    if not link:
        return False
    if any(token in link for token in BAD_IMAGE_PATTERNS):
        return False

    size_patterns = [
        r'([?&](?:w|width|h|height)=)(\d+)',
        r'/(\d{1,4})x(\d{1,4})(?:[/?._-]|$)',
    ]
    dimensions: list[int] = []
    for pattern in size_patterns:
        for match in re.finditer(pattern, link, flags=re.IGNORECASE):
            nums = [int(x) for x in match.groups() if str(x).isdigit()]
            dimensions.extend(nums)
    if dimensions and max(dimensions) < 180:
        return False
    return True



def _normalize_image_candidate(url: str | None) -> str | None:
    link = str(url or '').strip()
    if not _is_probably_content_image(link):
        return None
    return link



def _extract_first_image_url(entry: Any, content: str) -> str | None:
    media_content = entry.get('media_content') or []
    for media in media_content:
        url = _normalize_image_candidate(media.get('url'))
        if url:
            return url

    media_thumbnail = entry.get('media_thumbnail') or []
    for media in media_thumbnail:
        url = _normalize_image_candidate(media.get('url'))
        if url:
            return url

    enclosures = entry.get('enclosures') or []
    for enclosure in enclosures:
        href = _normalize_image_candidate(enclosure.get('href') or enclosure.get('url'))
        content_type = (enclosure.get('type') or '').lower()
        if href and content_type.startswith('image/'):
            return href

    image_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', unescape(content or ''), flags=re.IGNORECASE)
    if image_match:
        return _normalize_image_candidate(image_match.group(1).strip())
    return None



def _extract_meta_image_from_url(url: str, timeout_seconds: float) -> str | None:
    link = (url or '').strip()
    if not link:
        return None
    if link in _IMAGE_CACHE:
        return _IMAGE_CACHE[link]
    try:
        response = requests.get(
            link,
            timeout=min(timeout_seconds, 4.0),
            headers={'User-Agent': 'CEOBriefBot/0.2 (+rss-reader meta-image)'},
        )
        response.raise_for_status()
        html = response.text or ''
        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                image = match.group(1).strip()
                if image:
                    image = _normalize_image_candidate(urllib.parse.urljoin(link, image))
                    _IMAGE_CACHE[link] = image
                    return image
    except Exception:
        pass
    _IMAGE_CACHE[link] = None
    return None


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
            image_url = _extract_first_image_url(entry, content)
            if not image_url:
                image_url = _extract_meta_image_from_url(link, self.timeout_seconds)
            items.append({
                'source': source_name or parsed.feed.get('title') or url,
                'title': title,
                'url': link,
                'content': content[:1200],
                'publishedDate': entry.get('published') or entry.get('updated'),
                'imageUrl': image_url,
            })
        return items

    def google_news_rss_url(self, query: str, lang: str = 'zh-CN', country: str = 'CN') -> str:
        encoded_query = urllib.parse.quote(query)
        return f'https://news.google.com/rss/search?q={encoded_query}&hl={lang}&gl={country}&ceid={country}:{lang}'

    def parse_google_news(self, query: str, limit: int | None = None, lang: str = 'zh-CN', country: str = 'CN') -> dict[str, Any]:
        url = self.google_news_rss_url(query, lang=lang, country=country)
        items = self.parse_feed(url, source_name=f'Google News RSS: {query}', limit=limit)
        return {'query': query, 'feedUrl': url, 'items': items}
