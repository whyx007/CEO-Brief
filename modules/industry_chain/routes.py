from __future__ import annotations

import time
import uuid
import re
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from modules.industry_chain.config import INDUSTRY_CHAIN_DEFAULT_LIMIT, INDUSTRY_CHAIN_MAX_LIMIT
from modules.industry_chain.services.analyst import analyze_with_llm, build_rule_answer
from modules.industry_chain.services.external_company_profile import (
    build_external_company_profile,
    flatten_profile_query_terms,
)
from modules.industry_chain.services.graph_fact_discovery import (
    build_fact_discovery_plan,
    rank_fact_discovery_rows,
    should_use_graph_fact_discovery,
)
from modules.industry_chain.services.graph_serializer import add_edge, add_node, make_graph
from modules.industry_chain.services.neo4j_client import run_read_query, verify_connectivity
from modules.industry_chain.services.opportunity_ranker import rank_external_company_opportunities
from modules.industry_chain.services import query_templates as qt

router = APIRouter()

OVERVIEW_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
_overview_cache: dict[str, Any] = {'loadedAt': 0.0, 'rows': None}
_analysis_jobs: dict[str, dict[str, Any]] = {}


def _limit(payload: dict[str, Any] | None = None, default: int = INDUSTRY_CHAIN_DEFAULT_LIMIT) -> int:
    raw = (payload or {}).get('limit', default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(1, min(INDUSTRY_CHAIN_MAX_LIMIT, value))


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value in (None, '') else [value])


def _first_text(values: Any) -> str:
    for item in _as_list(values):
        text = str(item or '').strip()
        if text and not text.startswith('暂无') and '未明确' not in text:
            return text
    return ''


def _query_terms(keyword: str) -> list[str]:
    text = str(keyword or '').strip()
    if not text:
        return []
    terms = [text]
    terms.extend(part for part in re.split(r'[\s,，、/；;:：()（）\-]+', text) if len(part) >= 2)
    for marker in ('AI', 'ai', '数据中心', '反恐'):
        if marker in text:
            terms.append(marker)
    result: list[str] = []
    for term in terms:
        if term and term not in result:
            result.append(term)
    return result[:8]


_REGION_TERMS = [
    '北京', '上海', '天津', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江', '江苏', '浙江', '安徽', '福建',
    '江西', '山东', '河南', '湖北', '湖南', '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海',
    '台湾', '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门', '西安', '深圳', '广州', '苏州', '南京',
    '杭州', '成都', '武汉', '合肥', '青岛', '宁波', '厦门', '长沙', '郑州',
]

_ORG_SUFFIX_PATTERN = re.compile(
    r'(股份有限公司|有限责任公司|有限公司|集团股份|集团有限公司|控股集团|控股有限公司|科技股份|科技有限公司|'
    r'股份|集团|控股|公司|厂|院|所|中心|大学|研究院|研究所|实验室)$'
)

_GENERIC_INDUSTRY_EXPANSIONS: list[tuple[tuple[str, ...], list[str]]] = [
    (('电力', '电网', '供电', '输电', '配电', '变电', '能源局'), [
        '电力', '电网', '智能电网', '变电', '输电', '配网', '储能', '新能源消纳',
        '巡检', '无人机巡检', '传感', '温度监测', '虚拟电厂', '变压器', '开关柜', '电缆',
    ]),
    (('能源', '新能源', '发电', '风电', '光伏', '储能'), [
        '能源', '新能源', '储能', '风电', '光伏', '发电', '调峰', '调频', '能源管理', '虚拟电厂',
    ]),
    (('汽车', '车企', '主机厂', '整车', '商用车', '乘用车'), [
        '汽车', '新能源汽车', '整车', '车载', '座舱', '智能驾驶', '热管理', '充电', '换电', '动力电池',
    ]),
    (('电池', '锂电', '动力电池'), [
        '电池', '动力电池', '锂电', '储能', '电池材料', 'BMS', '热管理', '电芯', '电池安全',
    ]),
    (('数据中心', '算力', '智算', '云计算'), [
        '数据中心', '算力', '智算', 'AI', '液冷', '储能', '光通信', '服务器', '电源管理', '网络互联',
    ]),
    (('航天', '卫星', '火箭', '航空', '飞机', '飞行器'), [
        '航天', '商业航天', '卫星', '遥感', '测控', '通信', '导航', '无人机', '光通信',
    ]),
    (('半导体', '芯片', '集成电路'), [
        '半导体', '芯片', '集成电路', '封装', '测试', '传感器', '功率器件', '光电芯片',
    ]),
    (('机器人', '无人机', '巡检', '智能装备'), [
        '机器人', '无人机', '巡检', '智能装备', '机器视觉', '导航', '控制', '传感',
    ]),
    (('医疗', '医院', '医药', '生物'), [
        '医疗', '医药', '生物', '传感', '检测', '影像', '诊断', '耗材',
    ]),
    (('化工', '材料', '新材料'), [
        '化工', '材料', '新材料', '导电材料', '散热', '涂层', '复合材料',
    ]),
    (('铁路', '轨道', '交通'), [
        '轨道交通', '铁路', '交通', '巡检', '传感', '电力设备', '通信', '安全监测',
    ]),
]


def _append_unique(target: list[str], values: list[str] | tuple[str, ...]) -> None:
    for value in values:
        term = str(value or '').strip()
        if term and len(term) >= 2 and term not in target:
            target.append(term)


def _company_name_terms(text: str) -> tuple[list[str], list[str]]:
    compact = re.sub(r'\s+', '', text)
    aliases: list[str] = []
    anchors: list[str] = []
    if compact:
        aliases.append(compact)
        anchors.append(compact)

    without_suffix = _ORG_SUFFIX_PATTERN.sub('', compact)
    if without_suffix and without_suffix != compact:
        aliases.append(without_suffix)
        anchors.append(without_suffix)

    for region in _REGION_TERMS:
        if region in compact:
            aliases.append(region)
            rest = compact.replace(region, '')
            rest = _ORG_SUFFIX_PATTERN.sub('', rest)
            if len(rest) >= 2:
                aliases.append(rest)

    parts = [part for part in re.split(r'[省市区县集团控股股份有限责任公司（）()]+', compact) if len(part) >= 2]
    _append_unique(aliases, parts)
    return aliases, anchors[:8]


def _external_company_terms(keyword: str) -> tuple[list[str], list[str]]:
    text = str(keyword or '').strip()
    aliases, anchor_terms = _company_name_terms(text)
    terms = [*_query_terms(text), *aliases]
    expansions: list[str] = []
    for markers, values in _GENERIC_INDUSTRY_EXPANSIONS:
        if any(marker in text for marker in markers):
            expansions.extend(values)
    for region in _REGION_TERMS:
        if region in text:
            expansions.append(region)
    result: list[str] = []
    for term in [*terms, *expansions]:
        if term and term not in result:
            result.append(term)
    anchors: list[str] = []
    for term in anchor_terms:
        if term and term not in anchors:
            anchors.append(term)
    return result[:32], anchors[:8]


def _table(title: str, columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    return {'title': title, 'columns': columns, 'rows': rows}


def _cooperation_scene(opportunity_type: str, keyword: str, row: dict[str, Any]) -> str:
    capability = _first_text(row.get('targetCapabilities'))
    scenario = _first_text(row.get('scenarios')) or _first_text(row.get('scenario'))
    customer = _first_text(row.get('customers'))
    stage = str(row.get('targetStage') or row.get('sourceStage') or '').strip()
    sub_track = str(row.get('subTrack') or '').strip()
    basis = scenario or stage or sub_track
    if opportunity_type == 'external_company':
        if customer and any(term in customer for term in ('国家电网', '国网', '南方电网', keyword)):
            return f"已有{customer}相关客户/合作线索，可优先核验能否向“{keyword}”复制推广。"
        if basis and capability:
            return f"可围绕{basis}，用{capability}与“{keyword}”开展试点、供应链配套或场景共创。"
        if capability:
            return f"可基于{capability}，面向“{keyword}”的业务场景做产品适配和客户验证。"
        return f"围绕“{keyword}”的产业链合作、供应链配套或场景共创。"
    if opportunity_type == 'technology_scope':
        if capability and basis:
            return f"围绕“{keyword}”技术方向，可在{basis}场景验证{capability}。"
        if capability:
            return f"围绕“{keyword}”技术方向进行{capability}能力验证、联合方案或客户拓展。"
        return f"围绕“{keyword}”技术方向进行能力验证、联合方案或客户场景拓展。"
    if opportunity_type == 'industry_direction':
        if basis and capability:
            return f"围绕“{keyword}”产业方向，可将{capability}纳入{basis}任务包。"
        return f"围绕“{keyword}”产业方向组建解决方案组合。"
    return '可作为上下游协同、联合方案或客户共拓线索。'


def _analysis(mode: str, rows: list[dict[str, Any]], query: dict[str, Any], include: bool) -> tuple[str, dict[str, Any]]:
    if not include:
        return build_rule_answer(mode, rows, query), {'enabled': False, 'skipped': True}
    return analyze_with_llm(mode, rows, query)


@router.post('/api/industry-chain/analyze-result')
def industry_chain_analyze_result(payload: dict[str, Any]) -> dict[str, Any]:
    payload = payload or {}
    mode = str(payload.get('mode') or 'company-updown').strip() or 'company-updown'
    rows = payload.get('rows') if isinstance(payload.get('rows'), list) else []
    query = payload.get('query') if isinstance(payload.get('query'), dict) else {}
    question = str(payload.get('question') or '').strip()
    if question:
        query = {**query, 'question': question}
    answer, llm_meta = analyze_with_llm(mode, rows, query)
    return {
        'ok': True,
        'mode': mode,
        'query': query,
        'answer': answer,
        'meta': {'llm': llm_meta},
    }


def _run_analysis_job(job_id: str, mode: str, rows: list[dict[str, Any]], query: dict[str, Any]) -> None:
    _analysis_jobs[job_id] = {**_analysis_jobs[job_id], 'status': 'running', 'startedAt': time.time()}
    try:
        answer, llm_meta = analyze_with_llm(mode, rows, query)
        _analysis_jobs[job_id] = {
            **_analysis_jobs[job_id],
            'status': 'done',
            'finishedAt': time.time(),
            'result': {
                'ok': True,
                'mode': mode,
                'query': query,
                'answer': answer,
                'meta': {'llm': llm_meta},
            },
        }
    except Exception as exc:
        _analysis_jobs[job_id] = {
            **_analysis_jobs[job_id],
            'status': 'error',
            'finishedAt': time.time(),
            'error': str(exc),
        }


@router.post('/api/industry-chain/analyze-result/jobs')
def start_industry_chain_analysis_job(payload: dict[str, Any], background_tasks: BackgroundTasks) -> dict[str, Any]:
    payload = payload or {}
    mode = str(payload.get('mode') or 'company-updown').strip() or 'company-updown'
    rows = payload.get('rows') if isinstance(payload.get('rows'), list) else []
    query = payload.get('query') if isinstance(payload.get('query'), dict) else {}
    question = str(payload.get('question') or '').strip()
    if question:
        query = {**query, 'question': question}
    job_id = uuid.uuid4().hex
    _analysis_jobs[job_id] = {
        'id': job_id,
        'status': 'queued',
        'createdAt': time.time(),
        'mode': mode,
        'query': query,
    }
    background_tasks.add_task(_run_analysis_job, job_id, mode, rows, query)
    return {'ok': True, 'jobId': job_id, 'status': 'queued'}


@router.get('/api/industry-chain/analyze-result/jobs/{job_id}')
def get_industry_chain_analysis_job(job_id: str) -> dict[str, Any]:
    job = _analysis_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='analysis_job_not_found')
    return {'ok': True, **job}


def _overview_graph(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    graph = make_graph()
    for row in rows:
        sub_track_id = row.get('subTrackId') or row.get('subTrack')
        stage_id = row.get('stageId') or row.get('stage')
        if sub_track_id:
            add_node(graph, f'subtrack:{sub_track_id}', row.get('subTrack') or sub_track_id, 'SubTrack', {
                'description': row.get('subTrackDescription') or '',
            })
        if stage_id:
            add_node(graph, f'stage:{stage_id}', row.get('stage') or stage_id, 'ChainStage', {
                'stageLevel': row.get('stageLevel') or '',
                'stageOrder': row.get('stageOrder'),
                'enterpriseCount': row.get('enterpriseCount') or 0,
            })
            add_edge(graph, f'subtrack:{sub_track_id}', f'stage:{stage_id}', 'HAS_STAGE', '包含环节')
        for enterprise in _as_list(row.get('enterprises')):
            enterprise_id = f'enterprise:{enterprise}'
            add_node(graph, enterprise_id, enterprise, 'Enterprise')
            if stage_id:
                add_edge(graph, enterprise_id, f'stage:{stage_id}', 'LOCATED_IN_STAGE', '位于环节')
    return graph


def _company_updown_graph(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    graph = make_graph()
    for row in rows:
        enterprise = row.get('enterprise')
        if not enterprise:
            continue
        enterprise_id = f'enterprise:{enterprise}'
        add_node(graph, enterprise_id, enterprise, 'Enterprise', {'matchLevel': row.get('matchLevel') or ''})

        for stage in _as_list(row.get('stages')):
            stage_id = f'stage:{stage}'
            add_node(graph, stage_id, stage, 'ChainStage')
            add_edge(graph, enterprise_id, stage_id, 'LOCATED_IN_STAGE', '位于环节')

        for stage in _as_list(row.get('upstreamStages')):
            stage_id = f'stage:{stage}'
            add_node(graph, stage_id, stage, 'ChainStage', {'direction': 'upstream'})
            for own_stage in _as_list(row.get('stages')):
                add_edge(graph, stage_id, f'stage:{own_stage}', 'UPSTREAM_OF', '上游')

        for stage in _as_list(row.get('downstreamStages')):
            stage_id = f'stage:{stage}'
            add_node(graph, stage_id, stage, 'ChainStage', {'direction': 'downstream'})
            for own_stage in _as_list(row.get('stages')):
                add_edge(graph, f'stage:{own_stage}', stage_id, 'UPSTREAM_OF', '下游')

        for name in _as_list(row.get('upstreamEnterprises'))[:20]:
            node_id = f'enterprise:{name}'
            add_node(graph, node_id, name, 'Enterprise', {'direction': 'upstream'})
            for stage in _as_list(row.get('upstreamStages')):
                add_edge(graph, node_id, f'stage:{stage}', 'LOCATED_IN_STAGE', '位于上游环节')

        for name in _as_list(row.get('downstreamEnterprises'))[:20]:
            node_id = f'enterprise:{name}'
            add_node(graph, node_id, name, 'Enterprise', {'direction': 'downstream'})
            for stage in _as_list(row.get('downstreamStages')):
                add_edge(graph, node_id, f'stage:{stage}', 'LOCATED_IN_STAGE', '位于下游环节')
    return graph


def _relation_rows(row: dict[str, Any], direction: str) -> list[dict[str, str]]:
    relation_key = 'upstreamRelations' if direction == 'upstream' else 'downstreamRelations'
    stage_key = 'upstreamStages' if direction == 'upstream' else 'downstreamStages'
    enterprise_key = 'upstreamEnterprises' if direction == 'upstream' else 'downstreamEnterprises'
    label = '上游' if direction == 'upstream' else '下游'
    relations: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in _as_list(row.get(relation_key)):
        if not isinstance(item, dict):
            continue
        stage = str(item.get('stage') or '').strip()
        enterprise = str(item.get('enterprise') or '').strip()
        if not stage or not enterprise:
            continue
        key = (label, stage, enterprise)
        if key not in seen:
            relations.append({'direction': label, 'stage': stage, 'enterprise': enterprise})
            seen.add(key)
    if relations:
        return relations
    fallback_stage = '、'.join(str(item) for item in _as_list(row.get(stage_key)) if item) or '未标注环节'
    for enterprise in _as_list(row.get(enterprise_key)):
        enterprise_name = str(enterprise or '').strip()
        if not enterprise_name:
            continue
        key = (label, fallback_stage, enterprise_name)
        if key not in seen:
            relations.append({'direction': label, 'stage': fallback_stage, 'enterprise': enterprise_name})
            seen.add(key)
    return relations


def _opportunity_graph(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    graph = make_graph()
    for row in rows:
        source = row.get('sourceEnterprise') or row.get('queryObject')
        target = row.get('targetEnterprise')
        if not source or not target:
            continue
        source_id = f'enterprise:{source}'
        target_id = f'enterprise:{target}'
        source_type = 'ExternalCompany' if row.get('queryObject') and source == row.get('queryObject') else 'Enterprise'
        add_node(graph, source_id, source, source_type)
        add_node(graph, target_id, target, 'Enterprise')
        add_edge(graph, source_id, target_id, row.get('cooperationMode') or row.get('opportunityType') or 'OPPORTUNITY', '潜在合作', {
            'confidence': row.get('confidence') or '',
            'scenario': row.get('scenario') or '',
            'subTrack': row.get('subTrack') or '',
        })
        if row.get('sourceStage'):
            stage_id = f"stage:{row.get('sourceStageId') or row.get('sourceStage')}"
            add_node(graph, stage_id, row.get('sourceStage'), 'ChainStage')
            add_edge(graph, source_id, stage_id, 'LOCATED_IN_STAGE', '位于环节')
        if row.get('targetStage'):
            stage_id = f"stage:{row.get('targetStageId') or row.get('targetStage')}"
            add_node(graph, stage_id, row.get('targetStage'), 'ChainStage')
            add_edge(graph, target_id, stage_id, 'LOCATED_IN_STAGE', '位于环节')
    return graph


def _suggestions(mode: str) -> list[str]:
    if mode == 'overview':
        return ['哪些环节暂未挂接企业？', '按企业数量排序产业链环节', '进入某条产业链看合作机会']
    if mode == 'company-updown':
        return ['这些相邻企业里哪些最适合先撮合？', '只看下游合作对象', '补充这家企业的关键能力']
    if mode == 'opportunities':
        return ['只看高置信合作机会', '按上下游协同强度排序', '把机会转成投后服务跟进清单']
    return []


def _dimension_queries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for dimension in _as_list(profile.get('cooperationDimensions')):
        if not isinstance(dimension, dict):
            continue
        terms = [term for term in _as_list(dimension.get('queryTerms')) if str(term or '').strip()]
        if not terms:
            continue
        result.append({
            'mode': dimension.get('mode') or '',
            'queryTerms': terms[:20],
        })
    return result


def _external_grouped_payload(grouped_rows: dict[str, list[dict[str, Any]]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions = [
        item for item in _as_list(profile.get('cooperationDimensions'))
        if isinstance(item, dict) and item.get('mode')
    ]
    payload: list[dict[str, Any]] = []
    for dimension in dimensions:
        mode = str(dimension.get('mode') or '')
        rows = grouped_rows.get(mode) or []
        payload.append({
            'mode': mode,
            'externalRole': dimension.get('externalRole') or '',
            'description': dimension.get('description') or '',
            'queryTerms': _as_list(dimension.get('queryTerms'))[:12],
            'count': len(rows),
            'opportunities': rows[:12],
        })
    return payload


@router.get('/api/industry-chain/status')
def industry_chain_status() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        verify_connectivity()
        node_counts = run_read_query(qt.STATUS_COUNTS)[0].get('nodeCounts', [])
        rel_counts = run_read_query(qt.STATUS_REL_COUNTS)[0].get('relationshipCounts', [])
        sub_tracks = run_read_query(qt.SUB_TRACKS)
    except Exception as exc:
        return {
            'ok': False,
            'module': 'industry-chain',
            'ready': False,
            'message': f'Neo4j 连接失败：{exc}',
            'elapsedMs': round((time.perf_counter() - started) * 1000),
        }
    return {
        'ok': True,
        'module': 'industry-chain',
        'ready': True,
        'message': '产业链分析模块就绪。',
        'nodeCounts': node_counts,
        'relationshipCounts': rel_counts,
        'subTracks': sub_tracks,
        'elapsedMs': round((time.perf_counter() - started) * 1000),
    }


@router.get('/api/industry-chain/overview')
def industry_chain_overview(includeAnalysis: bool = False, question: str = '', refresh: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    now = time.time()
    cached_rows = _overview_cache.get('rows')
    if not refresh and cached_rows is not None and now - float(_overview_cache.get('loadedAt') or 0) < OVERVIEW_CACHE_TTL_SECONDS:
        rows = cached_rows
        cache_hit = True
    else:
        rows = run_read_query(qt.OVERVIEW)
        _overview_cache['rows'] = rows
        _overview_cache['loadedAt'] = now
        cache_hit = False
    answer, llm_meta = _analysis('overview', rows, {'question': question.strip()}, includeAnalysis)
    table_rows = [[
        row.get('subTrack') or '',
        row.get('stageLevel') or '',
        row.get('stageOrder') or '',
        row.get('stage') or '',
        row.get('enterpriseCount') or 0,
        '、'.join(_as_list(row.get('enterprises'))[:6]),
    ] for row in rows]
    return {
        'ok': True,
        'mode': 'overview',
        'answer': answer,
        'graph': _overview_graph(rows),
        'tables': [_table('产业链环节分布', ['产业链', '层级', '顺序', '环节', '企业数', '企业示例'], table_rows)],
        'rows': rows,
        'meta': {
            'rowCount': len(rows),
            'elapsedMs': round((time.perf_counter() - started) * 1000),
            'cacheHit': cache_hit,
            'llm': llm_meta,
        },
        'query': {'question': question.strip()},
        'suggestedQuestions': _suggestions('overview'),
    }


@router.post('/api/industry-chain/company-updown')
def industry_chain_company_updown(payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    enterprise_name = str((payload or {}).get('enterpriseName') or (payload or {}).get('keyword') or '').strip()
    if not enterprise_name:
        raise HTTPException(status_code=400, detail='enterprise_name_required')
    limit = _limit(payload)
    rows = run_read_query(qt.COMPANY_UPDOWN, {
        'enterpriseName': enterprise_name,
        'limit': limit,
        'enterpriseLimit': 5,
    })
    question = str((payload or {}).get('question') or '').strip()
    answer, llm_meta = _analysis('company-updown', rows, {
        'enterpriseName': enterprise_name,
        'question': question,
    }, bool(payload.get('includeAnalysis')))
    relationship_rows = [
        [
            row.get('enterprise') or '',
            relation['direction'],
            relation['stage'],
            relation['enterprise'],
            '、'.join(_as_list(row.get('subTracks'))),
            '、'.join(_as_list(row.get('stages'))),
        ]
        for row in rows
        for relation in (_relation_rows(row, 'upstream') + _relation_rows(row, 'downstream'))
    ]
    return {
        'ok': True,
        'mode': 'company-updown',
        'query': {'enterpriseName': enterprise_name, 'question': question},
        'answer': answer,
        'graph': _company_updown_graph(rows),
        'tables': [_table('上下游关联企业明细', ['目标企业', '关联方向', '关联环节', '关联企业', '产业链', '目标所在环节'], relationship_rows)],
        'relationshipRows': relationship_rows,
        'rows': rows,
        'meta': {
            'rowCount': len(rows),
            'elapsedMs': round((time.perf_counter() - started) * 1000),
            'llm': llm_meta,
        },
        'suggestedQuestions': _suggestions('company-updown'),
    }


@router.post('/api/industry-chain/opportunities')
def industry_chain_opportunities(payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    payload = payload or {}
    scope_type = str(payload.get('scopeType') or 'all').strip() or 'all'
    opportunity_mode = str(payload.get('opportunityMode') or scope_type or 'external_company').strip() or 'external_company'
    keyword = str(payload.get('keyword') or '').strip()
    question = str(payload.get('question') or '').strip()
    limit = _limit(payload)
    if should_use_graph_fact_discovery(question, keyword, opportunity_mode):
        opportunity_mode = 'graph_fact_discovery'
    if opportunity_mode in {'external_company', 'technology_scope', 'industry_direction'} and not keyword:
        raise HTTPException(status_code=400, detail='keyword_required')

    primary_terms = _query_terms(keyword)
    external_profile: dict[str, Any] | None = None
    grouped_opportunities: list[dict[str, Any]] = []
    fact_discovery_plan: dict[str, Any] | None = None
    if opportunity_mode == 'graph_fact_discovery':
        fact_discovery_plan = build_fact_discovery_plan(question, keyword)
        query_terms = _as_list(fact_discovery_plan.get('targetTerms'))
        anchor_terms = query_terms[:8]
    elif opportunity_mode == 'external_company':
        external_profile = build_external_company_profile(keyword)
        query_terms = flatten_profile_query_terms(external_profile)
        anchor_terms = _as_list(external_profile.get('aliases'))[:8]
    else:
        query_terms, anchor_terms = primary_terms, primary_terms
    params = {
        'scopeType': scope_type,
        'keyword': keyword,
        'primaryTerms': primary_terms,
        'anchorTerms': anchor_terms,
        'queryTerms': query_terms,
        'candidateLimit': min(max(limit * 4, 20), 80),
        'limit': limit,
    }
    if opportunity_mode == 'graph_fact_discovery':
        assert fact_discovery_plan is not None
        raw_rows = run_read_query(qt.GRAPH_FACT_DISCOVERY_ENTERPRISE_CONTEXT, {
            'targetTerms': _as_list(fact_discovery_plan.get('targetTerms'))[:100],
            'evidenceTerms': _as_list(fact_discovery_plan.get('evidenceTerms'))[:100],
            'excludeTerms': _as_list(fact_discovery_plan.get('excludeTerms'))[:40],
            'candidateLimit': 500,
        })
        rows = rank_fact_discovery_rows(raw_rows, fact_discovery_plan, limit)
        templates = ['graph_fact_discovery_enterprise_context']
    elif opportunity_mode == 'external_company':
        assert external_profile is not None
        dimension_queries = _dimension_queries(external_profile)
        rows = run_read_query(qt.OPPORTUNITIES_EXTERNAL_COMPANY_MULTIDIMENSION, {
            **params,
            'dimensionQueries': dimension_queries,
            'strongTerms': _as_list(external_profile.get('strongTerms'))[:60],
            'weakTerms': _as_list(external_profile.get('weakTerms'))[:30],
            'candidateLimit': 500,
        })
        rows, grouped_by_mode = rank_external_company_opportunities(rows, external_profile, limit)
        grouped_opportunities = _external_grouped_payload(grouped_by_mode, external_profile)
        templates = ['opportunities_external_company_multidimension']
    elif opportunity_mode == 'technology_scope':
        rows = run_read_query(qt.OPPORTUNITIES_TECHNOLOGY_SCOPE, params)
        templates = ['opportunities_technology_scope']
    elif opportunity_mode == 'industry_direction':
        rows = run_read_query(qt.OPPORTUNITIES_INDUSTRY_DIRECTION, params)
        templates = ['opportunities_industry_direction']
    elif scope_type == 'enterprise':
        rows = run_read_query(qt.OPPORTUNITIES_UPDOWN_BY_ENTERPRISE, params)
        templates = ['opportunities_updown_by_enterprise']
    else:
        updown_rows = run_read_query(qt.OPPORTUNITIES_UPDOWN_BY_SUBTRACK, params)
        remaining = max(1, limit - len(updown_rows))
        scenario_rows = run_read_query(qt.OPPORTUNITIES_SCENARIO, {**params, 'limit': remaining})
        rows = (updown_rows + scenario_rows)[:limit]
        templates = ['opportunities_updown_by_subtrack', 'opportunities_scenario']

    opportunities = []
    for row in rows:
        opportunity_type = row.get('opportunityType') or 'opportunity'
        evidence = _as_list(row.get('evidence'))
        if row.get('subTrack'):
            evidence.append(f"同属{row.get('subTrack')}")
        if row.get('targetCapabilities'):
            evidence.append(f"能力匹配：{'、'.join(_as_list(row.get('targetCapabilities'))[:5])}")
        if row.get('customers'):
            evidence.append(f"客户线索：{'、'.join(_as_list(row.get('customers'))[:5])}")
        if row.get('suppliers'):
            evidence.append(f"供应商线索：{'、'.join(_as_list(row.get('suppliers'))[:5])}")
        if row.get('scenarios'):
            evidence.append(f"场景线索：{'、'.join(_as_list(row.get('scenarios'))[:5])}")
        if row.get('sourceStage') and row.get('targetStage'):
            evidence.append(f"{row.get('sourceStage')} -> {row.get('targetStage')} 存在上下游路径")
        if row.get('scenario'):
            evidence.append(f"共同关联应用场景：{row.get('scenario')}")
        target_enterprise = row.get('targetEnterprise') or row.get('sourceEnterprise') or ''
        cooperation_scene = _cooperation_scene(opportunity_type, keyword, row)
        if opportunity_mode == 'graph_fact_discovery':
            products = '、'.join(_as_list(row.get('products'))[:3]) or '相关产品/技术'
            matched_terms = '、'.join(_as_list(row.get('matchedTerms'))[:6])
            cooperation_scene = f"图谱事实发现：{products} 已命中“{question or keyword}”相关场景/落地证据"
            if matched_terms:
                cooperation_scene = f"{cooperation_scene}。匹配词：{matched_terms}"
        elif opportunity_mode == 'external_company':
            mode_label = {
                'supply_to_external': '外部企业作为客户',
                'external_supply_to_portfolio': '外部企业作为供应商',
                'joint_r_and_d': '联合研发',
                'shared_customer': '客户协同',
                'scenario_landing': '场景落地',
                'factory_or_operation_support': '厂务与运营配套',
            }.get(str(row.get('cooperationMode') or ''), '外部公司合作')
            matched_terms = '、'.join(_as_list(row.get('matchedTerms'))[:6])
            matched_dimension = str(row.get('matchedDimension') or mode_label)
            cooperation_scene = f"{mode_label}：{matched_dimension}"
            if matched_terms:
                cooperation_scene = f"{cooperation_scene}。匹配词：{matched_terms}"
        opportunities.append({
            **row,
            'queryObject': keyword,
            'sourceEnterprise': row.get('sourceEnterprise') or keyword,
            'investedEnterprise': target_enterprise,
            'evidence': list(dict.fromkeys(str(item) for item in evidence if item)),
            'cooperationScene': cooperation_scene,
            'cooperationLogic': f"{cooperation_scene} 需结合产品规格、客户重合度和商务意愿进一步核验。",
            'suggestedAction': '建议由投后服务团队先做企业访谈和产品/客户匹配核验。',
            'opportunityTypeLabel': {
                'external_company': {
                    'supply_to_external': '外部企业作为客户',
                    'external_supply_to_portfolio': '外部企业作为供应商',
                    'joint_r_and_d': '联合研发',
                    'shared_customer': '客户协同',
                    'scenario_landing': '场景落地',
                    'factory_or_operation_support': '厂务与运营配套',
                }.get(str(row.get('cooperationMode') or ''), '外部公司合作'),
                'technology_scope': '技术能力匹配',
                'industry_direction': '产业方向协同',
                'updown': '上下游协同',
                'scenario_joint': '场景共拓',
            }.get(opportunity_type, opportunity_type),
        })

    answer, llm_meta = _analysis('opportunities', opportunities, {
        'scopeType': scope_type,
        'opportunityMode': opportunity_mode,
        'keyword': keyword,
        'question': question,
        'externalProfile': external_profile,
        'factDiscoveryPlan': fact_discovery_plan,
        'groupedOpportunities': grouped_opportunities,
    }, bool(payload.get('includeAnalysis')))
    table_rows = [[
        row.get('investedEnterprise') or row.get('sourceEnterprise') or '',
        row.get('opportunityTypeLabel') or row.get('opportunityType') or '',
        row.get('confidence') or '',
        row.get('subTrack') or row.get('scenario') or '、'.join(_as_list(row.get('scenarios'))[:2]),
        row.get('targetStage') or row.get('sourceStage') or '',
        '、'.join(_as_list(row.get('targetCapabilities'))[:5]),
        row.get('cooperationScene') or '',
        '；'.join(_as_list(row.get('evidence'))),
    ] for row in opportunities]
    return {
        'ok': True,
        'mode': 'opportunities',
        'query': {'scopeType': scope_type, 'opportunityMode': opportunity_mode, 'keyword': keyword, 'question': question},
        'answer': answer,
        'externalProfile': external_profile,
        'factDiscoveryPlan': fact_discovery_plan,
        'groupedOpportunities': grouped_opportunities,
        'opportunities': opportunities,
        'graph': _opportunity_graph(opportunities),
        'tables': [_table('被投企业合作机会', ['被投企业', '机会类型', '置信', '依据对象', '匹配环节', '匹配能力', '合作场景', '图谱证据'], table_rows)],
        'meta': {
            'rowCount': len(opportunities),
            'elapsedMs': round((time.perf_counter() - started) * 1000),
            'cypherTemplates': templates,
            'llm': llm_meta,
        },
        'suggestedQuestions': _suggestions('opportunities'),
    }
