"""
竞情分析搜索工具（SearXNG 原生版）
优先级：SearXNG → 百度资讯 → 招投标站点 → DuckDuckGo
已屏蔽：Bocha / Serper / Bing / SerpAPI
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from typing import Optional, Type
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import JINA_API_KEY, REPORT_END, REPORT_START

logger = logging.getLogger(__name__)

TIMEOUT = 30
SEARCH_SOURCE_FAILURES: dict[str, int] = defaultdict(int)
SEARCH_SOURCE_DISABLED_UNTIL: dict[str, float] = {}
HEADERS_BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _source_enabled(name: str, default: bool = True) -> bool:
    return _env_flag(f'COMP_ANALYSIS_ENABLE_{name.upper()}', default)


def _source_available(name: str, default: bool = True) -> bool:
    if not _source_enabled(name, default):
        return False
    import time
    disabled_until = SEARCH_SOURCE_DISABLED_UNTIL.get(name, 0)
    return disabled_until <= time.time()


def _record_source_failure(name: str, *, threshold: int = 2, cooldown_seconds: int = 1800) -> None:
    import time
    failures = SEARCH_SOURCE_FAILURES[name] + 1
    SEARCH_SOURCE_FAILURES[name] = failures
    if failures >= threshold:
        SEARCH_SOURCE_DISABLED_UNTIL[name] = time.time() + cooldown_seconds
        logger.warning('[CircuitBreaker] disable source=%s failures=%d cooldown=%ss', name, failures, cooldown_seconds)


def _record_source_success(name: str) -> None:
    SEARCH_SOURCE_FAILURES[name] = 0
    SEARCH_SOURCE_DISABLED_UNTIL.pop(name, None)


def _searxng_config() -> dict:
    return {
        'base_url': os.getenv('SEARXNG_BASE_URL', '').strip().rstrip('/'),
        'verify_ssl': os.getenv('SEARXNG_VERIFY_SSL', 'false').strip().lower() in {'1', 'true', 'yes', 'on'},
        'language': os.getenv('SEARXNG_LANGUAGE', 'zh-CN').strip() or 'zh-CN',
        'news_categories': os.getenv('SEARXNG_CATEGORIES', 'news').strip() or 'news',
        'general_categories': 'general',
        'time_range': os.getenv('SEARXNG_TIME_RANGE', 'week').strip() or 'week',
        'timeout': int(os.getenv('SEARXNG_TIMEOUT_SECONDS', '12')),
    }


def _normalize_time_range(freshness: str = '') -> str:
    mapping = {
        '': 'month',
        'oneweek': 'week',
        'twoweeks': 'month',
        'oneday': 'day',
        'day': 'day',
        'week': 'week',
        'month': 'month',
        'year': 'year',
    }
    return mapping.get((freshness or '').strip().lower(), 'week')


def _searxng_search(query: str, num: int = 10, *, category_mode: str = 'general', freshness: str = 'oneweek') -> list[dict]:
    cfg = _searxng_config()
    if not cfg['base_url']:
        logger.warning('SearXNG not configured')
        return []
    if not _source_available('searxng'):
        logger.info('[Skip] source=searxng query=%s', query[:60])
        return []

    categories = cfg['news_categories'] if category_mode == 'news' else cfg['general_categories']
    time_range = _normalize_time_range(freshness)

    try:
        response = requests.get(
            f"{cfg['base_url']}/search",
            params={
                'q': query,
                'format': 'json',
                'language': cfg['language'],
                'categories': categories,
                'time_range': time_range,
                'pageno': 1,
            },
            timeout=cfg['timeout'],
            verify=cfg['verify_ssl'],
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning('SearXNG search failed: %s', exc)
        _record_source_failure('searxng')
        return []

    SPAM_DOMAINS = {
        'tea', 'massage', 'escort', 'vip', 'gg', 'seo', 'xing', 'adult',
        'dating', 'casino', 'betting', 'porn', 'xxx', 'lolita', 'tgp',
        'money', 'loan', 'cialis', 'viagra',
    }
    def _is_spam(url: str) -> bool:
        import re
        url_lower = url.lower()
        if re.search(r'喝茶|约炮|极品|网红|美女|外围|seo|留痕', url_lower):
            return True
        try:
            from urllib.parse import urlparse
            hostname = urlparse(url_lower).hostname or ''
            parts = set(hostname.split('.'))
            if parts & SPAM_DOMAINS:
                return True
        except Exception:
            pass
        return False

    results = []
    for item in (data.get('results') or [])[:num]:
        url = item.get('url', '')
        if _is_spam(url):
            continue
        results.append({
            'title': item.get('title', ''),
            'snippet': item.get('content', '') or item.get('snippet', ''),
            'link': url,
            'date': item.get('publishedDate', '') or item.get('published_date', ''),
            'source': item.get('engine', 'searxng'),
        })
    _record_source_success('searxng')
    return results


# 公共 SearXNG 备用实例
PUBLIC_SEARXNG_INSTANCES = [
    'https://searx.be',
    'https://search.sapti.me',
    'https://searx.work',
]


# 中文搜索备用：搜狗搜索 API（无墙，适合中文内容）
def _sogou_search(query: str, num: int = 8) -> list[dict]:
    if not _source_available('sogou', default=False):
        return []
    try:
        import requests as req_lib
        session = req_lib.Session()
        # Pre-fetch home page to get cookies
        session.get('https://www.sogou.com', headers=HEADERS_BROWSER, timeout=TIMEOUT)
        url = f"https://www.sogou.com/web?query={quote_plus(query)}"
        headers = {**HEADERS_BROWSER, 'Referer': 'https://www.sogou.com/'}
        r = session.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code == 403:
            logger.warning('Sogou 403, trying with different UA')
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36'
            r = session.get(url, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')
        results = []
        for item in soup.select('.vrwrap, .rb, .vr-title')[:num]:
            a_tag = item.select_one('a')
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = a_tag.get('href', '')
            snippet_tag = item.select_one('.str-text, .str_info, .star-wiki')
            snippet = snippet_tag.get_text(strip=True)[:200] if snippet_tag else ''
            if title and href:
                results.append({
                    'title': title,
                    'snippet': snippet,
                    'link': href,
                    'date': '',
                    'source': 'sogou',
                })
        return results
    except Exception as exc:
        logger.warning('Sogou search failed: %s', exc)
        _record_source_failure('sogou', threshold=1, cooldown_seconds=3600)
        return []


def _public_searxng_fallback(query: str, num: int = 8) -> list[dict]:
    """尝试公共 SearXNG 实例搜索"""
    for base_url in PUBLIC_SEARXNG_INSTANCES:
        try:
            response = requests.get(
                f"{base_url}/search",
                params={'q': query, 'format': 'json', 'language': 'zh-CN', 'time_range': 'month'},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            results = []
            for item in (data.get('results') or [])[:num]:
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('content', '') or item.get('snippet', ''),
                    'link': item.get('url', ''),
                    'date': item.get('publishedDate', '') or item.get('published_date', ''),
                    'source': 'public-searxng',
                })
            if results:
                return results
        except Exception as exc:
            logger.warning('Public SearXNG %s failed: %s', base_url, exc)
            continue
    return []


def _ddgs_search(query: str, num: int = 8) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for item in ddgs.text(keywords=query, region='cn-zh', max_results=num):
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('body', ''),
                    'link': item.get('href', ''),
                    'date': item.get('date'),
                    'source': 'duckduckgo',
                })
        return results
    except Exception as exc:
        logger.warning('DDG search failed: %s', exc)
        return []


def _ddgs_news(query: str, num: int = 8) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for item in ddgs.news(keywords=query, region='cn-zh', max_results=num):
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('body', ''),
                    'link': item.get('url', ''),
                    'date': item.get('date'),
                    'source': 'duckduckgo_news',
                })
        return results
    except Exception as exc:
        logger.warning('DDG news failed: %s', exc)
        return []


def _baidu_news_search(query: str, num: int = 8) -> list[dict]:
    try:
        url = f"https://www.baidu.com/s?tn=news&word={quote_plus(query)}&rn={num}"
        r = requests.get(url, headers=HEADERS_BROWSER, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for item in soup.select('.result')[:num]:
            title_tag = item.select_one('h3 a')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag.get('href', '')
            snippet_tag = item.select_one('.c-summary, .c-abstract')
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ''
            date_tag = item.select_one('.c-color-gray, .c-font-normal')
            date_str = date_tag.get_text(strip=True) if date_tag else ''
            results.append({
                'title': title,
                'snippet': snippet,
                'link': link,
                'date': date_str,
                'source': 'baidu_news',
            })
        return results
    except Exception as exc:
        logger.warning('Baidu news failed: %s', exc)
        return []


def _gov_bidding_search(query: str, num: int = 8) -> list[dict]:
    if not _source_available('ccgp'):
        return []
    try:
        url = 'http://search.ccgp.gov.cn/bxsearch'
        params = {
            'searchtype': 1,
            'page_index': 1,
            'bidSort': 0,
            'buyerName': '',
            'projectId': '',
            'pinMu': 0,
            'bidType': 0,
            'dbselect': 'bidx',
            'kw': query,
            'start_time': REPORT_START.strftime('%Y:%m:%d'),
            'end_time': REPORT_END.strftime('%Y:%m:%d'),
            'timeType': 6,
            'displayZone': '',
            'zoneId': '',
            'pppStatus': 0,
            'agentName': '',
        }
        r = requests.get(url, params=params, headers=HEADERS_BROWSER, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for item in soup.select('.vT-srch-result-list-bid li, .vT-srch-result-list li')[:num]:
            a_tag = item.select_one('a')
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            link = a_tag.get('href', '')
            span = item.select_one('span')
            date_str = span.get_text(strip=True) if span else ''
            snippet = item.get_text(strip=True)[:200]
            results.append({
                'title': title,
                'snippet': snippet,
                'link': link,
                'date': date_str,
                'source': 'ccgp_gov',
            })
        return results
    except Exception as exc:
        logger.warning('CCGP bidding search failed: %s', exc)
        _record_source_failure('ccgp')
        return []


def _chinabidding_search(query: str, num: int = 8) -> list[dict]:
    if not _source_available('chinabidding', default=False):
        return []
    try:
        url = f"https://www.chinabidding.cn/search?keywords={quote_plus(query)}"
        r = requests.get(url, headers=HEADERS_BROWSER, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')

        results = []
        for item in soup.select('.list-item, .search-item, .nui-result-item')[:num]:
            a_tag = item.select_one('a')
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            link = a_tag.get('href', '')
            if link and not link.startswith('http'):
                link = 'https://www.chinabidding.cn' + link
            snippet = item.get_text(strip=True)[:200]
            results.append({
                'title': title,
                'snippet': snippet,
                'link': link,
                'date': '',
                'source': 'chinabidding',
            })
        return results
    except Exception as exc:
        logger.warning('Chinabidding search failed: %s', exc)
        _record_source_failure('chinabidding', threshold=1, cooldown_seconds=3600)
        return []


def _jina_read(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        headers = {'Accept': 'application/json'}
        if JINA_API_KEY:
            headers['Authorization'] = f'Bearer {JINA_API_KEY}'
        r = requests.get(f'https://r.jina.ai/{url}', headers=headers, timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            return data.get('data', {}).get('content', '')[:5000]
    except Exception as exc:
        logger.debug('Jina read failed for %s: %s', url, exc)
    return None


def _sogou_news(query: str, num: int = 8) -> list[dict]:
    """搜狗新闻搜索（中文环境最佳搜索结果）"""
    if not _source_available('sogou_news', default=False):
        return []
    try:
        import requests as req_lib
        session = req_lib.Session()
        session.get('https://news.sogou.com', headers=HEADERS_BROWSER, timeout=TIMEOUT)
        url = f"https://news.sogou.com/news?query={quote_plus(query)}"
        headers = {**HEADERS_BROWSER, 'Referer': 'https://news.sogou.com/'}
        r = session.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code == 403:
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36'
            r = session.get(url, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')
        results = []
        for item in soup.select('.news-wrap, .vrwrap, .rb, .newslist')[:num]:
            a_tag = item.select_one('a')
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = a_tag.get('href', '')
            snippet_tag = item.select_one('.str-text, .str_info, p')
            snippet = snippet_tag.get_text(strip=True)[:200] if snippet_tag else ''
            date_tag = item.select_one('.news-time, .time, span')
            date_str = date_tag.get_text(strip=True) if date_tag else ''
            if title and href:
                results.append({
                    'title': title,
                    'snippet': snippet,
                    'link': href,
                    'date': date_str,
                    'source': 'sogou_news',
                })
        return results
    except Exception as exc:
        logger.warning('Sogou news failed: %s', exc)
        _record_source_failure('sogou_news', threshold=1, cooldown_seconds=3600)
        return []


def multi_search(
    query: str,
    num: int = 10,
    include_news: bool = True,
    include_bidding: bool = False,
    freshness: str = 'oneweek',
) -> list[dict]:
    """
    多源聚合搜索
    优先级：SearXNG → 百度资讯 → 招投标站点。
    搜狗默认关闭；若显式开启，也会在失败后自动熔断，避免拖死整轮任务。
    """
    all_results: list[dict] = []
    seen = set()

    def _dedup(new_items: list[dict]) -> list[dict]:
        result = []
        for item in new_items:
            link = item.get('link', '')
            if not link:
                continue
            clean_link = re.sub(r'[?#].*$', '', link)
            if clean_link in seen:
                continue
            seen.add(clean_link)
            result.append(item)
        return result

    logger.info('[Search] query=%s num=%d include_news=%s include_bidding=%s', query[:60], num, include_news, include_bidding)

    # 1) 自建 SearXNG（首选）
    searxng = _searxng_search(query, num=num, category_mode='general', freshness=freshness)
    if searxng:
        deduped = _dedup(searxng)
        all_results.extend(deduped)
        logger.info('[SearXNG] %d results', len(deduped))

    # 2) 搜狗（默认关闭；若开启则作为补充）
    if len(all_results) < num:
        try:
            sogou_text = _sogou_search(query, num=num)
            if sogou_text:
                deduped = _dedup(sogou_text)
                all_results.extend(deduped)
                logger.info('[Sogou web] %d results', len(deduped))
        except Exception as exc:
            logger.debug('Sogou web skipped: %s', exc)

    if include_news and len(all_results) < num * 2:
        try:
            sogou_n = _sogou_news(query, num=max(4, num))
            if sogou_n:
                deduped = _dedup(sogou_n)
                all_results.extend(deduped)
                logger.info('[Sogou news] %d results', len(deduped))
        except Exception as exc:
            logger.debug('Sogou news skipped: %s', exc)

    # 3) 百度搜索（主要备用）
    if len(all_results) < num:
        baidu = _baidu_news_search(query, num=max(4, num))
        if baidu:
            deduped = _dedup(baidu)
            all_results.extend(deduped)
            logger.info('[Baidu] %d results', len(deduped))

    # 4) 招投标站点（缩量）
    if include_bidding:
        gov = _gov_bidding_search(query, num=3)
        if gov:
            all_results.extend(_dedup(gov))
        cb = _chinabidding_search(query, num=3)
        if cb:
            all_results.extend(_dedup(cb))

    return all_results[: max(num, min(num * 2, 12))]


def deep_read(url: str) -> str:
    content = _jina_read(url)
    return content or '(无法读取该页面内容)'


class SearchInput(BaseModel):
    query: str = Field(description='搜索关键词')
    num_results: int = Field(default=5, description='结果数量')


class CompetitorSearchTool(BaseTool):
    name: str = 'competitor_search'
    description: str = (
        '搜索竞争对手公开信息。使用 SearXNG + 百度资讯 + DuckDuckGo + 招投标站点多源搜索。'
        '覆盖新闻、行业媒体、企业官网与公开采购公告。输入关键词，返回标题/摘要/链接/日期。'
    )
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str, num_results: int = 10) -> str:
        results = multi_search(query, num=num_results, include_news=True)
        if not results:
            return json.dumps({'status': 'no_results', 'query': query}, ensure_ascii=False)
        return json.dumps(results, ensure_ascii=False, indent=2)


class DeepReadInput(BaseModel):
    url: str = Field(description='要深度读取的网页URL')


class DeepReadTool(BaseTool):
    name: str = 'deep_read'
    description: str = (
        '深度读取网页完整内容（Jina Reader转Markdown）。'
        '适合对搜索到的关键证据进行详细信息提取。输入URL，返回结构化文本。'
    )
    args_schema: Type[BaseModel] = DeepReadInput

    def _run(self, url: str) -> str:
        return deep_read(url)
