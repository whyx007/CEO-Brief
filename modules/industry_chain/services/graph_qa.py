from __future__ import annotations

import re
from typing import Any, Callable

from modules.industry_chain.services.neo4j_client import run_read_query
from modules.industry_chain.services import query_templates as qt

TermExtractor = Callable[[str], list[str]]

GRAPH_QA_EXPANSIONS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (('大模型', 'LLM', '生成式AI', 'AIGC', '智能体'), ('大模型', '人工智能', 'AI', '生成式AI', 'AIGC', '智能体', '机器学习', '深度学习')),
    (('人工智能', 'AI'), ('人工智能', 'AI', '大模型', '机器学习', '深度学习', '算法')),
    (('机器人', '具身智能'), ('机器人', '具身智能', '智能装备', '机器视觉', '运动控制', '导航')),
    (('光伏', '隆基'), ('光伏', '新能源', '组件', '硅片', '电池片', '储能', '能源管理')),
    (('储能',), ('储能', '电池', '能源管理', '新能源', 'BMS')),
    (('算力', '智算', '数据中心'), ('算力', '智算', '数据中心', '服务器', 'GPU', '液冷', '机房', 'PUE')),
    (('电力', '电网', '供电'), ('电力', '电网', '智能电网', '输电', '配网', '变电', '巡检')),
)

GRAPH_QA_STOP_FRAGMENTS = (
    '哪些', '什么', '是否', '有没有', '多少', '如何', '怎么', '为什么', '请问',
    '被投', '企业涉', '涉及', '相关', '方面', '合作的', '有哪些', '可以和',
    '哪些被', '些被投', '投企业', '可以', '合作', '公司有', '企业有',
    '服务过', '客户', '上下游',
)

GRAPH_QA_QUESTION_WORDS = (
    '哪些', '哪个', '哪家', '什么', '是否', '有没有', '多少', '如何', '怎么', '为什么', '请问',
    '被投企业', '被投', '企业', '公司', '相关', '涉及', '方面', '可以', '合作', '有哪些',
    '服务过', '客户', '上下游', '供应商', '供应链', '图谱', '知识',
)

GRAPH_QA_DOMAIN_TERMS = (
    '大模型', '人工智能', '生成式AI', 'AIGC', '智能体', '机器学习', '深度学习', '算法',
    '机器人', '具身智能', '智能装备', '机器视觉', '运动控制', '导航',
    '光伏', '新能源', '组件', '硅片', '电池片', '储能', '能源管理', '电池', 'BMS',
    '算力', '智算', '数据中心', '服务器', 'GPU', '液冷', '机房', 'PUE',
    '电力', '电网', '智能电网', '输电', '配网', '变电', '巡检', '无人机巡检',
    '半导体', '芯片', '集成电路', '封装', '测试', '传感器', '光通信',
    '医疗', '医院', '轨道交通', '铁路', '汽车', '新能源汽车',
)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value in (None, '') else [value])


def _unique_texts(values: list[Any], limit: int | None = None) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if len(text) < 2 or text in result:
            continue
        result.append(text)
        if limit and len(result) >= limit:
            break
    return result


def _clean_question_phrase(value: str) -> str:
    text = str(value or '').strip(' ?？。,.，、;；:：的与和及在跟同对')
    for word in sorted(GRAPH_QA_QUESTION_WORDS, key=len, reverse=True):
        text = text.replace(word, '')
    text = re.sub(r'(能够|能否|以及|还有|或者|还是|和|与|及|跟|同|对)', '', text)
    text = re.sub(r'有$', '', text)
    return text.strip(' ?？。,.，、;；:：的与和及在跟同对')


def _is_useful_graph_qa_term(value: str, question: str) -> bool:
    text = str(value or '').strip()
    if len(text) < 2 or text in GRAPH_QA_QUESTION_WORDS:
        return False
    if any(fragment in text for fragment in GRAPH_QA_STOP_FRAGMENTS):
        return False
    if text in GRAPH_QA_DOMAIN_TERMS:
        return True
    if any(char.isascii() for char in text):
        return True
    if re.search(r'(集团|股份|有限责任公司|有限公司|公司|大学|研究院|研究所|医院|中心|厂|院|所)$', text):
        return True
    if 2 <= len(text) <= 8 and text in question:
        return True
    return False


def _is_useful_extracted_term(value: str) -> bool:
    text = str(value or '').strip()
    if any(char.isascii() for char in text):
        return True
    return bool(re.search(r'(集团|股份|有限责任公司|有限公司|公司|大学|研究院|研究所|医院|中心|厂|院|所)$', text))


def _question_terms(text: str) -> list[str]:
    compact = re.sub(r'\s+', '', text)
    terms: list[str] = []
    for domain in GRAPH_QA_DOMAIN_TERMS:
        if domain in compact:
            terms.append(domain)
    for match in re.findall(r'[A-Za-z][A-Za-z0-9+.-]{1,}', text):
        if len(match) >= 2:
            terms.append(match)
    for phrase in re.split(r'[?？。,.，、;；:：\s]+', compact):
        cleaned = _clean_question_phrase(phrase)
        if 2 <= len(cleaned) <= 12:
            terms.append(cleaned)
    company_like = re.findall(
        r'[\u4e00-\u9fffA-Za-z0-9（）()]{2,24}(?:集团|股份|有限责任公司|有限公司|公司|大学|研究院|研究所|医院|中心|厂|院|所)',
        compact,
    )
    terms.extend(_clean_question_phrase(term) for term in company_like)
    return terms


def expand_graph_qa_terms(question: str, extract_terms: TermExtractor) -> list[str]:
    text = str(question or '').strip()
    terms: list[str] = _question_terms(text)
    for term in extract_terms(text):
        value = _clean_question_phrase(str(term or ''))
        if len(value) > 12 and not any(char.isascii() for char in value):
            continue
        if not _is_useful_graph_qa_term(value, text) or not _is_useful_extracted_term(value):
            continue
        terms.append(value)
    for markers, expansions in GRAPH_QA_EXPANSIONS:
        if any(marker in text for marker in markers):
            terms.extend(expansions)
    return _unique_texts([term for term in terms if _is_useful_graph_qa_term(term, text)], 48)


def graph_qa_intent(question: str) -> str:
    text = str(question or '')
    if any(word in text for word in ('合作', '协同', '对接', '撮合')):
        return 'cooperation'
    if any(word in text for word in ('客户', '服务过', '供应商', '供应链')):
        return 'customer_supply'
    return 'lookup'


def _field_text(row: dict[str, Any], fields: tuple[str, ...], limit: int = 4) -> str:
    values: list[Any] = []
    for field in fields:
        values.extend(_as_list(row.get(field)))
    return '、'.join(_unique_texts(values, limit))


def _evidence_text(row: dict[str, Any]) -> str:
    parts = []
    capability = _field_text(row, ('keyCapabilities', 'capabilities', 'products'), 5)
    scenario = _field_text(row, ('scenarios', 'demands', 'industries'), 4)
    customer = _field_text(row, ('customers', 'suppliers'), 4)
    stage = _field_text(row, ('subTracks', 'stages'), 3)
    if capability:
        parts.append(f"能力/产品：{capability}")
    if scenario:
        parts.append(f"场景/行业：{scenario}")
    if customer:
        parts.append(f"客户/供应链：{customer}")
    if stage:
        parts.append(f"链条位置：{stage}")
    return '；'.join(parts) or '图谱仅返回企业名称命中'


def _normalize_row(row: dict[str, Any], source: str) -> dict[str, Any]:
    matched_terms = _unique_texts(_as_list(row.get('matchedTerms')), 12)
    matched_fields = _unique_texts(_as_list(row.get('matchedFields')), 8)
    return {
        **row,
        'targetEnterprise': row.get('targetEnterprise') or row.get('enterprise') or '',
        'matchedTerms': matched_terms,
        'matchedFields': matched_fields,
        'sourceTemplate': source,
        'evidenceText': _evidence_text(row),
    }


def retrieve_graph_qa_evidence(question: str, extract_terms: TermExtractor, limit: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    terms = expand_graph_qa_terms(question, extract_terms)
    if not terms:
        return [], {'terms': [], 'templates': [], 'rowCount': 0}
    intent = graph_qa_intent(question)

    params = {
        'terms': terms,
        'candidateLimit': min(max(limit * 6, 80), 300),
        'limit': limit,
    }
    templates: list[str] = []
    rows: list[dict[str, Any]] = []

    profile_rows = run_read_query(qt.GRAPH_QA_ENTERPRISE_PROFILE, {'terms': terms[:16], 'limit': min(8, limit)})
    templates.append('graph_qa_enterprise_profile')
    rows.extend(_normalize_row(row, '企业画像') for row in profile_rows)

    if intent == 'cooperation':
        cooperation_rows = run_read_query(qt.GRAPH_QA_COOPERATION_CANDIDATES, params)
        templates.append('graph_qa_cooperation_candidates')
        rows.extend(_normalize_row(row, '合作候选') for row in cooperation_rows)
    elif intent == 'customer_supply':
        customer_rows = run_read_query(qt.GRAPH_QA_CUSTOMER_SUPPLY_EVIDENCE, params)
        templates.append('graph_qa_customer_supply_evidence')
        rows.extend(_normalize_row(row, '客户/供应链证据') for row in customer_rows)

    tag_rows = run_read_query(qt.GRAPH_QA_TAG_RELATED_ENTERPRISES, params)
    templates.append('graph_qa_tag_related_enterprises')
    rows.extend(_normalize_row(row, '标签关联企业') for row in tag_rows)

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in sorted(rows, key=lambda item: (int(item.get('matchScore') or 0), len(_as_list(item.get('matchedTerms')))), reverse=True):
        enterprise = str(row.get('targetEnterprise') or '').strip()
        if not enterprise or enterprise in seen:
            continue
        merged.append(row)
        seen.add(enterprise)
        if len(merged) >= limit:
            break

    return merged, {
        'terms': terms,
        'intent': intent,
        'templates': templates,
        'rowCount': len(merged),
    }


def graph_qa_table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        'title': '图谱问答证据',
        'columns': ['企业', '命中词', '图谱依据', '链条/环节', '分数'],
        'rows': [
            [
                row.get('targetEnterprise') or '',
                '、'.join(_as_list(row.get('matchedTerms'))[:6]),
                row.get('evidenceText') or '',
                _field_text(row, ('subTracks', 'stages'), 4),
                row.get('matchScore') or '',
            ]
            for row in rows
        ],
    }
