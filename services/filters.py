from __future__ import annotations

from typing import Any

DEFAULT_BUSINESS_HINTS = [
    '融资', '订单', '产线', '芯片', '半导体', '封装', '机器人', '新能源', '供应链', '工厂',
    '合作', '平台', '模型', '产业', '量产', '客户', '材料', 'AI', '智能', '制造'
]

DEFAULT_POLICY_HINTS = [
    '政策', '规划', '办法', '通知', '指导意见', '实施方案', '工信部', '发改委', '国务院',
    '新华社', '央视', '人民网', '外交', '国际', '峰会', '会谈', '停火', '冲突', '战争', '局势',
    '伊朗', '俄乌', '乌克兰', '俄罗斯', '美国', '联合国', '制裁', '中东'
]

DEFAULT_MACRO_HINTS = [
    '利率', '降息', '加息', '汇率', '人民币', '美元', '出口', '进口', '贸易', '通胀', 'cpi', 'ppi',
    '制造业', 'pmi', '期货', '证券', '股市', '债券', '大宗商品', '原油', '黄金', '铜', '美股', 'a股',
    '港股', '纳指', '标普', '道指', '国债', '央行', '财政', '经济'
]

DEFAULT_SPACE_INDUSTRY_HINTS = [
    '商业航天', '卫星', '卫星互联网', '火箭', '发射', '遥感', '测运控', '星座', '地面站', '测控',
    '航天器', '载荷', '卫星制造', '轨道', '低轨', '空间基础设施'
]


def _filter_items(items: list[dict[str, Any]], hints: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        text = ' '.join([
            str(item.get('title') or ''),
            str(item.get('content') or ''),
            str(item.get('articleText') or ''),
            str(item.get('source') or ''),
        ]).lower()
        if any(h.lower() in text for h in hints):
            result.append(item)
    return result


def filter_business_items(items: list[dict[str, Any]], hints: list[str] | None = None) -> list[dict[str, Any]]:
    active_hints = hints or DEFAULT_BUSINESS_HINTS
    return _filter_items(items, active_hints)


def filter_policy_items(items: list[dict[str, Any]], hints: list[str] | None = None) -> list[dict[str, Any]]:
    active_hints = hints or DEFAULT_POLICY_HINTS
    return _filter_items(items, active_hints)


def filter_macro_items(items: list[dict[str, Any]], hints: list[str] | None = None) -> list[dict[str, Any]]:
    active_hints = hints or DEFAULT_MACRO_HINTS
    return _filter_items(items, active_hints)


def filter_space_industry_items(items: list[dict[str, Any]], hints: list[str] | None = None) -> list[dict[str, Any]]:
    active_hints = hints or DEFAULT_SPACE_INDUSTRY_HINTS
    return _filter_items(items, active_hints)
