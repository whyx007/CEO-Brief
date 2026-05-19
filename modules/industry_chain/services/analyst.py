from __future__ import annotations

from typing import Any

from services.llm_client import DeepSeekClient


def _compact(value: Any, limit: int = 5000) -> str:
    text = str(value)
    return text[:limit]


def build_rule_answer(mode: str, rows: list[dict[str, Any]]) -> str:
    if mode == 'overview':
        sub_tracks = {row.get('subTrack') for row in rows if row.get('subTrack')}
        empty_stages = [row.get('stage') for row in rows if row.get('stage') and not row.get('enterpriseCount')]
        return f'当前图谱覆盖 {len(sub_tracks)} 条产业链/子赛道，包含 {len(rows)} 个环节记录；其中 {len(empty_stages)} 个环节暂未挂接企业。'
    if mode == 'company-updown':
        if not rows:
            return '当前图谱未发现匹配企业。'
        row = rows[0]
        return (
            f"{row.get('enterprise')} 位于 {', '.join(row.get('stages') or []) or '未标注环节'}；"
            f"上游相关企业 {len(row.get('upstreamEnterprises') or [])} 家，"
            f"下游相关企业 {len(row.get('downstreamEnterprises') or [])} 家。"
        )
    if mode == 'opportunities':
        high = sum(1 for row in rows if row.get('confidence') == 'high')
        medium = sum(1 for row in rows if row.get('confidence') == 'medium')
        return f'当前查询发现 {len(rows)} 条潜在合作机会，其中高置信 {high} 条，中置信 {medium} 条。'
    return f'当前查询返回 {len(rows)} 条结果。'


def analyze_with_llm(mode: str, rows: list[dict[str, Any]], query: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    client = DeepSeekClient()
    if not client.enabled:
        return build_rule_answer(mode, rows), {'enabled': False, 'provider': 'deepseek'}

    system_prompt = (
        '你是星擎智服的产业链与投后服务分析助手。只能基于输入的 Neo4j 查询结果回答，'
        '不能编造不存在的企业关系。若证据不足，要明确说明当前图谱未发现或建议补充核验。'
        '输出面向投后服务团队，强调图谱依据和可执行动作。'
    )
    user_prompt = (
        f'分析模式：{mode}\n'
        f'查询条件：{_compact(query, 1000)}\n'
        f'Neo4j 查询结果：{_compact(rows)}\n\n'
        '请用中文输出简洁分析。若是合作机会模式，请归纳机会类型、图谱依据、置信等级和建议动作。'
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
