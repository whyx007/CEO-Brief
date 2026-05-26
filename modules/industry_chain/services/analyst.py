from __future__ import annotations

import re
from typing import Any

from services.llm_client import DeepSeekClient

POWER_GRID_TERMS = ('国网', '国家电网', '电力电网', '供电', '电网')
COOPERATION_MODE_LABELS = {
    'supply_to_external': '目标公司作为客户',
    'external_supply_to_portfolio': '目标公司作为供应商',
    'joint_r_and_d': '联合研发',
    'shared_customer': '客户协同',
    'scenario_landing': '场景落地',
    'factory_or_operation_support': '厂务与运营配套',
}
FIELD_LABELS = {
    'products': '产品',
    'capabilities': '能力',
    'targetCapabilities': '能力/产品',
    'scenarios': '场景',
    'demands': '需求',
    'customers': '客户',
    'industries': '行业',
    'subTrack': '产业链/赛道',
    'targetStage': '环节',
    'suppliers': '供应商',
}

OPPORTUNITY_CARD_LABEL_PATTERN = (
    r'(?:产业方向协同|技术能力匹配|上下游协同|场景共拓|公司合作|'
    r'目标公司作为客户|目标公司作为供应商|联合研发|客户协同|场景落地|厂务与运营配套)'
)


def _compact(value: Any, limit: int = 5000) -> str:
    text = str(value)
    return text[:limit]


def _strip_appended_opportunity_cards(text: str) -> str:
    value = str(text or '').strip()
    if not value:
        return ''
    company_line = r'[^\n]{2,80}(?:公司|企业|中心|院|所|集团|厂|大学|实验室)[^\n]*'
    confidence_line = r'(?:high|medium|low|高|中|低)'
    return re.sub(
        rf'\n+(?:#{{1,6}}\s*)?{OPPORTUNITY_CARD_LABEL_PATTERN}\s*\n{company_line}\s*\n{confidence_line}\s*\n[\s\S]*$',
        '',
        value,
        flags=re.IGNORECASE,
    ).strip()


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value in (None, '') else [value])


def _contains_any(value: Any, terms: tuple[str, ...]) -> bool:
    return any(term in str(value or '') for term in terms)


def _join(values: Any, limit: int = 4) -> str:
    result: list[str] = []
    for item in _as_list(values):
        text = str(item or '').strip()
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return '、'.join(result)


def _join_field_labels(values: Any, limit: int = 4) -> str:
    labels = [FIELD_LABELS.get(str(item or ''), str(item or '')) for item in _as_list(values)]
    return _join(labels, limit)


def _profile_summary(profile: dict[str, Any]) -> str:
    products = _join((profile.get('coreProducts') or []) + (profile.get('coreTechnologies') or []), 8) or '规则画像未明确'
    position = profile.get('chainPosition') or '规则画像未明确'
    needs = _join(profile.get('upstreamNeeds'), 6) or '待核验'
    applications = _join((profile.get('downstreamApplications') or []) + (profile.get('targetCustomers') or []), 6) or '待核验'
    return (
        f'- 业务与位置：{position}；核心产品/技术：{products}。\n'
        f'- 需求与场景：上游需求包括 {needs}；下游应用/客户包括 {applications}。'
    )


def _format_report_table(rows: list[dict[str, Any]], keyword: str, *, with_existing_customer: bool) -> str:
    table = [
        '| 企业 | 所在地/产业链 | 核心能力 | 已有客户/图谱线索 | 可能的合作方向 |',
        '|------|------------|---------|----------------|--------------|',
    ]
    selected: list[dict[str, Any]] = []
    for row in rows:
        customers = _join(row.get('customers'), 5)
        has_power_customer = _contains_any(customers, POWER_GRID_TERMS)
        if with_existing_customer != has_power_customer:
            continue
        selected.append(row)
        if len(selected) >= 10:
            break
    if not selected and not with_existing_customer:
        selected = rows[:10]
    for row in selected:
        enterprise = row.get('investedEnterprise') or row.get('targetEnterprise') or row.get('sourceEnterprise') or '-'
        place_or_track = row.get('subTrack') or row.get('targetStage') or row.get('sourceStage') or '图谱未标注'
        capabilities = _join(row.get('targetCapabilities'), 5) or _join(row.get('scenarios'), 3) or '图谱未标注'
        evidence = _join(row.get('customers'), 4) or '暂无明确客户标签'
        scene = row.get('cooperationScene') or row.get('cooperationLogic') or f'围绕“{keyword}”的电网业务场景进一步核验合作可行性'
        table.append(f'| **{enterprise}** | {place_or_track} | {capabilities} | {evidence} | {scene} |')
    if len(table) == 2:
        table.append('| - | - | - | - | 当前图谱未检索到符合该分组的企业 |')
    return '\n'.join(table)


def _build_target_company_report(rows: list[dict[str, Any]], query: dict[str, Any]) -> str:
    keyword = str(query.get('keyword') or query.get('enterpriseName') or '目标公司').strip()
    existing_rows = [
        row for row in rows
        if _contains_any(_join(row.get('customers'), 8), POWER_GRID_TERMS)
    ]
    potential_rows = [row for row in rows if row not in existing_rows]
    priority_rows = (existing_rows[:4] + potential_rows[:6])[:7]
    priority_table = [
        '| 优先级 | 企业 | 推荐理由 |',
        '|-------|------|---------|',
    ]
    priority_labels = ['第一优先级', '第一优先级', '第一优先级', '第二优先级', '第二优先级', '第二优先级', '第三优先级']
    for index, row in enumerate(priority_rows):
        enterprise = row.get('investedEnterprise') or row.get('targetEnterprise') or row.get('sourceEnterprise') or '-'
        capabilities = _join(row.get('targetCapabilities'), 3)
        customers = _join(row.get('customers'), 3)
        reason_parts = []
        if customers:
            reason_parts.append(f'已有客户线索：{customers}')
        if capabilities:
            reason_parts.append(f'能力匹配：{capabilities}')
        if row.get('cooperationScene'):
            reason_parts.append(str(row.get('cooperationScene')))
        priority_table.append(f"| {priority_labels[index] if index < len(priority_labels) else '第三优先级'} | **{enterprise}** | {'；'.join(reason_parts[:2]) or '与目标公司存在图谱匹配线索，建议进一步核验'} |")
    if len(priority_table) == 2:
        priority_table.append('| - | - | 当前图谱未返回可排序机会 |')
    directions = [
        row.get('targetStage') or row.get('subTrack') or _join(row.get('scenarios'), 1)
        for row in rows[:12]
        if row.get('targetStage') or row.get('subTrack') or row.get('scenarios')
    ]
    direction_text = '、'.join(list(dict.fromkeys(str(item) for item in directions if item))[:3]) or '电网设备在线监测、储能与新能源消纳、输配电智能运维'
    return (
        f'## 被投企业与{keyword}潜在合作分析报告\n\n'
        f'### 一、已与国网体系合作的企业（{len(existing_rows)}家）——深化合作空间大\n\n'
        f'{_format_report_table(existing_rows, keyword, with_existing_customer=True)}\n\n'
        f'### 二、尚未合作但有强相关能力的潜在企业（{len(potential_rows)}家）\n\n'
        f'{_format_report_table(potential_rows, keyword, with_existing_customer=False)}\n\n'
        '### 三、重点推荐（综合评估）\n\n'
        '直接从合作优先级排序：\n\n'
        f"{chr(10).join(priority_table)}\n\n"
        f'**总结**：图谱中与{keyword}潜在合作的企业主要集中在 **{direction_text}** 等方向。'
        '建议先从已有国网体系客户线索、陕西本地/周边可交付能力、以及可快速试点的设备监测和能源管理场景切入。'
    )


def _build_external_company_report(rows: list[dict[str, Any]], query: dict[str, Any]) -> str:
    profile = query.get('externalProfile') if isinstance(query.get('externalProfile'), dict) else {}
    grouped = query.get('groupedOpportunities') if isinstance(query.get('groupedOpportunities'), list) else []
    keyword = str(query.get('keyword') or profile.get('companyName') or (rows[0].get('queryObject') if rows else '') or '目标公司').strip()
    high = sum(1 for row in rows if row.get('confidence') == 'high')
    medium = sum(1 for row in rows if row.get('confidence') == 'medium')
    overview_table = [
        '| 合作方向 | 目标公司角色 | 候选企业数 | 主要切入点 |',
        '|---------|-------------|-----------|-----------|',
    ]
    for group in grouped:
        overview_table.append(
            f"| {group.get('description') or COOPERATION_MODE_LABELS.get(str(group.get('mode') or ''), '') or '-'} | {COOPERATION_MODE_LABELS.get(str(group.get('mode') or ''), '') or '-'} | "
            f"{group.get('count') or 0} | {_join(group.get('queryTerms'), 6) or '待核验'} |"
        )
    if len(overview_table) == 2:
        overview_table.append('| - | - | 0 | 当前图谱未召回候选 |')

    sections: list[str] = []
    for group in grouped:
        items = group.get('opportunities') if isinstance(group.get('opportunities'), list) else []
        if not items:
            continue
        lines = [f"### {group.get('description') or group.get('mode')}"]
        for item in items[:5]:
            enterprise = item.get('investedEnterprise') or item.get('targetEnterprise') or '-'
            fields = _join_field_labels(item.get('matchedFields'), 4)
            terms = _join(item.get('matchedTerms'), 6)
            evidence = _join(item.get('evidence'), 3)
            lines.append(f"- **{enterprise}**：{fields or '图谱字段'} 命中 {terms or '画像词'}；{evidence or '需补充证据'}。")
        sections.append('\n'.join(lines))
    recommendations = [
        '| 优先级 | 被投企业 | 合作模式 | 推荐理由 | 证据 |',
        '|-------|---------|---------|---------|------|',
    ]
    for index, row in enumerate(rows[:8], start=1):
        enterprise = row.get('investedEnterprise') or row.get('targetEnterprise') or '-'
        mode = row.get('opportunityTypeLabel') or COOPERATION_MODE_LABELS.get(str(row.get('cooperationMode') or ''), '') or '公司合作'
        terms = _join(row.get('matchedTerms'), 5)
        evidence = _join(row.get('evidence'), 2)
        recommendations.append(f"| {index} | **{enterprise}** | {mode} | 命中{terms or '画像相关词'}，置信度{row.get('confidence') or '-'} | {evidence or '需核验'} |")
    if len(recommendations) == 2:
        recommendations.append('| - | - | - | 当前图谱未返回可排序机会 | - |')
    return (
        f'目标公司：**{keyword}**\n\n'
        '## 一、目标公司业务画像\n\n'
        f"{_profile_summary(profile)}\n\n"
        '## 二、合作机会总览\n\n'
        f"{chr(10).join(overview_table)}\n\n"
        '## 三、分方向合作机会\n\n'
        f"{chr(10).join(sections) if sections else '当前图谱未发现明确分方向合作机会。'}\n\n"
        '## 四、重点推荐\n\n'
        f"{chr(10).join(recommendations)}\n\n"
        '## 五、数据限制与需核验事项\n\n'
        f'- 当前召回基于规则画像和 Neo4j 证据，共返回 {len(rows)} 条机会，其中高置信 {high} 条、中置信 {medium} 条。\n'
        '- 规则画像不等同于企业事实尽调，进入商务推进前需核验产品规格、客户关系、交付地区和合作意愿。'
    )


def _build_graph_fact_discovery_report(rows: list[dict[str, Any]], query: dict[str, Any]) -> str:
    plan = query.get('factDiscoveryPlan') if isinstance(query.get('factDiscoveryPlan'), dict) else {}
    question = str(query.get('question') or plan.get('question') or '图谱事实发现').strip()
    high = sum(1 for row in rows if row.get('confidence') == 'high')
    medium = sum(1 for row in rows if row.get('confidence') == 'medium')
    table = [
        '| 排名 | 被投企业 | 产品/技术 | 已应用/落地证据 | 证据等级 |',
        '|-----|---------|-----------|----------------|---------|',
    ]
    for index, row in enumerate(rows[:20], start=1):
        enterprise = row.get('investedEnterprise') or row.get('targetEnterprise') or '-'
        product = _join(row.get('targetCapabilities') or row.get('products'), 4) or '图谱未标注'
        evidence = _join(row.get('evidence'), 3) or _join(row.get('customers'), 3) or _join(row.get('scenarios'), 3) or '需补充核验'
        table.append(f"| {index} | **{enterprise}** | {product} | {evidence} | {row.get('confidence') or '-'} |")
    if len(table) == 2:
        table.append('| - | - | 当前图谱未返回可排序企业 | - | - |')
    target_terms = _join(plan.get('targetTerms'), 10) if plan else ''
    evidence_terms = _join(plan.get('evidenceTerms'), 10) if plan else ''
    return (
        '## 一、核心发现\n'
        f'- 针对“{question}”，当前从 Neo4j 被投企业图谱中筛出 **{len(rows)}** 家候选企业，其中高置信 **{high}** 家、中置信 **{medium}** 家。\n'
        '- 本模式按“产品/技术 + 目标场景 + 客户/应用/认证/商业化证据”排序，不把目标机构误当成外部合作公司。\n\n'
        '## 二、已应用/落地企业清单\n\n'
        f"{chr(10).join(table)}\n\n"
        '## 三、检索与筛选口径\n'
        f"- 目标场景词：{target_terms or '未显式生成'}。\n"
        f"- 落地证据词：{evidence_terms or '未显式生成'}。\n"
        '- 高置信通常需要同时命中产品/技术与客户、场景、认证或成熟度证据；仅命中泛行业词的企业会被降级。\n\n'
        '## 四、数据限制\n'
        '- 当前结论只基于 Neo4j 已入库字段，若企业原始材料中的认证、客户或科室信息未结构化入图，仍可能漏召回或低估。'
    )


def _build_technology_scope_report(rows: list[dict[str, Any]], query: dict[str, Any]) -> str:
    keyword = str(query.get('keyword') or '目标技术领域').strip()
    high = sum(1 for row in rows if row.get('confidence') == 'high')
    medium = sum(1 for row in rows if row.get('confidence') == 'medium')
    stage_groups: dict[str, list[dict[str, Any]]] = {}
    scene_groups: dict[str, list[str]] = {}
    subfield_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        stage = row.get('targetStage') or row.get('subTrack') or '未标注环节'
        stage_groups.setdefault(str(stage), []).append(row)
        enterprise = row.get('investedEnterprise') or row.get('targetEnterprise') or '-'
        subfield = row.get('subTrack') or row.get('targetStage') or _join(row.get('industries'), 1) or _join(row.get('scenarios'), 1) or '未标注细分领域'
        subfield_groups.setdefault(str(subfield), []).append(row)
        for scene in _as_list(row.get('scenarios') or row.get('demands')):
            scene_text = str(scene or '').strip()
            if scene_text:
                scene_groups.setdefault(scene_text, [])
                if enterprise not in scene_groups[scene_text]:
                    scene_groups[scene_text].append(enterprise)

    core_table = [
        '| 序号 | 被投企业 | 主要环节/方向 | 可发挥作用 | 图谱依据 |',
        '|:---:|----------|--------------|------------|----------|',
    ]
    for index, row in enumerate(rows[:20], start=1):
        enterprise = row.get('investedEnterprise') or row.get('targetEnterprise') or '-'
        stage = row.get('targetStage') or row.get('subTrack') or '未标注环节'
        capability = _join(row.get('targetCapabilities'), 4) or _join(row.get('products'), 3) or '图谱未标注'
        evidence = _join(row.get('matchedTerms'), 4) or _join(row.get('scenarios'), 2) or _join(row.get('industries'), 2) or '需补充核验'
        core_table.append(f'| {index} | **{enterprise}** | {stage} | 可在{keyword}相关的{capability}方向发挥作用 | {evidence} |')
    if len(core_table) == 2:
        core_table.append('| - | - | - | 当前图谱未召回相关被投企业 | - |')

    stage_lines = []
    for stage, items in sorted(stage_groups.items(), key=lambda pair: len(pair[1]), reverse=True)[:8]:
        names = _join([item.get('investedEnterprise') or item.get('targetEnterprise') for item in items], 6)
        caps = _join([cap for item in items for cap in _as_list(item.get('targetCapabilities'))], 5)
        stage_lines.append(f'- **{stage}**：{names or "暂无企业名"}；主要能力包括 {caps or "图谱未标注"}。')

    matrix = [
        '| 场景/需求 | 匹配企业 | 作用说明 |',
        '|-----------|----------|----------|',
    ]
    for scene, enterprises in list(scene_groups.items())[:10]:
        matrix.append(f'| {scene} | {_join(enterprises, 6) or "-"} | 可作为{keyword}领域的产品、技术或解决方案支撑。 |')
    if len(matrix) == 2:
        matrix.append('| - | - | 当前图谱未形成明确场景标签 |')

    all_capabilities = _join([cap for row in rows for cap in _as_list(row.get('targetCapabilities'))], 10) or '相关产品/技术能力'
    customer_names = _join([customer for row in rows for customer in _as_list(row.get('customers'))], 8)
    supplier_names = _join([supplier for row in rows for supplier in _as_list(row.get('suppliers'))], 6)
    scene_names = _join([scene for row in rows for scene in _as_list(row.get('scenarios'))], 8)
    strong_enterprises = _join([
        row.get('investedEnterprise') or row.get('targetEnterprise')
        for row in rows
        if row.get('confidence') == 'high'
    ], 8)
    subfield_lines = []
    for subfield, items in sorted(subfield_groups.items(), key=lambda pair: len(pair[1]), reverse=True)[:8]:
        names = _join([item.get('investedEnterprise') or item.get('targetEnterprise') for item in items], 5)
        caps = _join([cap for item in items for cap in _as_list(item.get('targetCapabilities'))], 4)
        scenes = _join([scene for item in items for scene in _as_list(item.get('scenarios'))], 3)
        subfield_lines.append(
            f'- **{subfield}**：代表企业 {names or "暂无企业名"}；优势集中在 {caps or "图谱未标注能力"}；'
            f'主要场景为 {scenes or "待进一步明确"}。'
        )
    weakness_parts = []
    if any((not row.get('targetStage') and not row.get('subTrack')) for row in rows):
        weakness_parts.append('部分企业尚未清晰挂接到产业链环节或细分赛道，横向比较时需要人工归类')
    if sum(1 for row in rows if _as_list(row.get('customers'))) < max(1, len(rows) // 3):
        weakness_parts.append('明确客户/交付线索覆盖不足，商业化强弱还需要结合尽调核验')
    if sum(1 for row in rows if _as_list(row.get('suppliers'))) < max(1, len(rows) // 4):
        weakness_parts.append('供应链上下游标签偏少，暂难完整判断配套与协同能力')
    weakness_text = '；'.join(weakness_parts) or '主要短板不在能力召回，而在产品规格、客户重合度和规模化交付数据仍需进一步核验'

    return (
        f'# {keyword}产业链分析报告\n\n'
        '## 一、核心发现\n\n'
        f'- 当前从 Neo4j 被投企业图谱中召回 **{len(rows)}** 家与“{keyword}”相关的被投企业，其中高置信 **{high}** 家、中置信 **{medium}** 家。\n'
        f'- 相关企业主要分布在 **{_join(list(stage_groups.keys()), 6) or "未标注环节"}** 等环节，可用于判断“哪些被投企业在什么环节发挥作用”。\n\n'
        '## 二、相关被投企业清单\n\n'
        f"{chr(10).join(core_table)}\n\n"
        '## 三、产业链环节分布\n\n'
        f"{chr(10).join(stage_lines) if stage_lines else '- 当前图谱未返回明确环节。'}\n\n"
        '## 四、场景-企业匹配矩阵\n\n'
        f"{chr(10).join(matrix)}\n\n"
        '## 五、总结\n\n'
        f'- **总体优势**：被投企业在“{keyword}”领域已形成 {all_capabilities} 等能力基础；'
        f'{f"其中 {strong_enterprises} 等企业匹配度较高。" if strong_enterprises else "当前候选企业可作为进一步筛选池。"}'
        f'{f"已有客户/场景线索包括 {customer_names or scene_names}。" if (customer_names or scene_names) else ""}\n'
        f'- **主要短板**：{weakness_text}。'
        f'{f"供应链相关线索包括 {supplier_names}，但仍需判断关键环节是否可控。" if supplier_names else ""}\n'
        '- **细分领域判断**：\n'
        f"{chr(10).join(subfield_lines) if subfield_lines else '- 当前图谱未形成明确细分领域分组。'}"
    )


def _build_industry_direction_report(rows: list[dict[str, Any]], query: dict[str, Any]) -> str:
    keyword = str(query.get('keyword') or '目标技术命题').strip()
    high = sum(1 for row in rows if row.get('confidence') == 'high')
    medium = sum(1 for row in rows if row.get('confidence') == 'medium')
    capabilities = _join([cap for row in rows for cap in _as_list(row.get('targetCapabilities'))], 12) or '相关产品/技术能力'
    scenarios = _join([scene for row in rows for scene in _as_list(row.get('scenarios'))], 10) or keyword
    customers = _join([customer for row in rows for customer in _as_list(row.get('customers'))], 8)
    suppliers = _join([supplier for row in rows for supplier in _as_list(row.get('suppliers'))], 8)
    is_compute_cooling = any(term in keyword for term in ('算力', '智算', '数据中心', '机房')) and '散热' in keyword
    is_notebook_cooling = any(term in keyword for term in ('电竞', '笔记本', '消费电子', '终端')) and '散热' in keyword
    if is_compute_cooling:
        domain_focus = 'AI 算力中心散热偏机房级热管理，重点不是单机散热材料，而是液冷/冷板/浸没式方案、供配电协同、PUE、运维监控和工程交付。'
        default_scene = '智算中心液冷改造或新建机房冷却系统验证'
        customer_targets = '智算中心业主、云厂商、IDC 运营方或园区算力中心'
        delivery_support = '液冷系统集成商、机房工程方、CDU/冷却塔/管路配套、运维监控和能耗优化资源'
        core_metric = 'PUE、单柜功率密度、冷却效率、漏液风险、连续运行稳定性、运维成本'
    elif is_notebook_cooling:
        domain_focus = '电竞笔记本散热偏终端级热管理，重点是导热材料、热管/均热板/石墨片/风扇模组、轻薄化结构和可靠性测试。'
        default_scene = '电竞笔记本整机热设计和散热模组验证'
        customer_targets = '笔记本品牌方、ODM/OEM 厂商或散热模组供应商'
        delivery_support = 'ODM/OEM、散热模组厂、可靠性测试、结构设计和小批量试制资源'
        core_metric = 'CPU/GPU 温度、表面温度、噪声、厚度重量、成本、可靠性测试结果'
    else:
        domain_focus = f'{keyword}需要先拆成可验证场景，再判断被投企业能力、客户需求和工程交付资源是否能闭环。'
        default_scene = keyword
        customer_targets = '目标客户、园区运营方或行业龙头企业'
        delivery_support = '制造、检测认证、可靠性测试和运维资源'
        core_metric = '性能、成本、交付周期、稳定性和合规指标'

    def row_name(row: dict[str, Any]) -> str:
        return str(row.get('investedEnterprise') or row.get('targetEnterprise') or '').strip()

    def row_score(row: dict[str, Any]) -> int:
        try:
            return int(row.get('matchScore') or row.get('score') or 0)
        except (TypeError, ValueError):
            return 0

    def dedupe_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in items:
            name = row_name(item)
            if not name or name in seen:
                continue
            result.append(item)
            seen.add(name)
        return result

    def has_any(row: dict[str, Any], fields: tuple[str, ...]) -> bool:
        return any(_as_list(row.get(field)) for field in fields)

    rows_sorted = sorted(dedupe_rows(rows), key=row_score, reverse=True)
    core_rows = [row for row in rows_sorted if has_any(row, ('targetCapabilities',))]
    scene_rows = [row for row in rows_sorted if has_any(row, ('scenarios', 'customers', 'industries'))]
    supply_rows = [row for row in rows_sorted if has_any(row, ('suppliers', 'demands'))]
    software_rows = [
        row for row in rows_sorted
        if any(
            term in ' '.join(
                str(item or '')
                for field in ('targetCapabilities', 'scenarios', 'demands', 'industries', 'matchedTerms')
                for item in _as_list(row.get(field))
            )
            for term in ('软件', '数据', '平台', '算法', '智能', '运维', '监测', '系统', '模型')
        )
    ]

    def plan_score(items: list[dict[str, Any]]) -> dict[str, int]:
        unique_items = dedupe_rows(items)
        evidence = min(25, 10 + sum(8 if row.get('confidence') == 'high' else 4 for row in unique_items[:4]))
        complementarity = 8
        complementarity += 6 if any(row in core_rows for row in unique_items) else 0
        complementarity += 6 if any(row in scene_rows for row in unique_items) else 0
        complementarity += 5 if any(row in supply_rows for row in unique_items) else 0
        complementarity += 3 if any(row in software_rows for row in unique_items) else 0
        complementarity = min(25, complementarity)
        scene = min(20, 6 + sum(4 for row in unique_items[:4] if has_any(row, ('scenarios', 'customers'))))
        delivery = min(20, 6 + sum(3 for row in unique_items[:4] if has_any(row, ('suppliers', 'demands', 'targetCapabilities'))))
        risk = 10
        if not any(has_any(row, ('customers',)) for row in unique_items):
            risk -= 3
        if not any(has_any(row, ('suppliers', 'demands')) for row in unique_items):
            risk -= 2
        return {
            '证据强度': evidence,
            '互补度': complementarity,
            '场景清晰度': scene,
            '交付成熟度': delivery,
            '风险可控性': max(4, risk),
        }

    def plan_priority(total: int) -> str:
        if total >= 78:
            return '优先推进'
        if total >= 62:
            return '小范围验证'
        return '先补证据'

    def plan_enterprises(lead: dict[str, Any] | None, support: list[dict[str, Any]], extra_support: str = '') -> str:
        names = []
        if lead:
            names.append(f"牵头：{row_name(lead)}")
        support_names = _join([row_name(row) for row in support if row is not lead], 4)
        if support_names:
            names.append(f"支撑：{support_names}")
        if extra_support:
            names.append(f"待引入：{extra_support}")
        return '；'.join(names) or '待补充企业画像'

    def first_scene(items: list[dict[str, Any]]) -> str:
        return (
            _join([scene for row in items for scene in _as_list(row.get('scenarios'))], 2)
            or _join([industry for row in items for industry in _as_list(row.get('industries'))], 2)
            or keyword
        )

    raw_plans: list[dict[str, Any]] = []
    if rows_sorted:
        lead = core_rows[0] if core_rows else rows_sorted[0]
        items = dedupe_rows([lead] + scene_rows[:2] + supply_rows[:2] + software_rows[:1])
        raw_plans.append({
            'name': f'{keyword}核心能力验证方案',
            'lead': lead,
            'items': items,
            'extra_support': '',
            'logic': f'以{_join([cap for row in items for cap in _as_list(row.get("targetCapabilities"))], 5) or capabilities}形成最小可验证能力包',
            'scene': first_scene(items),
        })
    if scene_rows:
        lead = scene_rows[0]
        items = dedupe_rows([lead] + core_rows[:2] + supply_rows[:1] + software_rows[:1])
        raw_plans.append({
            'name': f'{keyword}场景客户共创方案',
            'lead': lead,
            'items': items,
            'extra_support': '' if customers else customer_targets,
            'logic': f'围绕{default_scene if (is_compute_cooling or is_notebook_cooling) else first_scene(items)}先定义客户指标，再组合被投企业能力做示范',
            'scene': default_scene if (is_compute_cooling or is_notebook_cooling) else first_scene(items),
        })
    if supply_rows or len(rows_sorted) >= 2:
        lead = supply_rows[0] if supply_rows else rows_sorted[1]
        items = dedupe_rows([lead] + core_rows[:2] + scene_rows[:1] + software_rows[:1])
        raw_plans.append({
            'name': f'{keyword}工程交付方案',
            'lead': lead,
            'items': items,
            'extra_support': '' if suppliers else delivery_support,
            'logic': '补齐供应链、测试验证、工程交付和持续运维，形成可复制的联合解决方案',
            'scene': default_scene if (is_compute_cooling or is_notebook_cooling) else first_scene(items),
        })
    elif rows_sorted:
        lead = rows_sorted[0]
        raw_plans.append({
            'name': f'{keyword}工程交付补足方案',
            'lead': lead,
            'items': [lead],
            'extra_support': delivery_support,
            'logic': '以已有被投企业能力为核心，外部补足供应链、测试验证和工程交付能力',
            'scene': default_scene if (is_compute_cooling or is_notebook_cooling) else first_scene([lead]),
        })

    plan_rows = [
        '| 方案 | 牵头/支撑企业 | 组合逻辑 | 首个验证场景 | 落地评分 | 推进建议 |',
        '|------|---------------|----------|--------------|----------|----------|',
    ]
    score_rows = [
        '| 方案 | 证据强度 | 互补度 | 场景清晰度 | 交付成熟度 | 风险可控性 | 总分 |',
        '|------|----------|--------|------------|------------|------------|------|',
    ]
    scored_plans: list[tuple[dict[str, Any], dict[str, int], int]] = []
    for plan in raw_plans[:3]:
        score = plan_score(plan['items'])
        total = sum(score.values())
        scored_plans.append((plan, score, total))
        plan_rows.append(
            f"| {plan['name']} | {plan_enterprises(plan['lead'], plan['items'], str(plan.get('extra_support') or ''))} | {plan['logic']} | "
            f"{plan['scene']} | {total}/100 | {plan_priority(total)} |"
        )
        score_rows.append(
            f"| {plan['name']} | {score['证据强度']} | {score['互补度']} | {score['场景清晰度']} | "
            f"{score['交付成熟度']} | {score['风险可控性']} | {total} |"
        )
    if len(plan_rows) == 2:
        plan_rows.append('| 待形成组合方案 | 待补充企业画像 | 当前图谱候选不足，需先补齐核心能力、场景和交付企业 | 待明确 | 40/100 | 先补证据 |')
        score_rows.append('| 待形成组合方案 | 10 | 8 | 8 | 8 | 6 | 40 |')

    gap_table = [
        '| 不足方向 | 补足方式 | 可能合作形式 |',
        '|----------|----------|--------------|',
    ]
    if not core_rows:
        gap_table.append('| 核心能力缺口 | 补入关键技术、产品或系统集成伙伴，明确性能边界 | 联合解决方案、联合产品线 |')
    if not scene_rows or not customers:
        gap_table.append(f'| 场景与标杆客户 | 引入{customer_targets}提出指标和验收口径 | 场景共创协议、首台套示范 |')
    if not supply_rows or not suppliers:
        gap_table.append(f'| 供应链与交付 | 补入{delivery_support} | EPC 联合体、属地化交付团队 |')
    gap_table.append('| 商业化验证 | 用小批量试点验证成本、稳定性、交付周期和复购可能性 | 示范项目、联合实验室、投后撮合联盟 |')

    top_plan = scored_plans[0][0] if scored_plans else None
    top_items = top_plan['items'] if top_plan else rows_sorted[:3]
    verify_table = [
        '| 核验对象 | 需核验问题 | 建议动作 | 输出物 |',
        '|----------|------------|----------|--------|',
        f"| 牵头企业能力 | 产品参数、成熟度、交付边界是否支撑“{default_scene}” | 访谈产品和交付负责人，收集规格书、案例、报价 | 能力边界表 |",
        '| 支撑企业协同 | 企业之间能力是否互补，接口、责任边界和商务分工是否清楚 | 组织 1 次联合方案会，形成模块分工 | 联合方案草案 |',
        f'| 客户/场景 | 是否存在明确需求方、预算方和验收指标 | 对接{customer_targets}，确认{core_metric} | 场景需求书 |',
        '| 供应链与认证 | 产能、检测认证、交付周期和关键供应风险是否可控 | 尽调供应链、认证周期、产线投入和外协资源 | 风险清单与补足计划 |',
    ]
    enterprise_checks = _join([row_name(row) for row in top_items], 5)
    if enterprise_checks:
        verify_table.append(f'| 候选企业 | {enterprise_checks} 的图谱证据仍需逐项核验 | 逐家核验客户、产品、产能和合作意愿 | 候选企业尽调记录 |')

    location_table = [
        '| 地域 | 适配判断 | 原因 | 更适合的落地方式 |',
        '|------|----------|------|------------------|',
        f'| 西安 | 技术验证和低成本示范 | 适合把“{keyword}”拆成可测试原型，先验证能力边界 | 联合实验室、园区示范、首套样机验证 |',
        '| 上海 | 客户牵引和方案定义 | 总部客户、产业资本、专业服务和生态伙伴集中，更容易定义高标准需求 | 客户共创、总部销售、行业标杆项目 |',
        '| 常州 | 制造转化和批量交付 | 长三角制造配套强，适合把验证方案转成工程产品 | 生产基地、供应链协同、项目交付中心 |',
    ]

    return (
        f'# {keyword}融链延链探索报告\n\n'
        '## 一、核心判断\n\n'
        f'- 当前围绕“{keyword}”召回 **{len(rows)}** 家被投企业，其中高置信 **{high}** 家、中置信 **{medium}** 家。\n'
        f'- **命题分化**：{domain_focus}\n'
        f'- 适合优先按“场景方 + 核心能力模块 + 供应链配套 + 工程交付”组装方案，而不是只做企业清单。已有能力基础包括 {capabilities}；可切入场景包括 {scenarios}。\n'
        f'- {f"图谱已有客户/交付线索包括 {customers}，可优先核验能否作为首个需求定义方。" if customers else "当前明确客户/交付线索不足，第一步应先锁定需求定义方和验收指标。"}'
        f'{f"供应链相关线索包括 {suppliers}，但仍需核验关键环节是否可控。" if suppliers else "供应链与工程交付标签不足，需要外部补入制造、检测、认证或运维资源。"}\n\n'
        '## 二、推荐组合方案\n\n'
        f"{chr(10).join(plan_rows)}\n\n"
        '## 三、落地性评分\n\n'
        f"{chr(10).join(score_rows)}\n\n"
        '评分口径：证据强度看图谱命中和置信等级；互补度看是否覆盖核心能力、场景、供应链和软件/运维；场景清晰度看是否有客户或应用场景；交付成熟度看是否有供应链、需求和产品能力线索；风险可控性看是否存在明显待核验缺口。\n\n'
        '## 四、缺口与补足路径\n\n'
        f"{chr(10).join(gap_table)}\n\n"
        '## 五、尽调核验清单\n\n'
        f"{chr(10).join(verify_table)}\n\n"
        '## 六、落地地域建议\n\n'
        f"{chr(10).join(location_table)}\n\n"
        '## 七、三个月推进动作\n\n'
        '- 第 1-2 周：确定一个首个验证场景，输出需求书、验收指标和候选企业分工。\n'
        '- 第 3-6 周：完成牵头企业与支撑企业访谈，核验产品参数、客户案例、产能、认证和合作意愿。\n'
        '- 第 7-10 周：形成联合方案报价、试点计划和风险补足清单，明确客户、园区或项目载体。\n'
        '- 第 11-12 周：推动小规模示范或联合实验室立项，沉淀可复制的联合解决方案。'
    )


def _format_fact_rows_for_llm(rows: list[dict[str, Any]], limit: int = 20) -> str:
    lines = ['排名 | 被投企业 | 产品/技术 | 证据 | 置信 | 分数']
    for index, row in enumerate(rows[:limit], start=1):
        enterprise = row.get('investedEnterprise') or row.get('targetEnterprise') or '-'
        product = _join(row.get('targetCapabilities') or row.get('products'), 4) or '-'
        evidence = _join(row.get('evidence'), 4) or _join(row.get('customers'), 3) or _join(row.get('scenarios'), 3) or '-'
        lines.append(
            f"{index} | {enterprise} | {product} | {evidence} | "
            f"{row.get('confidence') or '-'} | {row.get('score') or row.get('matchScore') or '-'}"
        )
    return '\n'.join(lines)


def _format_external_rows_for_llm(rows: list[dict[str, Any]], limit: int = 24) -> str:
    lines = ['排名 | 被投企业 | 合作模式 | 产品/能力 | 证据 | 匹配词 | 置信 | 分数']
    for index, row in enumerate(rows[:limit], start=1):
        enterprise = row.get('investedEnterprise') or row.get('targetEnterprise') or '-'
        mode = row.get('opportunityTypeLabel') or COOPERATION_MODE_LABELS.get(str(row.get('cooperationMode') or ''), '') or row.get('matchedDimension') or '-'
        capability = _join(row.get('targetCapabilities') or row.get('products') or row.get('capabilities'), 4) or '-'
        evidence = _join(row.get('evidence'), 3) or _join(row.get('customers'), 2) or _join(row.get('scenarios'), 2) or '-'
        terms = _join(row.get('matchedTerms'), 6) or '-'
        lines.append(
            f"{index} | {enterprise} | {mode} | {capability} | {evidence} | {terms} | "
            f"{row.get('confidence') or '-'} | {row.get('score') or row.get('matchScore') or '-'}"
        )
    return '\n'.join(lines)


def _format_technology_rows_for_llm(rows: list[dict[str, Any]], limit: int = 24) -> str:
    lines = ['排名 | 被投企业 | 环节/方向 | 产品/能力 | 场景/需求 | 匹配词 | 置信']
    for index, row in enumerate(rows[:limit], start=1):
        enterprise = row.get('investedEnterprise') or row.get('targetEnterprise') or '-'
        stage = row.get('targetStage') or row.get('subTrack') or '-'
        capability = _join(row.get('targetCapabilities') or row.get('products') or row.get('capabilities'), 4) or '-'
        scene = _join(row.get('scenarios') or row.get('demands') or row.get('industries'), 3) or '-'
        terms = _join(row.get('matchedTerms'), 6) or '-'
        lines.append(f"{index} | {enterprise} | {stage} | {capability} | {scene} | {terms} | {row.get('confidence') or '-'}")
    return '\n'.join(lines)


def _company_relation_lines(row: dict[str, Any], direction: str, limit: int = 12) -> list[str]:
    relation_key = 'upstreamRelations' if direction == 'upstream' else 'downstreamRelations'
    stage_key = 'upstreamStages' if direction == 'upstream' else 'downstreamStages'
    enterprise_key = 'upstreamEnterprises' if direction == 'upstream' else 'downstreamEnterprises'
    label = '上游' if direction == 'upstream' else '下游'
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for item in _as_list(row.get(relation_key)):
        if not isinstance(item, dict):
            continue
        stage = str(item.get('stage') or '').strip()
        enterprise = str(item.get('enterprise') or '').strip()
        if not stage or not enterprise or (stage, enterprise) in seen:
            continue
        lines.append(f'- {label}环节 **{stage}**：{enterprise}')
        seen.add((stage, enterprise))
        if len(lines) >= limit:
            return lines
    fallback_stage = '、'.join(str(item) for item in _as_list(row.get(stage_key)) if item) or '未标注环节'
    for enterprise in _as_list(row.get(enterprise_key)):
        enterprise_name = str(enterprise or '').strip()
        if not enterprise_name or (fallback_stage, enterprise_name) in seen:
            continue
        lines.append(f'- {label}环节 **{fallback_stage}**：{enterprise_name}')
        seen.add((fallback_stage, enterprise_name))
        if len(lines) >= limit:
            break
    return lines


def build_rule_answer(mode: str, rows: list[dict[str, Any]], query: dict[str, Any] | None = None) -> str:
    query = query or {}
    if mode == 'overview':
        sub_tracks = {row.get('subTrack') for row in rows if row.get('subTrack')}
        empty_stages = [row.get('stage') for row in rows if row.get('stage') and not row.get('enterpriseCount')]
        return (
            '## 一、核心发现\n'
            f'- 当前图谱覆盖 **{len(sub_tracks)}** 条产业链/子赛道，包含 **{len(rows)}** 个环节记录。\n'
            f'- 其中 **{len(empty_stages)}** 个环节暂未挂接企业，是后续补图和招商/投后服务的重点缺口。\n\n'
            '## 二、产业链布局判断\n'
            '- 现阶段适合先用图谱做结构化盘点，再由 DeepSeek 对高密度环节、空白环节和合作机会进行解释。\n\n'
            '## 三、分析\n'
            '- 优先核验企业数量较高的环节是否已形成可撮合的上下游关系。\n'
            '- 对暂未挂接企业的环节补充企业画像、产品能力和客户标签。'
        )
    if mode == 'company-updown':
        if not rows:
            return '当前图谱未发现匹配企业。'
        row = rows[0]
        relation_lines = _company_relation_lines(row, 'upstream') + _company_relation_lines(row, 'downstream')
        relation_text = '\n'.join(relation_lines) if relation_lines else '- 当前图谱未返回相邻环节企业明细。'
        return (
            '## 一、企业产业链位置\n'
            f"- **{row.get('enterprise')}** 位于 **{', '.join(row.get('stages') or []) or '未标注环节'}**。\n\n"
            '## 二、上下游线索\n'
            f"- 上游相关企业 **{len(row.get('upstreamEnterprises') or [])}** 家，下游相关企业 **{len(row.get('downstreamEnterprises') or [])}** 家。\n\n"
            '## 三、关联企业与环节\n'
            f'{relation_text}\n\n'
            '## 四、分析\n'
            '- 先核验相邻环节企业的产品规格、客户重合度和商务意愿，再进入撮合。'
        )
    if mode == 'opportunities':
        keyword = str((rows[0].get('queryObject') if rows else '') or '').strip()
        if rows and rows[0].get('opportunityType') == 'graph_fact_discovery':
            return _build_graph_fact_discovery_report(rows, query)
        if rows and rows[0].get('opportunityType') == 'external_company':
            return _build_external_company_report(rows, query)
        if rows and rows[0].get('opportunityType') == 'technology_scope':
            return _build_technology_scope_report(rows, query)
        if rows and rows[0].get('opportunityType') == 'industry_direction':
            return _build_industry_direction_report(rows, query)
        high = sum(1 for row in rows if row.get('confidence') == 'high')
        medium = sum(1 for row in rows if row.get('confidence') == 'medium')
        return (
            '## 一、核心发现\n'
            f'- 当前查询发现 **{len(rows)}** 条潜在合作机会，其中高置信 **{high}** 条，中置信 **{medium}** 条。\n\n'
            '## 二、合作机会判断\n'
            '- 这些机会来自上下游环节相邻关系或共同场景关系，仍需结合产品、客户和商务意愿核验。\n\n'
            '## 三、分析\n'
            '- 选择高置信机会进入投后访谈，形成企业-场景-客户三方撮合清单。'
        )
    return f'当前查询返回 {len(rows)} 条结果。'


def analyze_with_llm(mode: str, rows: list[dict[str, Any]], query: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    client = DeepSeekClient()
    keyword = str(query.get('keyword') or query.get('enterpriseName') or '').strip()
    opportunity_mode = str(query.get('opportunityMode') or query.get('scopeType') or '').strip()
    is_target_company_report = mode == 'opportunities' and opportunity_mode == 'external_company' and bool(keyword)
    is_graph_fact_report = mode == 'opportunities' and opportunity_mode == 'graph_fact_discovery'
    is_technology_scope_report = mode == 'opportunities' and opportunity_mode == 'technology_scope' and bool(keyword)
    is_industry_direction_report = mode == 'opportunities' and opportunity_mode == 'industry_direction' and bool(keyword)
    if not client.enabled:
        if is_graph_fact_report:
            answer = _build_graph_fact_discovery_report(rows, query)
        elif is_technology_scope_report:
            answer = _build_technology_scope_report(rows, query)
        elif is_industry_direction_report:
            answer = _build_industry_direction_report(rows, query)
        else:
            answer = _build_external_company_report(rows, query) if is_target_company_report else build_rule_answer(mode, rows, query)
        return _strip_appended_opportunity_cards(answer), {'enabled': False, 'provider': 'deepseek'}

    if is_graph_fact_report:
        system_prompt = (
            '你是星擎智服的产业链与投后服务分析师。你正在撰写“Neo4j 被投企业图谱事实发现报告”。'
            '你只能使用输入的检索计划和 Neo4j 证据，不得新增图谱中不存在的企业。'
            '重点判断企业产品/技术是否已经在用户指定场景中应用、供货、部署、服务或具备明确成熟度证据；证据不足必须写需核验。'
            '不要只保留有具体客户名称的企业；若企业有医疗器械/上市/注册/商业化/科室应用/医院合作等证据，也应列入清单并标注证据等级。'
        )
        user_prompt = (
            f'用户问题：{query.get("question") or keyword}\n'
            f'检索计划：{_compact(query.get("factDiscoveryPlan"), 5000)}\n'
            f'Neo4j 候选企业证据（已压缩，按排序输出）：\n{_format_fact_rows_for_llm(rows, 20)}\n\n'
            '请输出 Markdown 报告，结构必须为：\n'
            '## 一、核心发现\n'
            '## 二、已应用/落地企业清单\n'
            '| 排名 | 被投企业 | 产品/技术 | 已应用/落地证据 | 证据等级 |\n|-----|---------|-----------|----------------|---------|\n'
            '清单至少覆盖输入候选中的前15家，除非证据明确与问题无关；不要把所有“无具体医院名称”的候选都删除。\n'
            '## 三、分层判断\n'
            '按高置信、成熟产品但需核验医院客户、临床/研发阶段三类说明。\n'
            '## 四、数据限制与补图建议\n'
            '报告必须优先回答用户问题，不要写外部公司合作机会报告。'
        )
    elif is_target_company_report:
        system_prompt = (
            '你是星擎智服的产业链与投后服务分析师。你正在撰写“目标公司 × 被投企业潜在合作机会分析”。'
            '你只能使用输入的目标公司画像、分组机会和 Neo4j RAG 证据，不能编造不存在的企业、客户、合作关系或落地案例。'
            '合作判断必须围绕合作维度、匹配字段、匹配词和图谱证据展开；证据不足时明确写“需进一步核验”。'
            '目标公司可能是外部产业公司，也可能是 Neo4j 库内已有被投企业，不要固定写成“外部企业”。'
        )
        user_prompt = (
            f'目标公司：{keyword}\n'
            f'目标公司画像与查询条件：{_compact(query, 5000)}\n'
            f'Neo4j RAG 证据（已压缩，按排序输出）：\n{_format_external_rows_for_llm(rows, 24)}\n\n'
            '请输出完整 Markdown 报告，不要输出 JSON，结构必须为：\n'
            f'目标公司：**{keyword}**\n'
            '## 一、目标公司业务画像\n'
            '用 1-2 个短句压缩描述业务位置、核心产品/技术、需求与应用场景，不要输出画像表格。\n'
            '## 二、合作机会总览\n'
            '| 合作方向 | 目标公司角色 | 候选企业数 | 主要切入点 |\n|---------|-------------|-----------|-----------|\n'
            '## 三、分方向合作机会\n'
            '按中文方向归纳：目标公司作为客户、目标公司作为供应商、联合研发、客户协同、场景落地、厂务与运营配套；只写有候选的方向，每个方向最多列 3 家，不要输出括号中的英文模式码。\n'
            '## 四、重点推荐\n'
            '| 优先级 | 被投企业 | 合作模式 | 推荐理由 | 证据 |\n|-------|---------|---------|---------|------|\n'
            '## 五、数据限制与需核验事项\n'
            '重点推荐最多 8 家。推荐理由必须引用匹配词或 evidence，不能只说行业相关。'
            '报告总字数控制在 1800 字以内，要精炼，不要逐条复述全部原始字段；明显只由泛词命中的工业/芯片/航天企业应降级或写入需核验。'
        )
    elif is_technology_scope_report:
        system_prompt = (
            '你是星擎智服的产业链与投后服务分析师。你正在撰写“技术领域相关被投企业产业链分析报告”。'
            '你只能基于输入的 Neo4j RAG 证据回答，不得新增不存在的企业、产品、客户或合作案例。'
            '报告目标是回答“某技术/领域有哪些被投企业、分别在什么产业链环节发挥作用”。'
        )
        user_prompt = (
            f'目标技术领域：{keyword}\n'
            f'查询条件：{_compact(query, 1200)}\n'
            f'Neo4j RAG 证据（已压缩，按排序输出）：\n{_format_technology_rows_for_llm(rows, 24)}\n\n'
            '请输出 Markdown 报告，结构参考“反恐产业链分析报告”，但不要输出 emoji，不要写查询代码。必须包含：\n'
            f'# {keyword}产业链分析报告\n'
            '## 一、核心发现\n'
            '说明召回企业数量、核心能力维度、主要环节。\n'
            '## 二、相关被投企业清单\n'
            '| 序号 | 被投企业 | 主要环节/方向 | 可发挥作用 | 图谱依据 |\n|:---:|----------|--------------|------------|----------|\n'
            '## 三、产业链环节分布\n'
            '按环节归纳哪些企业发挥什么作用。\n'
            '## 四、场景-企业匹配矩阵\n'
            '| 场景/需求 | 匹配企业 | 作用说明 |\n|-----------|----------|----------|\n'
            '## 五、总结\n'
            '总结必须聚焦三点：1）我们的被投企业在该技术领域的总体优势；2）主要劣势或短板；3）按细分领域/应用场景归纳哪些企业更强、哪些方向仍需补强。'
            '不要把第五部分写成“数据限制与补图建议”。报告总字数控制在 1800 字以内；企业清单优先覆盖输入候选，不要只写 3-5 家；证据不足要写需核验。'
        )
    elif is_industry_direction_report:
        system_prompt = (
            '你是星擎智服的产业链与投后服务分析师。你正在撰写“融链延链探索报告”。'
            '你只能基于输入的 Neo4j RAG 证据回答，不得新增图谱中不存在的被投企业、客户或既有合作案例。'
            '报告目标不是简单列相关企业，而是围绕技术命题设计可推进的组合方案、新公司或联合解决方案。'
            '必须输出方案名称、牵头/支撑企业、落地评分、缺口补足和尽调核验动作，让投后团队知道先推哪一个、怎么推、核验什么。'
            '如果技术命题包含“散热”，必须先区分应用场景：AI算力中心/数据中心散热应聚焦液冷、机房工程、PUE、单柜功率密度、运维监控和IDC/云厂商客户；电竞笔记本/消费电子散热应聚焦导热材料、热管/均热板/石墨片/风扇模组、轻薄化、噪声和ODM/OEM客户。'
            '不要输出“报告说明”“数据来源说明”或类似附录；不要在报告正文后追加候选机会列表、置信等级列表或单条机会卡片文案。'
        )
        user_prompt = (
            f'技术命题：{keyword}\n'
            f'查询条件：{_compact(query, 1600)}\n'
            f'Neo4j RAG 证据（已压缩，按排序输出）：\n{_format_technology_rows_for_llm(rows, 24)}\n\n'
            '请输出 Markdown 报告，不要输出 JSON，不要写查询代码。必须包含：\n'
            f'# {keyword}融链延链探索报告\n'
            '## 一、核心判断\n'
            '判断这个技术命题是否适合用被投企业组建组合方案/项目公司/联合解决方案，并点明首要推进前提。\n'
            '## 二、推荐组合方案\n'
            '| 方案 | 牵头/支撑企业 | 组合逻辑 | 首个验证场景 | 落地评分 | 推进建议 |\n|------|---------------|----------|--------------|----------|----------|\n'
            '至少输出 2 个方案，优先围绕“场景方 + 核心能力模块 + 供应链配套 + 工程交付”组织；不要只列企业。落地评分用 0-100 分，推进建议只能是“优先推进/小范围验证/先补证据”之一。\n'
            '## 三、落地性评分\n'
            '| 方案 | 证据强度 | 互补度 | 场景清晰度 | 交付成熟度 | 风险可控性 | 总分 |\n|------|----------|--------|------------|------------|------------|------|\n'
            '分项评分总和必须等于总分，评分依据必须来自输入证据，证据不足要降分。\n'
            '## 四、缺口与补足路径\n'
            '| 不足方向 | 补足方式 | 可能合作形式 |\n|----------|----------|--------------|\n'
            '不足要具体到核心部件、场景客户、系统集成、工程交付、认证、供应链、产能等，不要写泛泛而谈的短板。\n'
            '## 五、尽调核验清单\n'
            '| 核验对象 | 需核验问题 | 建议动作 | 输出物 |\n|----------|------------|----------|--------|\n'
            '核验清单必须覆盖牵头企业能力、支撑企业协同、客户/场景、供应链与认证、商务合作意愿。\n'
            '## 六、落地地域建议\n'
            '| 地域 | 适配判断 | 原因 | 更适合的落地方式 |\n|------|----------|------|------------------|\n'
            '必须比较西安、上海、常州：西安偏技术验证和示范，上海偏客户牵引和方案定义，常州偏制造转化和批量交付；要结合技术命题本身和输入证据解释为什么，不要绑定某个具体方向的指标。\n'
            '## 七、三个月推进动作\n'
            '按第1-2周、第3-6周、第7-10周、第11-12周写具体动作。报告总字数控制在 2200 字以内；证据不足要在对应判断中写需核验。'
            '报告必须在第七部分结束，不要追加“报告说明”或任何候选企业明细列表。'
        )
    else:
        system_prompt = (
            '你是星擎智服的产业链与投后服务分析师。你的输出不是数据陈列，而是面向决策层的产业链分析报告。'
            '你只能基于输入的 Neo4j 查询结果回答，不能编造不存在的企业关系。若证据不足，要明确说明当前图谱未发现或建议补充核验。'
            '报告要结构化：先给核心发现，再解释企业/环节/场景匹配，最后给出分析判断。'
        )
        user_prompt = (
            f'分析模式：{mode}\n'
            f'查询条件：{_compact(query, 1000)}\n'
            f'Neo4j 查询结果：{_compact(rows)}\n\n'
            '请优先回答查询条件中的 question。请用 Markdown 输出，结构必须包含：\n'
            '## 一、核心发现\n'
            '## 二、重点企业/环节判断\n'
            '## 三、合作机会或能力缺口\n'
            '## 四、分析\n'
            '## 五、数据限制\n'
            '若是企业上下游模式，必须列出哪些公司位于哪个上游/下游环节，并说明其与目标企业的关联方向。\n'
            '若是合作机会模式，请归纳机会类型、图谱依据、置信等级和分析判断。'
        )
    try:
        result = client.chat(system_prompt, user_prompt, temperature=0.2)
        return _strip_appended_opportunity_cards(result.get('content') or build_rule_answer(mode, rows, query)), {
            'enabled': True,
            'provider': result.get('provider'),
            'model': result.get('model'),
        }
    except Exception as exc:
        if is_graph_fact_report:
            answer = _build_graph_fact_discovery_report(rows, query)
        elif is_technology_scope_report:
            answer = _build_technology_scope_report(rows, query)
        elif is_industry_direction_report:
            answer = _build_industry_direction_report(rows, query)
        else:
            answer = _build_external_company_report(rows, query) if is_target_company_report else build_rule_answer(mode, rows, query)
        return _strip_appended_opportunity_cards(answer), {
            'enabled': False,
            'provider': 'deepseek',
            'error': str(exc),
        }
