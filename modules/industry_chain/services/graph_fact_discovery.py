from __future__ import annotations

import re
from typing import Any


DIRECT_FACT_MARKERS = (
    '哪些被投企业', '被投企业', '已经', '已', '直接应用', '应用在', '落地', '进入', '服务', '供货', '客户',
    '中标', '部署', '临床应用',
)

SCENE_EXPANSIONS: list[tuple[tuple[str, ...], list[str]]] = [
    (('医院', '医疗', '临床', '科室', '医药', '患者'), [
        '医院', '医疗', '临床', '科室', '三甲医院', '附属医院', '医学', '医疗器械', '医药', '诊断',
        '治疗', '监护', '手术', '影像', '心血管', '肿瘤', '核医学', '口腔', '皮肤病', '神经',
        '精神疾病', '康复', '检验', '体检中心', '基层医疗', '基层医疗服务中心', '患者', '心电',
        '体温', '生命体征', '血氧', '脑功能', '睡眠', '神经刺激', '微针', '透皮给药', '术中',
        '放疗', '放射', '放射卫生', '医疗卫生', '消毒器械', '核辐射', 'PET-CT', 'OCT', 'BNCT',
        'RLT', 'IVD',
    ]),
    (('电网', '电力', '供电', '输电', '配电'), [
        '电网', '电力', '供电', '输电', '配电', '变电', '国家电网', '国网', '南方电网', '电站',
        '电力设备', '巡检', '储能', '新能源消纳',
    ]),
    (('汽车', '车企', '主机厂', '整车', '车载'), [
        '汽车', '车企', '主机厂', '整车', '车载', '新能源汽车', '动力电池', '智能驾驶', '充电',
        '换电', '座舱',
    ]),
    (('半导体', '芯片', '集成电路', '晶圆'), [
        '半导体', '芯片', '集成电路', '晶圆', '封装', '测试', '光电芯片', '功率器件', '晶圆厂',
    ]),
    (('数据中心', '算力', '智算', '云计算'), [
        '数据中心', '算力', '智算', '云计算', 'AI', '服务器', '液冷', 'UPS', '光通信', '机房',
    ]),
]

GENERIC_EVIDENCE_TERMS = [
    '客户', '供货', '中标', '部署', '合作', '应用', '批量', '量产', '上市', '商业化', '已获',
    '认证', '注册', '交付', '销售', '出口', '收费', '试点', '示范',
]

MEDICAL_EVIDENCE_TERMS = [
    'NMPA', 'FDA', '医疗器械', '二类', 'II类', '三类', 'III类', '临床', '三甲医院', '附属医院',
    '科室', '手术', '监护', '诊断', '治疗', '医院客户', '医学转化', 'PET-CT', 'OCT', 'BNCT',
    'RLT', '体外诊断', 'IVD', '体检中心', '基层医疗服务中心', '医疗卫生', '放射卫生', '消毒器械',
    '心电', '生命体征', '体温', '脑功能', '睡眠监测', '神经刺激', '术中影像', '口腔医疗',
]

EXCLUDE_TERMS = [
    '暂无公开', '暂无明确', '可能应用', '原理样机', '临床前', '待验证', '未查到', '推测',
]

FIELD_WEIGHTS = {
    'customers': 30,
    'products': 24,
    'scenarios': 22,
    'industries': 18,
    'capabilities': 16,
    'keyCapabilities': 16,
    'stages': 8,
    'subTracks': 8,
    'demands': 4,
    'suppliers': 2,
}

DIRECT_APPLICATION_TERMS = [
    '医院', '三甲医院', '附属医院', '体检中心', '基层医疗服务中心', '医疗卫生', '放射卫生',
    '医学转化', '供货', '中标', '部署', '批量', '量产', '上市', '商业化', '已获', '认证',
    'NMPA', 'FDA', '二类', 'II类', '三类', 'III类', '销售', '出口',
]

MEDICAL_PRODUCT_TERMS = [
    '医疗器械', '诊断', '治疗', '监护', '手术', '影像', '心电', '体温', '生命体征', '血氧',
    '脑功能', '睡眠', '神经刺激', '微针', '透皮给药', '口腔', '术中', 'BNCT', 'OCT',
    'PET-CT', 'RLT', 'IVD', '消毒器械', '核辐射', '放射',
]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value in (None, '') else [value])


def _unique(values: list[Any] | tuple[Any, ...], limit: int | None = None) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if len(text) < 2 or text in result:
            continue
        result.append(text)
        if limit and len(result) >= limit:
            break
    return result


def should_use_graph_fact_discovery(question: str, keyword: str = '', opportunity_mode: str = '') -> bool:
    text = f'{question} {keyword} {opportunity_mode}'
    if opportunity_mode == 'graph_fact_discovery':
        return True
    has_subject = '被投企业' in text or '图谱' in text or 'Neo4j' in text or 'neo4j' in text
    has_fact = any(marker in text for marker in ('已经', '已', '直接应用', '应用在', '落地', '进入', '服务', '供货', '中标', '部署'))
    return has_subject and has_fact


def build_fact_discovery_plan(question: str, keyword: str = '') -> dict[str, Any]:
    text = f'{question} {keyword}'
    target_terms: list[str] = []
    for markers, expansions in SCENE_EXPANSIONS:
        if any(marker in text for marker in markers):
            target_terms.extend(expansions)
    target_terms.extend(term for term in re.split(r'[\s,，、/；;:：()（）？?]+', text) if len(term) >= 2)
    evidence_terms = list(GENERIC_EVIDENCE_TERMS)
    if any(marker in text for marker in ('医院', '医疗', '临床', '科室', '医药')):
        evidence_terms.extend(MEDICAL_EVIDENCE_TERMS)
    return {
        'task': 'portfolio_fact_discovery',
        'question': question,
        'keyword': keyword,
        'targetTerms': _unique(target_terms, 80),
        'evidenceTerms': _unique(evidence_terms, 80),
        'excludeTerms': EXCLUDE_TERMS,
        'outputIntent': '找出被投企业中已经在目标行业/场景落地的产品技术，并按证据强弱排序',
    }


def _field_hits(row: dict[str, Any], field: str, terms: list[str]) -> list[str]:
    values = [str(item or '').strip() for item in _as_list(row.get(field)) if str(item or '').strip()]
    hits = []
    for term in terms:
        if any(term in value or (len(value) >= 4 and value in term) for value in values):
            hits.append(term)
    return _unique(hits)


def _best_values(row: dict[str, Any], fields: list[str], terms: list[str], limit: int = 5) -> list[str]:
    result: list[str] = []
    for field in fields:
        for value in _as_list(row.get(field)):
            text = str(value or '').strip()
            if not text:
                continue
            if any(term in text or (len(text) >= 4 and text in term) for term in terms) or not result:
                result.append(text)
            if len(_unique(result)) >= limit:
                return _unique(result, limit)
    return _unique(result, limit)


def _confidence(score: int, direct_fields: list[str], evidence_hits: list[str], exclude_hits: list[str]) -> str:
    if score >= 88 and {'customers', 'products'}.issubset(set(direct_fields)) and evidence_hits:
        return 'high'
    if score >= 62 and evidence_hits and direct_fields:
        return 'medium'
    if exclude_hits and score < 70:
        return 'low'
    return 'medium' if score >= 48 else 'low'


def rank_fact_discovery_rows(rows: list[dict[str, Any]], plan: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    target_terms = _unique(_as_list(plan.get('targetTerms')), 100)
    evidence_terms = _unique(_as_list(plan.get('evidenceTerms')), 100)
    exclude_terms = _unique(_as_list(plan.get('excludeTerms')), 40)
    ranked: list[dict[str, Any]] = []
    for row in rows:
        direct_fields: list[str] = []
        target_hits_all: list[str] = []
        evidence_hits_all: list[str] = []
        score = 0
        for field, weight in FIELD_WEIGHTS.items():
            target_hits = _field_hits(row, field, target_terms)
            evidence_hits = _field_hits(row, field, evidence_terms)
            if target_hits:
                score += weight + min(len(target_hits), 4) * 4
                target_hits_all.extend(target_hits)
                direct_fields.append(field)
            if evidence_hits:
                score += max(8, weight // 2) + min(len(evidence_hits), 4) * 3
                evidence_hits_all.extend(evidence_hits)
                if field not in direct_fields:
                    direct_fields.append(field)
        exclude_hits = []
        for field in FIELD_WEIGHTS:
            exclude_hits.extend(_field_hits(row, field, exclude_terms))
        exclude_hits = _unique(exclude_hits)
        direct_application_hits: list[str] = []
        medical_product_hits: list[str] = []
        for field in FIELD_WEIGHTS:
            direct_application_hits.extend(_field_hits(row, field, DIRECT_APPLICATION_TERMS))
            medical_product_hits.extend(_field_hits(row, field, MEDICAL_PRODUCT_TERMS))
        direct_application_hits = _unique(direct_application_hits, 12)
        medical_product_hits = _unique(medical_product_hits, 12)
        if direct_application_hits:
            score += 24 + min(len(direct_application_hits), 5) * 5
        if medical_product_hits:
            score += 18 + min(len(medical_product_hits), 5) * 4
        if exclude_hits:
            score -= 12 + len(exclude_hits) * 4

        target_hits_all = _unique(target_hits_all or _as_list(row.get('targetHits')), 16)
        evidence_hits_all = _unique(evidence_hits_all + direct_application_hits + _as_list(row.get('evidenceHits')), 16)
        if not target_hits_all and not evidence_hits_all:
            continue
        if 'customers' not in direct_fields and not direct_application_hits and not evidence_hits_all and score < 58:
            continue

        products = _unique(_as_list(row.get('products')), 8)
        capabilities = _unique(_as_list(row.get('keyCapabilities')) + _as_list(row.get('capabilities')), 8)
        scenario_evidence = _best_values(row, ['customers', 'scenarios', 'industries'], target_terms + evidence_terms, 6)
        product_evidence = _best_values(row, ['products', 'capabilities', 'keyCapabilities'], target_terms + evidence_terms, 6)
        evidence = []
        if target_hits_all:
            evidence.append(f"目标场景命中：{'、'.join(target_hits_all[:8])}")
        if evidence_hits_all:
            evidence.append(f"落地/成熟证据命中：{'、'.join(evidence_hits_all[:8])}")
        if product_evidence:
            evidence.append(f"产品/技术：{'、'.join(product_evidence[:4])}")
        if scenario_evidence:
            evidence.append(f"客户/场景/行业：{'、'.join(scenario_evidence[:4])}")
        ranked.append({
            **row,
            'products': products,
            'capabilities': capabilities,
            'targetCapabilities': _unique(products + capabilities, 10),
            'matchedTerms': _unique(target_hits_all + evidence_hits_all, 16),
            'matchedFields': _unique(direct_fields, 12),
            'targetHits': target_hits_all,
            'evidenceHits': evidence_hits_all,
            'directApplicationHits': direct_application_hits,
            'productShapeHits': medical_product_hits,
            'excludeHits': exclude_hits,
            'score': score,
            'matchScore': score,
            'confidence': _confidence(score, direct_fields, evidence_hits_all, exclude_hits),
            'evidence': _unique(evidence, 8),
            'opportunityType': 'graph_fact_discovery',
        })
    return sorted(ranked, key=lambda item: int(item.get('score') or 0), reverse=True)[:limit]
