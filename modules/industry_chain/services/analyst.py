from __future__ import annotations

from typing import Any

from services.llm_client import DeepSeekClient

POWER_GRID_TERMS = ('国网', '国家电网', '电力电网', '供电', '电网')


def _compact(value: Any, limit: int = 5000) -> str:
    text = str(value)
    return text[:limit]


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
    keyword = str(query.get('keyword') or profile.get('companyName') or (rows[0].get('queryObject') if rows else '') or '外部企业').strip()
    high = sum(1 for row in rows if row.get('confidence') == 'high')
    medium = sum(1 for row in rows if row.get('confidence') == 'medium')
    profile_table = [
        '| 维度 | 内容 |',
        '|------|------|',
        f"| 核心业务 | {_join(profile.get('coreProducts'), 6) or '规则画像未明确'} |",
        f"| 产业链位置 | {profile.get('chainPosition') or '规则画像未明确'} |",
        f"| 关键能力/产品 | {_join((profile.get('coreTechnologies') or []) + (profile.get('coreProducts') or []), 8) or '规则画像未明确'} |",
        f"| 上游需求 | {_join(profile.get('upstreamNeeds'), 8) or '规则画像未明确'} |",
        f"| 下游应用/客户 | {_join((profile.get('downstreamApplications') or []) + (profile.get('targetCustomers') or []), 8) or '规则画像未明确'} |",
    ]
    overview_table = [
        '| 合作方向 | 外部企业角色 | 候选企业数 | 主要切入点 |',
        '|---------|-------------|-----------|-----------|',
    ]
    for group in grouped:
        overview_table.append(
            f"| {group.get('description') or group.get('mode') or '-'} | {group.get('externalRole') or '-'} | "
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
            fields = _join(item.get('matchedFields'), 4)
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
        mode = row.get('opportunityTypeLabel') or row.get('cooperationMode') or '外部公司合作'
        terms = _join(row.get('matchedTerms'), 5)
        evidence = _join(row.get('evidence'), 2)
        recommendations.append(f"| {index} | **{enterprise}** | {mode} | 命中{terms or '画像相关词'}，置信度{row.get('confidence') or '-'} | {evidence or '需核验'} |")
    if len(recommendations) == 2:
        recommendations.append('| - | - | - | 当前图谱未返回可排序机会 | - |')
    return (
        f'# {keyword} × 被投企业 潜在合作机会分析\n\n'
        '## 一、外部企业业务画像\n\n'
        f"{chr(10).join(profile_table)}\n\n"
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
        mode = row.get('opportunityTypeLabel') or row.get('cooperationMode') or row.get('matchedDimension') or '-'
        capability = _join(row.get('targetCapabilities') or row.get('products') or row.get('capabilities'), 4) or '-'
        evidence = _join(row.get('evidence'), 3) or _join(row.get('customers'), 2) or _join(row.get('scenarios'), 2) or '-'
        terms = _join(row.get('matchedTerms'), 6) or '-'
        lines.append(
            f"{index} | {enterprise} | {mode} | {capability} | {evidence} | {terms} | "
            f"{row.get('confidence') or '-'} | {row.get('score') or row.get('matchScore') or '-'}"
        )
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
    if not client.enabled:
        if is_graph_fact_report:
            answer = _build_graph_fact_discovery_report(rows, query)
        else:
            answer = _build_external_company_report(rows, query) if is_target_company_report else build_rule_answer(mode, rows, query)
        return answer, {'enabled': False, 'provider': 'deepseek'}

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
            '你是星擎智服的产业链与投后服务分析师。你正在撰写“外部企业 × 被投企业潜在合作机会分析”。'
            '你只能使用输入的外部企业规则画像、分组机会和 Neo4j RAG 证据，不能编造不存在的企业、客户、合作关系或落地案例。'
            '合作判断必须围绕合作维度、匹配字段、匹配词和图谱证据展开；证据不足时明确写“需进一步核验”。'
        )
        user_prompt = (
            f'外部企业：{keyword}\n'
            f'外部企业画像与查询条件：{_compact(query, 5000)}\n'
            f'Neo4j RAG 证据（已压缩，按排序输出）：\n{_format_external_rows_for_llm(rows, 24)}\n\n'
            '请输出完整 Markdown 报告，不要输出 JSON，结构必须为：\n'
            f'# {keyword} × 被投企业 潜在合作机会分析\n'
            '## 一、外部企业业务画像\n'
            '| 维度 | 内容 |\n|------|------|\n'
            '## 二、合作机会总览\n'
            '| 合作方向 | 外部企业角色 | 候选企业数 | 主要切入点 |\n|---------|-------------|-----------|-----------|\n'
            '## 三、分方向合作机会\n'
            '按 supply_to_external、external_supply_to_portfolio、joint_r_and_d、shared_customer、scenario_landing、factory_or_operation_support 归纳；只写有候选的方向，每个方向最多列 3 家。\n'
            '## 四、重点推荐\n'
            '| 优先级 | 被投企业 | 合作模式 | 推荐理由 | 证据 |\n|-------|---------|---------|---------|------|\n'
            '## 五、数据限制与需核验事项\n'
            '重点推荐最多 8 家。推荐理由必须引用匹配词或 evidence，不能只说行业相关。'
            '报告总字数控制在 1800 字以内，要精炼，不要逐条复述全部原始字段；明显只由泛词命中的工业/芯片/航天企业应降级或写入需核验。'
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
        return result.get('content') or build_rule_answer(mode, rows, query), {
            'enabled': True,
            'provider': result.get('provider'),
            'model': result.get('model'),
        }
    except Exception as exc:
        if is_graph_fact_report:
            answer = _build_graph_fact_discovery_report(rows, query)
        else:
            answer = _build_external_company_report(rows, query) if is_target_company_report else build_rule_answer(mode, rows, query)
        return answer, {
            'enabled': False,
            'provider': 'deepseek',
            'error': str(exc),
        }
