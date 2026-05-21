from __future__ import annotations

from typing import Any

from services.llm_client import DeepSeekClient


def _compact(value: Any, limit: int = 5000) -> str:
    text = str(value)
    return text[:limit]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value in (None, '') else [value])


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


def build_rule_answer(mode: str, rows: list[dict[str, Any]]) -> str:
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
    if not client.enabled:
        return build_rule_answer(mode, rows), {'enabled': False, 'provider': 'deepseek'}

    system_prompt = (
        '你是星擎智服的产业链与投后服务分析师。你的输出不是数据陈列，而是面向决策层的产业链分析报告。'
        '你只能基于输入的 Neo4j 查询结果回答，不能编造不存在的企业关系。若证据不足，要明确说明当前图谱未发现或建议补充核验。'
        '报告要像“反恐产业链分析报告”那样结构化：先给核心发现，再解释企业/环节/场景匹配，最后给出分析判断。'
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
        return result.get('content') or build_rule_answer(mode, rows), {
            'enabled': True,
            'provider': result.get('provider'),
            'model': result.get('model'),
        }
    except Exception as exc:
        return build_rule_answer(mode, rows), {
            'enabled': False,
            'provider': 'deepseek',
            'error': str(exc),
        }
