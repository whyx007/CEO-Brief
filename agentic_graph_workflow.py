"""
================================================================================
 Agentic Graph Workflow — 产业图谱智能分析引擎
 架构：Schema先验 → 查询分解 → 分步执行 → 业务推理 → 结构化报告
 依赖：pip install neo4j openai
================================================================================
"""

import json
import os
from typing import Any

from neo4j import GraphDatabase
from openai import OpenAI

# ═══════════════════════════════════════════════════════════════════════
#  配置区（按需修改）
# ═══════════════════════════════════════════════════════════════════════

NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j"

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-xxxxxxxxxxxxxxxx")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"  # 或 deepseek-reasoner


# ═══════════════════════════════════════════════════════════════════════
#  第1层：Schema 探测器 — 自动探测图谱结构
# ═══════════════════════════════════════════════════════════════════════

class Neo4jSchemaExplorer:
    """连接 Neo4j 并爬取完整的 Schema 元数据。"""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def probe_schema(self) -> dict:
        """返回结构化 schema 字典。"""
        labels = self._run("CALL db.labels()")
        rel_types = self._run("CALL db.relationshipTypes()")
        prop_keys = self._run("CALL db.propertyKeys()")

        # 精细：每个 label 有哪些 property key
        label_props = {}
        for label in [r["label"] for r in labels]:
            rows = self._run(
                f"MATCH (n:`{label}`) "
                f"RETURN keys(n) AS props LIMIT 3"
            )
            all_keys = set()
            for row in rows:
                all_keys.update(row["props"])
            label_props[label] = sorted(all_keys)

        # 精细：每个 relationship type 有哪些 property key
        rel_props = {}
        for rel in [r["relationshipType"] for r in rel_types]:
            rows = self._run(
                f"MATCH ()-[r:`{rel}`]->() "
                f"RETURN keys(r) AS props LIMIT 3"
            )
            all_keys = set()
            for row in rows:
                all_keys.update(row["props"])
            rel_props[rel] = sorted(all_keys)

        # 抽样：5条关系样例，帮助 LLM 理解数据形态
        sample_rels = []
        for rel in [r["relationshipType"] for r in rel_types][:5]:
            rows = self._run(
                f"MATCH (a)-[r:`{rel}`]->(b) "
                f"RETURN a.name AS src, type(r) AS rel, b.name AS dst "
                f"LIMIT 2"
            )
            for row in rows:
                sample_rels.append({
                    "src": row.get("src", "?"),
                    "rel": row["rel"],
                    "dst": row.get("dst", "?")
                })

        return {
            "labels": [r["label"] for r in labels],
            "relationship_types": [r["relationshipType"] for r in rel_types],
            "property_keys": [r["propertyKey"] for r in prop_keys],
            "label_properties": label_props,
            "relationship_properties": rel_props,
            "sample_relationships": sample_rels,
        }

    def count_nodes(self, label: str) -> int:
        rows = self._run(f"MATCH (n:`{label}`) RETURN count(n) AS cnt")
        return rows[0]["cnt"] if rows else 0

    def _run(self, query: str):
        with self.driver.session() as session:
            return list(session.run(query))


# ═══════════════════════════════════════════════════════════════════════
#  第2层：查询分解器 + 执行引擎
# ═══════════════════════════════════════════════════════════════════════

class QueryDecomposer:
    """把用户问题拆成一个多步查询计划。"""

    CYPHER_SYSTEM_PROMPT = """你是一个产业图谱分析师。以下是 Neo4j 知识图谱的完整结构：

## 节点类型 (Node Labels)
{labels}

## 关系类型 (Relationship Types)
{rel_types}

## 各节点的属性字段
{label_props}

## 各关系的属性字段
{rel_props}

## 数据样例（三元组）
{samples}

## 节点数量统计
{counts}

## 任务
请把用户的问题拆成 2~5 个有序的子查询步骤。每个步骤包含：
1. step: 步骤序号
2. purpose: 查询目的（一句话）
3. cypher: 可执行的 Cypher 语句（用参数化查询，中文要转义好）
4. depends_on: 依赖的上一步骤序号列表（[] 表示无依赖）

只输出 JSON 数组，不要多余文字。
"""

    def __init__(self, client: OpenAI, schema: dict, node_counts: dict[str, int] | None = None):
        self.client = client
        self.schema = schema
        self.node_counts = node_counts or {}

    def decompose(self, question: str) -> list[dict]:
        prompt = self.CYPHER_SYSTEM_PROMPT.format(
            labels=json.dumps(self.schema["labels"], ensure_ascii=False, indent=2),
            rel_types=json.dumps(self.schema["relationship_types"], ensure_ascii=False, indent=2),
            label_props=json.dumps(self.schema["label_properties"], ensure_ascii=False, indent=2),
            rel_props=json.dumps(self.schema["relationship_properties"], ensure_ascii=False, indent=2),
            samples=json.dumps(self.schema["sample_relationships"], ensure_ascii=False, indent=2),
            counts=json.dumps(self.node_counts, ensure_ascii=False, indent=2),
        )
        resp = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"用户问题：{question}"},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        # 兼容两种格式：直接是数组，或 {"steps": [...]}
        if isinstance(data, dict) and "steps" in data:
            return data["steps"]
        if isinstance(data, list):
            return data
        raise ValueError(f"Unexpected LLM response format: {raw[:200]}")


class CypherExecutor:
    """执行 Cypher 并返回结构化结果。"""

    def __init__(self, driver):
        self.driver = driver

    def run(self, cypher: str) -> list[dict]:
        with self.driver.session() as session:
            result = session.run(cypher)
            return [dict(r) for r in result]

    def run_steps(self, steps: list[dict]) -> dict[int, Any]:
        """按依赖顺序执行步骤，返回 {step_num: result}。"""
        results = {}
        executed = set()

        while len(executed) < len(steps):
            for step in steps:
                sn = step["step"]
                if sn in executed:
                    continue
                deps = step.get("depends_on", [])
                if all(d in executed for d in deps):
                    print(f"  ▶ 步骤 {sn}: {step.get('purpose', '')}")
                    raw = self.run(step["cypher"])
                    results[sn] = raw
                    executed.add(sn)
                    print(f"    → 返回 {len(raw)} 条记录")
        return results


# ═══════════════════════════════════════════════════════════════════════
#  第3层：业务推理引擎
# ═══════════════════════════════════════════════════════════════════════

REASONER_SYSTEM_PROMPT = """你是一位资深产业咨询顾问。你收到了一份企业数据（包含技术能力、所处产业链环节、已有客户、服务行业等信息）。

请针对**每一家企业**，结合其自身能力和**外部公司**的业务场景、所在环节，推断一个具体的『可能的合作方向』。

推理原则：
1. 技术能力匹配：如果企业A有某项技术能力（HAS_CAPABILITY/关键能力），而外部企业所在的环节需要该技术 → 可以合作
2. 上下游协同：如果两家企业在同一产业链的相邻环节 → 上下游供货/采购合作
3. 行业跨界：如果企业服务于多个行业，外部公司在某个行业中但缺乏该能力 → 能力输出
4. 客户背书：如果企业已有行业头部客户 → 说明其能力经过验证，可信度高

输出格式（Markdown表格）：
| 企业名称 | 所处环节 | 技术能力 | 已有客户/行业 | 可能的合作方向 |
|---------|---------|---------|-------------|--------------|
"""


class BusinessReasoner:
    """基于图谱查询结果进行业务推理。"""

    def __init__(self, client: OpenAI):
        self.client = client

    def reason(self, context: str, target_company: str) -> str:
        """context 是前面所有步骤的查询结果拼接。"""
        resp = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": REASONER_SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"外部公司名称：{target_company}\n\n"
                    f"以下是查询到的图谱数据：\n{context}\n\n"
                    f"请根据以上数据输出合作方向分析报告。"
                )},
            ],
            temperature=0.3,
        )
        return resp.choices[0].message.content


# ═══════════════════════════════════════════════════════════════════════
#  主流程：编排以上所有组件
# ═══════════════════════════════════════════════════════════════════════

def main(target_company: str, user_question: str):
    print("=" * 60)
    print("  Agentic Graph Workflow — 产业图谱智能分析")
    print("=" * 60)

    # ---- 1. Schema 探测 ----
    print("\n[1/4] 🔍 探测图谱 Schema ...")
    explorer = Neo4jSchemaExplorer(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    schema = explorer.probe_schema()
    node_counts = {lbl: explorer.count_nodes(lbl) for lbl in schema["labels"]}
    print(f"    节点类型 {len(schema['labels'])} 个, "
          f"关系类型 {len(schema['relationship_types'])} 个, "
          f"属性 {len(schema['property_keys'])} 个")
    print(f"    节点数量：{node_counts}")
    print(f"    样例关系：{json.dumps(schema['sample_relationships'], ensure_ascii=False)}")

    # ---- 2. 初始化 LLM ----
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    # ---- 3. 查询分解 ----
    print(f"\n[2/4] 🧩 分解用户问题 ...")
    decomposer = QueryDecomposer(client, schema, node_counts)
    steps = decomposer.decompose(user_question)
    print(f"    分解为 {len(steps)} 个子查询步骤：")
    for s in steps:
        print(f"      Step {s['step']}: {s.get('purpose', '')[:60]}")

    # ---- 4. 分步执行 ----
    print(f"\n[3/4] ⚡ 分步执行 Cypher 查询 ...")
    executor = CypherExecutor(explorer.driver)
    results = executor.run_steps(steps)

    # ---- 5. 构建上下文 ----
    context_parts = []
    for sn in sorted(results.keys()):
        step_info = next(s for s in steps if s["step"] == sn)
        context_parts.append(
            f"【步骤 {sn}: {step_info.get('purpose', '')}】\n"
            f"查询：{step_info['cypher']}\n"
            f"结果：{json.dumps(results[sn], ensure_ascii=False, indent=2)}\n"
        )
    full_context = "\n".join(context_parts)

    # ---- 6. 业务推理 ----
    print(f"\n[4/4] 🧠 业务推理 → 生成报告 ...")
    reasoner = BusinessReasoner(client)
    report = reasoner.reason(full_context, target_company)

    # ---- 7. 输出 ----
    print("\n" + "=" * 60)
    print("  📊 合作方向分析报告")
    print("=" * 60)
    print(report)
    print("=" * 60)

    # 清理
    explorer.close()
    return report


# ═══════════════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # === 你可以在这里修改输入 ===
    TARGET = "美的集团"          # 外部公司
    QUESTION = (
        f"查询{TARGET}所处的产业链环节，"
        f"以及同环节/上下游有哪些企业，"
        f"这些企业有哪些技术能力和客户，"
        f"分析它们之间可能的合作方向"
    )
    # ===========================

    report = main(TARGET, QUESTION)
