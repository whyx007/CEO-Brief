from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from modules.industry_chain.config import INDUSTRY_CHAIN_DEFAULT_LIMIT, INDUSTRY_CHAIN_MAX_LIMIT
from modules.industry_chain.services.analyst import analyze_with_llm, build_rule_answer
from modules.industry_chain.services.graph_serializer import add_edge, add_node, make_graph
from modules.industry_chain.services.neo4j_client import run_read_query, verify_connectivity
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


def _table(title: str, columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    return {'title': title, 'columns': columns, 'rows': rows}


def _analysis(mode: str, rows: list[dict[str, Any]], query: dict[str, Any], include: bool) -> tuple[str, dict[str, Any]]:
    if not include:
        return build_rule_answer(mode, rows), {'enabled': False, 'skipped': True}
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
        source = row.get('sourceEnterprise')
        target = row.get('targetEnterprise')
        if not source or not target:
            continue
        source_id = f'enterprise:{source}'
        target_id = f'enterprise:{target}'
        add_node(graph, source_id, source, 'Enterprise')
        add_node(graph, target_id, target, 'Enterprise')
        add_edge(graph, source_id, target_id, row.get('opportunityType') or 'OPPORTUNITY', '潜在合作', {
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
    keyword = str(payload.get('keyword') or '').strip()
    question = str(payload.get('question') or '').strip()
    limit = _limit(payload)
    if scope_type != 'all' and not keyword:
        raise HTTPException(status_code=400, detail='keyword_required')

    params = {'scopeType': scope_type, 'keyword': keyword, 'limit': limit}
    if scope_type == 'enterprise':
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
        evidence = []
        if row.get('subTrack'):
            evidence.append(f"同属{row.get('subTrack')}")
        if row.get('sourceStage') and row.get('targetStage'):
            evidence.append(f"{row.get('sourceStage')} -> {row.get('targetStage')} 存在上下游路径")
        if row.get('scenario'):
            evidence.append(f"共同关联应用场景：{row.get('scenario')}")
        opportunities.append({
            **row,
            'evidence': evidence,
            'cooperationLogic': '可作为上下游协同、联合方案或客户共拓线索，需结合产品规格、客户重合度和商务意愿进一步核验。',
            'suggestedAction': '建议由投后服务团队先做企业访谈和产品/客户匹配核验。',
            'opportunityTypeLabel': {
                'updown': '上下游协同',
                'scenario_joint': '场景共拓',
            }.get(opportunity_type, opportunity_type),
        })

    answer, llm_meta = _analysis('opportunities', opportunities, {
        'scopeType': scope_type,
        'keyword': keyword,
        'question': question,
    }, bool(payload.get('includeAnalysis')))
    table_rows = [[
        row.get('sourceEnterprise') or '',
        row.get('targetEnterprise') or '',
        row.get('opportunityTypeLabel') or row.get('opportunityType') or '',
        row.get('confidence') or '',
        row.get('subTrack') or row.get('scenario') or '',
        row.get('sourceStage') or '',
        row.get('targetStage') or '',
        '；'.join(_as_list(row.get('evidence'))),
    ] for row in opportunities]
    return {
        'ok': True,
        'mode': 'opportunities',
        'query': {'scopeType': scope_type, 'keyword': keyword, 'question': question},
        'answer': answer,
        'opportunities': opportunities,
        'graph': _opportunity_graph(opportunities),
        'tables': [_table('被投企业合作机会', ['企业A', '企业B', '机会类型', '置信', '依据对象', 'A环节', 'B环节', '图谱证据'], table_rows)],
        'meta': {
            'rowCount': len(opportunities),
            'elapsedMs': round((time.perf_counter() - started) * 1000),
            'cypherTemplates': templates,
            'llm': llm_meta,
        },
        'suggestedQuestions': _suggestions('opportunities'),
    }
