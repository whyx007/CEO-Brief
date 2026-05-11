from __future__ import annotations

from typing import Any

DEFAULT_BUSINESS_HINTS = [
    '融资', '订单', '产线', '芯片', '半导体', '封装', '机器人', '新能源', '供应链', '工厂',
    '合作', '平台', '模型', '产业', '量产', '客户', '材料', 'AI', '智能', '制造'
]

DEFAULT_POLICY_HINTS = [
    '政策', '规划', '办法', '通知', '指导意见', '实施方案', '工信部', '发改委', '国务院',
    '新华社', '央视', '人民网', '外交', '国际', '峰会', '会谈', '谈判', '会见', '访问',
    '停火', '冲突', '战争', '局势', '伊朗', '俄乌', '乌克兰', '俄罗斯', '美国', '联合国',
    '制裁', '中东', '欧盟', '关税', '外交', '航班',
    '监管', '处罚', '罚单', '市场监管总局',
    '军事', '军', '战舰', '演习', '国防', '军队', '武器', '军备',
    '文化', '教育', '体育', '艺术', '社会', '民生', '司法', '法律', '立法',
    '医疗', '医改', '卫生', '养老', '社保', '就业服务', '社区', '基层治理',
    '三农', '乡村振兴', '乡村建设', '农村人居环境', '农业农村', '粮食安全', '高标准农田', '春耕', '秋收',
    '农业增产', '农业增效', '农民增收', '农村改革', '农业强国',
    '选举', '大选', '国会议', '参议院', '众议院', '议会',
    '声明', '谴责', '反对', '支持', '抗议',
]

EXCLUDE_POLICY_HINTS = [
    'a股', '港股', '美股', '恒生指数', '恒生科技指数', '创业板', '沪指', '深成指', '纳指', '标普', '道指',
    '涨停', '跌停', '涨超', '跌超', '收涨', '收跌', '盘中', '尾盘', '开盘', '低开', '高开', '现货白银', '黄金', '期货',
    '融资', '并购', 'IPO', 'ipo', '股价', '市值', '营收', '利润', '财报', '业绩', '上市', '招标', '扩产', '订单',
    '股票', '基金', 'ETF', 'etf', '资管', '私募', '公募',
    '商业航天', '卫星', '卫星互联网', '星载', '激光通信', '测控', '遥感', '火箭', '航天器', '中科天塔',
]


DEFAULT_MACRO_HINTS = [
    '利率', '降息', '加息', '汇率', '人民币', '美元', '出口', '进口', '贸易', '通胀', 'cpi', 'ppi',
    '制造业', 'pmi', '期货', '证券', '股市', '债券', '大宗商品', '原油', '黄金', '铜', '美股', 'a股',
    '港股', '纳指', '标普', '道指', '国债', '央行', '财政', '经济',
    '收购', '融资', '并购', '财报', '订单', '扩产', '招标', '上市', 'ipo', '出海', '业绩', '利润', '营收',
    '股票', '基金', 'ETF', 'etf', '资管', '私募', '公募', '估值', '市值', '股价', '板块',
    '逆势', '拉升', '普涨', '普跌', '走强', '走弱', '反弹', '回调',
    '企业', '公司', '产业', '产经', '工业', '商业',
    '供应链', 'AI', '智能', '制造', '芯片', '半导体', '机器人', '新能源', '汽车',
]

EXCLUDE_MACRO_HINTS = [
    '民生', '教育', '医疗', '医改', '卫生', '养老', '社保', '就业服务', '社区', '基层治理',
    '三农', '乡村振兴', '乡村建设', '农村人居环境', '农业农村', '粮食安全', '高标准农田', '春耕', '秋收',
    '农业增产', '农业增效', '农民增收', '农村改革', '农业强国',
    '文化', '文旅', '旅游', '体育', '艺术', '生态环境', '环保',
    '学习进行时', '人民网时政', '新华网时政'
]

DEFAULT_SPACE_INDUSTRY_HINTS = [
    '商业航天', '卫星', '卫星互联网', '火箭', '发射', '遥感', '测运控', '星座', '地面站', '测控',
    '航天器', '载荷', '卫星制造', '轨道', '低轨', '空间基础设施',
    '中科天塔', '星载', '激光通信', '通信终端', '天地一体'
]

SPACE_SOURCE_ALLOWLIST = {
    'SpaceNews',
    'NASA Breaking News',
    'ESA Top News',
    'Space.com',
}


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
    matched = _filter_items(items, active_hints)
    result: list[dict[str, Any]] = []
    for item in matched:
        text = ' '.join([
            str(item.get('title') or ''),
            str(item.get('content') or ''),
            str(item.get('articleText') or ''),
            str(item.get('source') or ''),
        ]).lower()
        if any(h.lower() in text for h in EXCLUDE_POLICY_HINTS):
            continue
        result.append(item)
    return result


def filter_macro_items(items: list[dict[str, Any]], hints: list[str] | None = None) -> list[dict[str, Any]]:
    active_hints = hints or DEFAULT_MACRO_HINTS
    matched = _filter_items(items, active_hints)
    result: list[dict[str, Any]] = []
    for item in matched:
        text = ' '.join([
            str(item.get('title') or ''),
            str(item.get('content') or ''),
            str(item.get('articleText') or ''),
            str(item.get('source') or ''),
        ]).lower()
        if any(h.lower() in text for h in EXCLUDE_MACRO_HINTS):
            continue
        result.append(item)
    return result


def filter_space_industry_items(items: list[dict[str, Any]], hints: list[str] | None = None) -> list[dict[str, Any]]:
    active_hints = hints or DEFAULT_SPACE_INDUSTRY_HINTS
    keyword_matched = _filter_items(items, active_hints)
    allowlisted = [
        item for item in items
        if str(item.get('source') or '').strip() in SPACE_SOURCE_ALLOWLIST
    ]
    seen_urls: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in [*keyword_matched, *allowlisted]:
        url = str(item.get('url') or '').strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        result.append(item)
    return result


def exclude_items(items: list[dict[str, Any]], excluded: list[dict[str, Any]]) -> list[dict[str, Any]]:
    excluded_urls = {str(item.get('url') or '').strip() for item in (excluded or []) if item.get('url')}
    if not excluded_urls:
        return items
    return [item for item in items if str(item.get('url') or '').strip() not in excluded_urls]
