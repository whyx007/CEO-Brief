"""时间窗口过滤工具：从新闻列表中移除超过指定天数的旧闻。"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any


def filter_by_date(
    items: list[dict[str, Any]],
    max_days: int = 2,
    date_keys: tuple[str, ...] | None = None,
    timezone_hours: int = 8,
) -> list[dict[str, Any]]:
    """
    过滤新闻列表，只保留 max_days 天内的条目。

    各字段按 date_keys 顺序尝试解析；均无法解析或为空时默认保留（容错）。

    Args:
        items: 新闻条目列表
        max_days: 允许的最大天数（默认 2 天）
        date_keys: 候选日期字段名，按优先级依次尝试（默认 publishedDate, date, updatedAt）
        timezone_hours: 时区偏移小时数（默认 +8 东八区）

    Returns:
        过滤后的条目列表
    """
    if date_keys is None:
        date_keys = ('publishedDate', 'published_date', 'date', 'updatedAt', 'pubDate', 'timestamp')

    tz = timezone(timedelta(hours=timezone_hours))
    now = datetime.now(tz=tz)
    cutoff = now - timedelta(days=max_days)

    kept: list[dict[str, Any]] = []
    dropped = 0
    for item in items:
        dt = _parse_date(item, date_keys, tz)
        if dt is None:
            # 无法解析日期时保留（容错）
            kept.append(item)
            continue
        if dt >= cutoff:
            kept.append(item)
        else:
            dropped += 1

    return kept


def filter_by_date_strict(
    items: list[dict[str, Any]],
    max_days: int = 2,
    date_keys: tuple[str, ...] | None = None,
    timezone_hours: int = 8,
) -> list[dict[str, Any]]:
    """
    严格模式：无法解析日期的条目也会被丢弃。
    """
    if date_keys is None:
        date_keys = ('publishedDate', 'published_date', 'date', 'updatedAt', 'pubDate', 'timestamp')

    tz = timezone(timedelta(hours=timezone_hours))
    now = datetime.now(tz=tz)
    cutoff = now - timedelta(days=max_days)

    kept: list[dict[str, Any]] = []
    for item in items:
        dt = _parse_date(item, date_keys, tz)
        if dt is not None and dt >= cutoff:
            kept.append(item)
    return kept


def _parse_date(
    item: dict[str, Any],
    date_keys: tuple[str, ...],
    tz: timezone,
) -> datetime | None:
    """从 item 中按顺序尝试解析日期字段。"""
    for key in date_keys:
        raw = item.get(key)
        if raw is None:
            continue
        dt = _try_parse(raw, tz)
        if dt is not None:
            return dt
    return None


def _try_parse(value: Any, tz: timezone) -> datetime | None:
    """尝试多种常见日期格式解析。"""
    if not value or not isinstance(value, (str, int, float)):
        return None

    if isinstance(value, (int, float)):
        # 可能是 Unix 时间戳（秒或毫秒）
        try:
            if value > 1e12:  # 毫秒
                value = value / 1000
            return datetime.fromtimestamp(value, tz=tz)
        except (OSError, ValueError, OverflowError):
            return None

    s = str(value).strip()
    if not s:
        return None

    # ISO 8601 格式（带时区或 Z 结尾）
    if s.endswith('Z'):
        s_iso = s[:-1] + '+00:00'
    else:
        s_iso = s

    # 尝试常见 ISO 格式
    for fmt in (
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
    ):
        try:
            dt = datetime.strptime(s_iso, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return dt
        except ValueError:
            continue

    # RFC 2822 / RSS 日期格式
    for fmt in (
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y',
    ):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return dt
        except ValueError:
            continue

    return None
