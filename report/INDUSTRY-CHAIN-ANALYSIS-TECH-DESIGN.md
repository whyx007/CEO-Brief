# 产业链分析模块技术设计

> 项目：星擎智服 / ceo-brief-deploy
> 模块位置：企业查询模型下新增“产业链分析”
> 数据底座：本机 Neo4j 统一图谱
> 大模型：DeepSeek，目标模型为 `deepseek-v4-flash`
> 版本：V0.1

## 1. 目标

在现有“企业查询”能力下新增产业链分析模块，连接本机 Neo4j 统一图谱，支持围绕被投企业、产业链环节、外部产业、技术能力和合作机会进行结构化查询、图谱展示与大模型分析。

模块采用：

```text
固定分析模式 + 自由追问
```

第一版不做完全开放式数据库问答，而是优先用受控查询模板覆盖核心场景，再由大模型对查询结果进行解释、归纳和追问建议。

## 2. 已确认的现有系统

### 2.1 后端框架

当前项目为 FastAPI 单体应用：

```text
app.py
modules/
  ceo_brief/
  company_query/
  competitive_analysis/
```

新增模块建议：

```text
modules/industry_chain/
  __init__.py
  config.py
  routes.py
  services/
    __init__.py
    neo4j_client.py
    query_templates.py
    graph_serializer.py
    analyst.py
```

### 2.2 前端框架

当前前端为静态页面：

```text
frontend/index.html
frontend/assets/app.js
frontend/assets/styles.css
```

产业链分析建议作为“企业查询”页内的新子功能，而不是新增独立主导航。

### 2.3 LLM 接入

已有 DeepSeek 客户端：

```text
services/llm_client.py
```

当前 `.env` 使用 `DEEPSEEK_MODEL=deepseek-chat`。后续如使用 `deepseek-v4-flash`，应通过环境变量切换，不在代码中写死。

### 2.4 Neo4j 图谱现状

已查询本机 Neo4j，核心节点包括：

```text
Enterprise
SubTrack
ChainStage
KeyCapability
ApplicationScenario
TechDirection
Product
Industry
Capability
Supplier
Customer
```

核心关系包括：

```text
(:Enterprise)-[:FOCUSES_ON_SUB_TRACK]->(:SubTrack)
(:Enterprise)-[:LOCATED_IN_STAGE]->(:ChainStage)
(:Enterprise)-[:HAS_KEY_CAPABILITY]->(:KeyCapability)
(:Enterprise)-[:HAS_SUPPLIER]->(:Supplier)
(:Enterprise)-[:HAS_CUSTOMER]->(:Customer)
(:SubTrack)-[:HAS_STAGE]->(:ChainStage)
(:ChainStage)-[:UPSTREAM_OF]->(:ChainStage)
(:ChainStage)-[:REQUIRES_CAPABILITY]->(:KeyCapability)
(:TechDirection)-[:ENABLES_STAGE]->(:ChainStage)
(:ApplicationScenario)-[:DRIVES_STAGE]->(:ChainStage)
```

当前“被投企业”在图谱中主要以 `Enterprise` 节点表达，暂不单独建 `InvestedCompany` 标签。

## 3. 功能范围

### 3.1 产业链全景

用于查看所有子赛道、产业链环节和被投企业布局。

支持问题：

```text
当前有哪些产业链？
每条产业链有多少被投企业？
哪些环节企业覆盖多？
哪些环节暂无企业布局？
```

核心路径：

```cypher
(:SubTrack)-[:HAS_STAGE]->(:ChainStage)<-[:LOCATED_IN_STAGE]-(:Enterprise)
```

### 3.2 企业上下游分析

输入企业名称，查询其产业链位置、上游环节、下游环节、相邻环节企业、供应商和客户标签。

支持问题：

```text
某企业处于哪个产业链环节？
它的上游和下游分别是什么？
相邻环节有哪些被投企业可以协同？
它已有供应商和客户标签是什么？
```

核心路径：

```cypher
(:Enterprise)-[:LOCATED_IN_STAGE]->(:ChainStage)
(:ChainStage)-[:UPSTREAM_OF]->(:ChainStage)
(:Enterprise)-[:HAS_SUPPLIER]->(:Supplier)
(:Enterprise)-[:HAS_CUSTOMER]->(:Customer)
```

注意：当前图谱中企业与企业之间没有稳定的直接上下游关系，第一版应将上下游解释为“产业链环节上下游 + 相邻环节企业 + 企业客户/供应商标签”。

### 3.3 外部产业合作分析

输入外部产业、应用场景或需求方向，分析哪些被投企业可能与该外部产业相关。

支持问题：

```text
半导体检测可以和哪些被投企业合作？
锂电/光伏检测涉及哪些企业？
AI 集群与数据中心方向有哪些相关企业？
商业航天应用可以连接哪些被投企业？
```

核心路径：

```cypher
(:ApplicationScenario)-[:DRIVES_STAGE]->(:ChainStage)<-[:LOCATED_IN_STAGE]-(:Enterprise)
```

### 3.4 技术关联分析

输入技术方向、关键能力或技术关键词，查询相关企业、产业链环节和应用场景。

支持问题：

```text
哪些被投企业涉及光计算芯片？
哪些企业具备高速光互连能力？
某项技术对应哪些产业链环节？
```

核心路径：

```cypher
(:Enterprise)-[:HAS_KEY_CAPABILITY]->(:KeyCapability)
(:TechDirection)-[:ENABLES_STAGE]->(:ChainStage)<-[:LOCATED_IN_STAGE]-(:Enterprise)
(:ChainStage)-[:REQUIRES_CAPABILITY]->(:KeyCapability)
```

### 3.5 产业链被投企业合作机会探索

这是新增重点需求。目标不是简单列企业，而是基于图谱关系发现被投企业之间的潜在协同机会。

支持问题：

```text
某条产业链里哪些被投企业之间有合作机会？
某企业可以和哪些被投企业协同？
哪些企业处于上下游相邻环节，具备潜在供需关系？
哪些企业能力互补，适合联合方案或客户共拓？
哪些外部产业场景可以串联多家被投企业？
```

第一版合作机会分为四类：

| 类型 | 说明 | 图谱依据 |
| --- | --- | --- |
| 上下游协同 | 企业分别处于相邻上下游环节 | `ChainStage -[:UPSTREAM_OF]-> ChainStage` |
| 能力互补 | 企业能力不同但同属一个环节、场景或子赛道 | `HAS_KEY_CAPABILITY`、`LOCATED_IN_STAGE` |
| 场景共拓 | 多家企业共同服务同一应用场景或外部产业 | `ApplicationScenario -> ChainStage -> Enterprise` |
| 技术链协同 | 企业技术方向、关键能力与环节需求匹配 | `TechDirection`、`REQUIRES_CAPABILITY`、`HAS_KEY_CAPABILITY` |

合作机会需要输出：

```text
合作企业 A
合作企业 B
机会类型
关联产业链/环节
图谱证据
合作逻辑
置信等级
建议动作
```

第一版置信等级建议使用规则计算：

```text
高：上下游相邻环节 + 同一子赛道 + 至少一方有关键能力匹配
中：同一应用场景或同一技术方向 + 企业处于相关环节
低：仅共享行业/场景/能力关键词，缺少明确上下游路径
```

## 4. 产品交互设计

企业查询页新增产业链分析区域：

```text
企业查询
  企业库查询
  产业链分析
    [产业链全景]
    [企业上下游]
    [外部产业合作]
    [技术关联]
    [合作机会探索]
```

每个模式包含：

```text
输入区
图谱区
AI 分析区
结果表格
推荐追问
```

合作机会探索模式建议输入：

```text
分析对象类型：
  - 全部产业链
  - 指定子赛道
  - 指定企业
  - 指定外部产业/应用场景
  - 指定技术/能力

输入关键词：
  企业名 / 子赛道 / 场景 / 技术关键词

排序方式：
  - 协同强度
  - 上下游距离
  - 企业覆盖数量
  - 机会类型
```

## 5. 后端接口设计

### 5.1 状态接口

```text
GET /api/industry-chain/status
```

返回 Neo4j 连通性、节点数量、关系数量、可用子赛道和模型配置状态。

### 5.2 产业链全景

```text
GET /api/industry-chain/overview
```

Query 参数：

```text
subTrackId?: string
limit?: number
```

### 5.3 企业上下游

```text
POST /api/industry-chain/company-updown
```

Request：

```json
{
  "enterpriseName": "中科慧远视觉技术（洛阳）有限公司",
  "limit": 30,
  "includeGraph": true,
  "includeAnalysis": true
}
```

### 5.4 外部产业合作

```text
POST /api/industry-chain/external-industry
```

Request：

```json
{
  "keyword": "半导体检测",
  "limit": 30,
  "includeGraph": true,
  "includeAnalysis": true
}
```

### 5.5 技术关联

```text
POST /api/industry-chain/technology
```

Request：

```json
{
  "keyword": "光计算芯片",
  "limit": 30,
  "includeGraph": true,
  "includeAnalysis": true
}
```

### 5.6 合作机会探索

```text
POST /api/industry-chain/opportunities
```

Request：

```json
{
  "scopeType": "sub_track",
  "keyword": "光通信/光模块",
  "opportunityTypes": ["updown", "capability_complement", "scenario_joint", "technology_chain"],
  "limit": 30,
  "includeGraph": true,
  "includeAnalysis": true
}
```

`scopeType` 可选值：

```text
all
sub_track
enterprise
scenario
technology
```

Response：

```json
{
  "ok": true,
  "mode": "opportunities",
  "query": {
    "scopeType": "sub_track",
    "keyword": "光通信/光模块"
  },
  "answer": "基于当前图谱，光通信/光模块方向存在三类合作机会...",
  "opportunities": [
    {
      "sourceEnterprise": "企业A",
      "targetEnterprise": "企业B",
      "opportunityType": "updown",
      "confidence": "high",
      "subTrack": "光通信/光模块",
      "sourceStage": "光电芯片（裸芯片/晶圆级）",
      "targetStage": "光引擎/器件集成",
      "evidence": [
        "企业A位于上游环节",
        "企业B位于下游环节",
        "两个环节存在 UPSTREAM_OF 路径"
      ],
      "cooperationLogic": "企业A可作为上游器件或技术能力提供方，企业B可作为集成验证和客户导入方。",
      "suggestedAction": "建议先做产品规格和目标客户重合度核验。"
    }
  ],
  "graph": {
    "nodes": [],
    "edges": []
  },
  "tables": [],
  "meta": {
    "cypherTemplates": ["opportunities_updown_by_subtrack"],
    "rowCount": 30,
    "llmModel": "deepseek-v4-flash"
  },
  "suggestedQuestions": [
    "这些机会里哪些最适合先做内部撮合？",
    "按上下游协同强度排序",
    "只看高置信合作机会"
  ]
}
```

### 5.7 自由追问

```text
POST /api/industry-chain/chat
```

Request：

```json
{
  "question": "这些企业里谁最适合一起做半导体检测客户拓展？",
  "contextMode": "opportunities",
  "context": {
    "lastQueryId": "optional"
  }
}
```

第一版自由追问只允许基于最近一次结构化查询结果回答。后续再扩展为受限 Cypher 自动生成。

## 6. 统一返回结构

所有分析接口尽量返回同一结构：

```json
{
  "ok": true,
  "mode": "overview",
  "answer": "",
  "graph": {
    "nodes": [
      {
        "id": "ENT_001",
        "label": "某企业",
        "type": "Enterprise",
        "group": "enterprise",
        "properties": {}
      }
    ],
    "edges": [
      {
        "id": "edge_001",
        "source": "ENT_001",
        "target": "STG_001",
        "type": "LOCATED_IN_STAGE",
        "label": "位于环节"
      }
    ]
  },
  "tables": [
    {
      "title": "结果明细",
      "columns": ["企业", "环节", "能力"],
      "rows": []
    }
  ],
  "meta": {
    "rowCount": 0,
    "elapsedMs": 0,
    "neo4jConnected": true,
    "llmEnabled": true
  },
  "suggestedQuestions": []
}
```

## 7. 查询模板设计

### 7.1 产业链全景

```cypher
MATCH (s:SubTrack)
OPTIONAL MATCH (s)-[:HAS_STAGE]->(st:ChainStage)
OPTIONAL MATCH (e:Enterprise)-[:LOCATED_IN_STAGE]->(st)
RETURN s.id AS subTrackId,
       s.name AS subTrack,
       st.id AS stageId,
       st.name AS stage,
       st.stage_level AS stageLevel,
       st.stage_order AS stageOrder,
       count(DISTINCT e) AS enterpriseCount,
       collect(DISTINCT e.name)[0..10] AS enterprises
ORDER BY subTrack, stageOrder
```

### 7.2 企业上下游

```cypher
MATCH (e:Enterprise)
WHERE e.name CONTAINS $enterpriseName
OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
OPTIONAL MATCH (up:ChainStage)-[:UPSTREAM_OF]->(st)
OPTIONAL MATCH (st)-[:UPSTREAM_OF]->(down:ChainStage)
OPTIONAL MATCH (upE:Enterprise)-[:LOCATED_IN_STAGE]->(up)
OPTIONAL MATCH (downE:Enterprise)-[:LOCATED_IN_STAGE]->(down)
OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
RETURN e.name AS enterprise,
       collect(DISTINCT s.name) AS subTracks,
       collect(DISTINCT st.name) AS stages,
       collect(DISTINCT up.name) AS upstreamStages,
       collect(DISTINCT upE.name)[0..$limit] AS upstreamEnterprises,
       collect(DISTINCT down.name) AS downstreamStages,
       collect(DISTINCT downE.name)[0..$limit] AS downstreamEnterprises,
       collect(DISTINCT supplier.name)[0..$limit] AS suppliers,
       collect(DISTINCT customer.name)[0..$limit] AS customers
LIMIT $limit
```

### 7.3 外部产业合作

```cypher
MATCH (a:ApplicationScenario)
WHERE a.name CONTAINS $keyword OR a.description CONTAINS $keyword
OPTIONAL MATCH (a)-[:DRIVES_STAGE]->(st:ChainStage)
OPTIONAL MATCH (e:Enterprise)-[:LOCATED_IN_STAGE]->(st)
OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
RETURN a.name AS scenario,
       st.name AS stage,
       collect(DISTINCT e.name)[0..$limit] AS enterprises,
       collect(DISTINCT k.name)[0..20] AS keyCapabilities
LIMIT $limit
```

### 7.4 技术关联

```cypher
MATCH (k:KeyCapability)
WHERE k.name CONTAINS $keyword OR k.description CONTAINS $keyword
OPTIONAL MATCH (e:Enterprise)-[:HAS_KEY_CAPABILITY]->(k)
OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
RETURN k.name AS capability,
       collect(DISTINCT e.name)[0..$limit] AS enterprises,
       collect(DISTINCT st.name)[0..20] AS stages,
       collect(DISTINCT s.name)[0..10] AS subTracks
LIMIT $limit
```

### 7.5 合作机会：上下游协同

```cypher
MATCH (s:SubTrack)
WHERE $scopeType = 'all' OR s.name CONTAINS $keyword OR s.id = $keyword
MATCH (s)-[:HAS_STAGE]->(up:ChainStage)-[:UPSTREAM_OF]->(down:ChainStage)
MATCH (a:Enterprise)-[:LOCATED_IN_STAGE]->(up)
MATCH (b:Enterprise)-[:LOCATED_IN_STAGE]->(down)
WHERE a <> b
OPTIONAL MATCH (a)-[:HAS_KEY_CAPABILITY]->(ak:KeyCapability)
OPTIONAL MATCH (b)-[:HAS_KEY_CAPABILITY]->(bk:KeyCapability)
RETURN a.name AS sourceEnterprise,
       b.name AS targetEnterprise,
       s.name AS subTrack,
       up.name AS sourceStage,
       down.name AS targetStage,
       collect(DISTINCT ak.name)[0..5] AS sourceCapabilities,
       collect(DISTINCT bk.name)[0..5] AS targetCapabilities,
       'updown' AS opportunityType,
       'high' AS confidence
LIMIT $limit
```

### 7.6 合作机会：场景共拓

```cypher
MATCH (a:ApplicationScenario)
WHERE $scopeType = 'all' OR a.name CONTAINS $keyword OR a.description CONTAINS $keyword
MATCH (a)-[:DRIVES_STAGE]->(st:ChainStage)<-[:LOCATED_IN_STAGE]-(e:Enterprise)
WITH a, collect(DISTINCT e) AS enterprises
UNWIND enterprises AS e1
UNWIND enterprises AS e2
WITH a, e1, e2
WHERE id(e1) < id(e2)
RETURN e1.name AS sourceEnterprise,
       e2.name AS targetEnterprise,
       a.name AS scenario,
       'scenario_joint' AS opportunityType,
       'medium' AS confidence
LIMIT $limit
```

## 8. 大模型编排

### 8.1 模型职责

DeepSeek 负责：

```text
意图解释
查询结果总结
合作机会逻辑归纳
风险和缺口提示
推荐追问生成
```

DeepSeek 不直接负责：

```text
数据库连接
无校验 Cypher 执行
凭空补充企业关系
写入 Neo4j
```

### 8.2 提示词原则

系统提示词应明确：

```text
你是产业链与投后服务分析助手。
只能基于 Neo4j 查询结果回答。
不能编造不存在的企业关系。
如果数据库没有证据，明确说明“当前图谱未发现”。
合作机会必须给出图谱依据。
输出要面向投后服务团队，强调可执行动作。
```

### 8.3 合作机会分析提示词模板

```text
请基于以下 Neo4j 查询结果，分析被投企业之间的合作机会。

要求：
1. 按机会类型归类：上下游协同、能力互补、场景共拓、技术链协同。
2. 每个机会必须说明图谱证据。
3. 不要编造未在结果中出现的企业、客户或合作关系。
4. 对每个机会给出置信等级和建议动作。
5. 如果证据不足，明确标记为低置信或建议补充核验。

查询结果：
{query_results}
```

## 9. 安全与配置

Neo4j 连接信息只放后端环境变量：

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=******
NEO4J_DATABASE=neo4j
```

前端不得接触数据库账号密码。

Cypher 执行限制：

```text
只允许 MATCH / OPTIONAL MATCH / WITH / RETURN / ORDER BY / LIMIT / WHERE / UNWIND
禁止 CREATE / MERGE / SET / DELETE / DETACH DELETE / DROP / CALL dbms
所有查询必须有 LIMIT 或服务端最大行数限制
```

第一版建议只执行预置模板，不开放任意 Cypher。

## 10. 前端实现建议

### 10.1 图谱库

当前项目没有前端构建链。MVP 推荐使用 ECharts Graph：

```text
frontend/assets/vendor/echarts.min.js
```

原因：

```text
可直接在静态 HTML 中加载
支持力导向图
实现成本低
足够覆盖产业链图谱 MVP
```

### 10.2 图谱节点样式

```text
SubTrack: 产业链/子赛道
ChainStage: 产业链环节
Enterprise: 被投企业
KeyCapability: 关键能力
ApplicationScenario: 外部产业/应用场景
TechDirection: 技术方向
Supplier/Customer: 供应商/客户标签
```

### 10.3 合作机会展示

合作机会不建议只画图，还需要表格承载判断依据：

```text
企业A
企业B
机会类型
所在链条
上游环节
下游环节
能力/场景依据
置信等级
建议动作
```

## 11. 实施阶段

### Phase 1：只读查询与结构化展示

目标：

```text
Neo4j 连通
5 个模式接口可用
前端能展示表格和基础图谱
不接自由 Cypher
```

范围：

```text
status
overview
company-updown
external-industry
technology
opportunities
```

### Phase 2：DeepSeek 分析总结

目标：

```text
每个模式增加 AI 分析结论
合作机会给出逻辑、置信等级和建议动作
生成推荐追问
```

### Phase 3：上下文追问

目标：

```text
用户可基于最近一次分析继续追问
追问不重新裸查数据库，优先使用上次结构化结果
必要时由后端选择模板补充查询
```

### Phase 4：受控自然语言查询

目标：

```text
模型识别意图
后端选择模板
必要时生成受限 Cypher
执行前做白名单校验
```

## 12. 验收标准

MVP 验收用例：

```text
1. 能打开产业链分析页，看到所有子赛道、环节和企业数量。
2. 输入企业名，能返回企业所在环节、上下游环节、相邻环节企业。
3. 输入外部产业/场景，能返回相关被投企业和图谱。
4. 输入技术关键词，能返回相关企业、环节和能力。
5. 输入子赛道或企业，能生成被投企业合作机会清单。
6. 合作机会必须包含企业A、企业B、机会类型、图谱依据、置信等级、建议动作。
7. AI 分析不能编造数据库中不存在的企业关系。
8. Neo4j 密码不出现在前端代码和接口响应中。
```

## 13. 关键风险

### 13.1 企业上下游口径风险

当前图谱中企业与企业的直接供应关系不强，主要是环节上下游和客户/供应商标签。产品文案必须避免把“潜在协同”表述成“已发生合作”。

### 13.2 数据覆盖风险

部分企业未挂接到子赛道或环节，合作机会分析可能遗漏。接口应返回数据覆盖提示。

### 13.3 模型幻觉风险

合作机会分析必须严格基于查询结果。提示词、接口返回和前端文案都要保留“图谱依据”。

### 13.4 图谱复杂度风险

全量图谱节点较多，前端不能一次性渲染全部企业关系。必须按模式、子赛道、企业或关键词裁剪。

## 14. 推荐下一步

下一步可以按以下顺序进入实现：

```text
1. 新增 modules/industry_chain 模块骨架
2. 接入 Neo4j Python driver
3. 实现 status 和 overview
4. 实现 company-updown
5. 实现 opportunities
6. 前端增加产业链分析区域和结果表格
7. 接入 ECharts Graph
8. 接入 DeepSeek 分析总结
```

第一轮实现建议先做 `overview + company-updown + opportunities`，因为这三项最能体现产业链图谱和被投企业合作机会价值。
