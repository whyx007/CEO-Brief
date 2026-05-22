from __future__ import annotations

import re
from typing import Any


FIELD_WEIGHTS = {
    'products': 22,
    'capabilities': 20,
    'targetCapabilities': 20,
    'scenarios': 18,
    'demands': 14,
    'customers': 12,
    'industries': 10,
    'subTrack': 8,
    'targetStage': 8,
    'suppliers': 6,
}

GENERIC_TERMS = {
    '医疗', '医院', '医疗机构', '患者', '传感器', '检测', '诊断', '治疗', '设备', '系统', '平台',
    '应用', '服务', '客户', '科研机构', '医联体', '安全管理', '能耗管理', '设备维保',
}

MODE_WEIGHTS = {
    'supply_to_external': 14,
    'external_supply_to_portfolio': 10,
    'joint_r_and_d': 12,
    'shared_customer': 8,
    'scenario_landing': 12,
    'factory_or_operation_support': 8,
}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value in (None, '') else [value])


def _unique(values: list[Any], limit: int | None = None) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if text and text not in result:
            result.append(text)
            if limit and len(result) >= limit:
                break
    return result


def _term_hits(values: Any, terms: list[str]) -> list[str]:
    texts = [str(item or '').strip() for item in _as_list(values) if str(item or '').strip()]
    hits: list[str] = []
    for term in terms:
        if any(_contains_term(text, term) for text in texts):
            hits.append(term)
    return _unique(hits)


def _contains_term(text: str, term: str) -> bool:
    if not text or not term:
        return False
    if term.isascii() and term.isalpha() and len(term) <= 4:
        return bool(re.search(rf'(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])', text, flags=re.IGNORECASE))
    return term in text or (len(text) >= 4 and text in term)


def _is_generic_only(terms: list[str]) -> bool:
    return bool(terms) and all(term in GENERIC_TERMS or len(term) <= 2 for term in terms)


def _field_value(row: dict[str, Any], field: str) -> Any:
    if field == 'targetCapabilities':
        return _as_list(row.get('keyCapabilities')) + _as_list(row.get('capabilities')) + _as_list(row.get('products')) + _as_list(row.get('targetCapabilities'))
    return row.get(field)


def _matched_fields(row: dict[str, Any], terms: list[str]) -> list[str]:
    fields = []
    for field in FIELD_WEIGHTS:
        if _term_hits(_field_value(row, field), terms):
            fields.append(field)
    return fields


def _confidence(score: int, matched_fields: list[str], strong_hits: list[str], weak_hits: list[str]) -> str:
    strong_evidence_fields = {'products', 'capabilities', 'targetCapabilities', 'scenarios'}
    has_strong_evidence = bool(strong_evidence_fields.intersection(matched_fields))
    if score >= 52 and has_strong_evidence and strong_hits:
        return 'high'
    if score >= 26 and (strong_hits or len(matched_fields) >= 2):
        return 'medium'
    if weak_hits and not strong_hits:
        return 'low'
    return 'medium' if score >= 22 else 'low'


def rank_external_company_opportunities(rows: list[dict[str, Any]], profile: dict[str, Any], limit: int) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    dimensions = [
        item for item in _as_list(profile.get('cooperationDimensions'))
        if isinstance(item, dict) and item.get('mode')
    ]
    strong_terms = _unique(_as_list(profile.get('strongTerms')))
    weak_terms = _unique(_as_list(profile.get('weakTerms')))
    by_enterprise: dict[str, dict[str, Any]] = {}

    for row in rows:
        enterprise = str(row.get('targetEnterprise') or row.get('enterprise') or '').strip()
        if not enterprise:
            continue
        products = _unique(_as_list(row.get('products')))
        capabilities = _unique(_as_list(row.get('keyCapabilities')) + _as_list(row.get('capabilities')) + _as_list(row.get('targetCapabilities')))
        normalized = {
            **row,
            'targetEnterprise': enterprise,
            'products': products,
            'capabilities': capabilities,
            'targetCapabilities': _unique(capabilities + products, 12),
            'customers': _unique(_as_list(row.get('customers')), 8),
            'suppliers': _unique(_as_list(row.get('suppliers')), 8),
            'scenarios': _unique(_as_list(row.get('scenarios')), 8),
            'demands': _unique(_as_list(row.get('demands')), 8),
            'industries': _unique(_as_list(row.get('industries')), 8),
        }
        dimension_matches: list[dict[str, Any]] = []
        matched_terms_all: list[str] = []
        matched_fields_all: list[str] = []
        score = 0
        for dimension in dimensions:
            mode = str(dimension.get('mode') or '')
            terms = _unique(_as_list(dimension.get('queryTerms')))
            term_pool = terms
            matched_fields = _matched_fields(normalized, term_pool)
            matched_terms = []
            for field in matched_fields:
                matched_terms.extend(_term_hits(_field_value(normalized, field), term_pool))
            matched_terms = _unique(matched_terms)
            if not matched_fields or not matched_terms:
                continue
            field_score = sum(FIELD_WEIGHTS.get(field, 4) for field in matched_fields)
            strong_hits = [term for term in matched_terms if term in strong_terms]
            weak_hits = [term for term in matched_terms if term in weak_terms]
            dimension_score = MODE_WEIGHTS.get(mode, 6) + field_score + len(strong_hits) * 8 + len(weak_hits) * 2
            if _is_generic_only(matched_terms):
                dimension_score = max(4, dimension_score // 3)
            score += dimension_score
            matched_terms_all.extend(matched_terms)
            matched_fields_all.extend(matched_fields)
            dimension_matches.append({
                'mode': mode,
                'externalRole': dimension.get('externalRole') or '',
                'description': dimension.get('description') or '',
                'matchedTerms': matched_terms,
                'matchedFields': matched_fields,
                'score': dimension_score,
            })
        weak_only_hits = []
        for field in FIELD_WEIGHTS:
            weak_only_hits.extend(_term_hits(_field_value(normalized, field), weak_terms))
        weak_only_hits = _unique(weak_only_hits)
        if weak_only_hits and not dimension_matches:
            score += 6
            matched_terms_all.extend(weak_only_hits)
            matched_fields_all.extend(_matched_fields(normalized, weak_terms))
        if not score:
            continue
        matched_terms = _unique(matched_terms_all, 16)
        matched_fields = _unique(matched_fields_all, 12)
        strong_hits = [term for term in matched_terms if term in strong_terms]
        weak_hits = [term for term in matched_terms if term in weak_terms]
        if weak_hits and not strong_hits:
            score = min(score, 18)
        if _is_generic_only(matched_terms):
            score = min(score, 24)
        evidence = build_evidence(normalized, matched_fields, matched_terms)
        best_dimension = sorted(dimension_matches, key=lambda item: int(item.get('score') or 0), reverse=True)[0] if dimension_matches else {}
        ranked = {
            **normalized,
            'matchedDimension': best_dimension.get('description') or '',
            'cooperationMode': best_dimension.get('mode') or 'external_company',
            'externalRole': best_dimension.get('externalRole') or '',
            'dimensionMatches': sorted(dimension_matches, key=lambda item: int(item.get('score') or 0), reverse=True),
            'matchedTerms': matched_terms,
            'matchedFields': matched_fields,
            'strongTermHits': strong_hits,
            'weakTermHits': weak_hits,
            'score': score,
            'matchScore': score,
            'confidence': _confidence(score, matched_fields, strong_hits, weak_hits),
            'evidence': evidence,
            'opportunityType': 'external_company',
        }
        current = by_enterprise.get(enterprise)
        if not current or score > int(current.get('score') or 0):
            by_enterprise[enterprise] = ranked

    ranked_rows = sorted(by_enterprise.values(), key=lambda item: (int(item.get('score') or 0), len(_as_list(item.get('dimensionMatches')))), reverse=True)
    limited = ranked_rows[:limit]
    grouped: dict[str, list[dict[str, Any]]] = {str(item.get('mode')): [] for item in dimensions}
    for row in limited:
        for match in _as_list(row.get('dimensionMatches')):
            mode = str(match.get('mode') or '')
            if mode in grouped and len(grouped[mode]) < limit:
                grouped[mode].append(row)
    return limited, grouped


def build_evidence(row: dict[str, Any], matched_fields: list[str], matched_terms: list[str]) -> list[str]:
    evidence: list[str] = []
    if row.get('subTrack'):
        evidence.append(f"产业链/赛道：{row.get('subTrack')}")
    if row.get('targetStage'):
        evidence.append(f"环节：{row.get('targetStage')}")
    if matched_terms:
        evidence.append(f"匹配词：{'、'.join(matched_terms[:8])}")
    labels = {
        'products': '产品',
        'capabilities': '能力',
        'targetCapabilities': '能力/产品',
        'scenarios': '场景',
        'demands': '需求',
        'customers': '客户',
        'suppliers': '供应商',
        'industries': '行业',
    }
    for field in matched_fields:
        values = _unique(_as_list(_field_value(row, field)), 5)
        if values and field in labels:
            evidence.append(f"{labels[field]}：{'、'.join(values)}")
    return _unique(evidence, 8)
