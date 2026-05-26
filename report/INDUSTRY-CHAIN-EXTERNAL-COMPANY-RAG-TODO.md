# 外部企业多维合作机会 RAG 改造待办

## 目标

把“产业链机会探索 / 外部公司合作探索”改造成一个泛化的外部企业多维 RAG 分析能力，而不是针对某一家样本企业做规则补丁。

用户输入任意外部企业后，系统应先构建该企业的业务画像，再从 Neo4j 被投企业图谱中按多个合作维度召回候选企业，最后输出“外部企业 × 被投企业”的合作机会报告。

`奕斯伟材料` 只是样本和验收用例之一。最终方案需要同样适用于电网、车企、能源集团、半导体公司、医院、数据中心、主机厂、航天院所等不同类型外部企业。

## 当前问题

当前 RAG 链路是：

1. 输入外部企业名称。
2. 拆关键词和行业词。
3. 用关键词匹配 Neo4j 中被投企业的客户、供应商、能力、产品、场景、产业链环节。
4. 把召回结果交给 DeepSeek 生成报告。

这个链路的问题是“先匹配，后理解”。它没有先回答：

- 这家外部企业到底做什么？
- 它处在什么产业链位置？
- 它的上游需要什么供应商、设备、材料、技术服务？
- 它的下游客户或应用场景是什么？
- 它可能和被投企业发生哪几类合作关系？

因此，当企业名称包含宽泛词时，如“材料、能源、科技、智能、装备”，召回会被泛词带偏。

## 泛化设计原则

### 1. 先画像，再召回

外部企业合作探索必须先构建 `ExternalCompanyProfile`，再用画像中的结构化字段生成召回词和合作维度。

### 2. 多维召回，不做单一关键词召回

召回应围绕合作关系展开，而不是围绕企业名称文本展开。

至少应覆盖：

- 外部企业作为客户：被投企业向它提供设备、材料、软件、服务、系统集成。
- 外部企业作为供应商：外部企业向被投企业提供材料、部件、平台、渠道或基础设施。
- 双方联合研发：能力互补、技术路线相邻、产品联合定义。
- 双方客户协同：服务同类下游客户，可联合拓展市场。
- 场景共创：外部企业有真实应用场景，被投企业有可落地能力。
- 厂务和运营配套：能源、电源、检测、运维、安全、碳管理等非主链但可合作方向。

### 3. 证据优先，模型负责组织表达

DeepSeek 不应负责凭空扩展候选企业。它应负责：

- 整理 Neo4j 证据。
- 解释合作逻辑。
- 归纳合作方向。
- 排序优先级。
- 标注证据不足和需核验点。

### 4. 宽词降权，专业词升权

“材料、智能、科技、装备、能源”等宽词只能作为弱信号。应优先使用产品、工艺、客户、场景、产业链位置等专业词。

## 外部企业画像结构

建议新增：

- `modules/industry_chain/services/external_company_profile.py`

核心数据结构：

```json
{
  "companyName": "外部企业名称",
  "aliases": ["简称", "品牌名", "集团名"],
  "industryDomains": ["一级行业", "二级行业"],
  "subSectors": ["细分赛道"],
  "chainPosition": "上游/中游/下游/平台方/应用方/运营方/客户方",
  "coreProducts": ["核心产品"],
  "coreTechnologies": ["核心技术"],
  "productionProcesses": ["关键工艺或业务流程"],
  "upstreamNeeds": ["设备", "材料", "部件", "软件", "服务"],
  "downstreamApplications": ["下游应用"],
  "targetCustomers": ["客户类型"],
  "painPoints": ["业务痛点"],
  "cooperationDimensions": [
    {
      "mode": "supply_to_external",
      "externalRole": "buyer",
      "description": "被投企业向外部企业供应产品/设备/服务",
      "queryTerms": ["检测", "量测", "设备", "系统"]
    },
    {
      "mode": "external_supply_to_portfolio",
      "externalRole": "supplier",
      "description": "外部企业向被投企业供应材料/部件/平台",
      "queryTerms": ["硅基", "衬底", "芯片"]
    },
    {
      "mode": "joint_r_and_d",
      "externalRole": "partner",
      "description": "联合研发或技术互补",
      "queryTerms": ["材料工艺", "联合开发"]
    },
    {
      "mode": "shared_customer",
      "externalRole": "market_partner",
      "description": "共同服务同类客户或行业",
      "queryTerms": ["客户", "行业场景"]
    },
    {
      "mode": "scenario_landing",
      "externalRole": "scenario_owner",
      "description": "外部企业提供场景，被投企业提供能力",
      "queryTerms": ["应用场景", "试点"]
    },
    {
      "mode": "factory_or_operation_support",
      "externalRole": "operator",
      "description": "厂务、运营、能源、运维、安全等配套",
      "queryTerms": ["储能", "温控", "巡检", "安全"]
    }
  ],
  "weakTerms": ["材料", "科技", "智能"],
  "strongTerms": ["能体现业务本质的专业词"]
}
```

## 画像生成策略

### 第一阶段：规则画像，不消耗 DeepSeek 配额

先建一个通用规则库，覆盖常见企业类型：

- 电网/电力公司
- 车企/主机厂
- 半导体/芯片/材料企业
- 能源/新能源/储能企业
- 数据中心/算力/云厂商
- 医院/医疗机构
- 航天/航空/军工院所
- 化工/新材料企业
- 轨交/铁路/交通企业
- 工业制造/装备企业

每类规则输出画像模板和合作维度，不针对单个样本硬编码。

### 第二阶段：DeepSeek 画像增强

配额允许时，用 DeepSeek 对外部企业做画像补全：

- 只输出结构化 JSON。
- 不直接生成报告。
- 画像中的事实若无法确认，标注 `inferred` 或 `unknown`。
- 画像生成后仍需经过规则清洗，避免宽词污染召回。

## 多维 Neo4j 召回

建议新增一个通用 Cypher 模板，不按“外部企业类型”写死，而按 `cooperationDimensions[].queryTerms` 检索。

每条召回应返回：

- `targetEnterprise`
- `matchedDimension`
- `cooperationMode`
- `externalRole`
- `matchedTerms`
- `matchedFields`
- `subTrack`
- `stage`
- `capabilities`
- `products`
- `customers`
- `suppliers`
- `scenarios`
- `demands`
- `industries`
- `score`
- `evidence`

召回字段建议覆盖 Neo4j 关系：

- `HAS_KEY_CAPABILITY`
- `HAS_CAPABILITY`
- `PROVIDES_PRODUCT`
- `APPLIES_TO_SCENARIO`
- `HAS_DEMAND`
- `SERVES_INDUSTRY`
- `FOCUSES_ON_SUB_TRACK`
- `LOCATED_IN_STAGE`
- `HAS_CUSTOMER`
- `HAS_SUPPLIER`

## 打分与重排序

基础规则：

- 命中 `strongTerms`：高权重。
- 命中 `weakTerms`：低权重，仅作为补充分。
- 命中多个合作维度：加权。
- 命中产品/能力/场景：高于仅命中客户或行业标签。
- 有明确客户/供应商/应用场景证据：加权。
- 企业与外部企业同城/同省：可加权，但不能压过业务匹配。
- 泛行业词单独命中时不得进入高置信。

候选结果应分为：

- `high`: 有明确产品/能力/场景证据，合作逻辑直接。
- `medium`: 有行业或客户相关性，但需核验具体产品适配。
- `low`: 仅弱相关，默认不进报告主体，可放证据池。

## 报告输出结构

外部公司合作探索的报告应泛化为：

```markdown
# 外部企业 × 被投企业 潜在合作机会分析

## 一、外部企业业务画像

| 维度 | 内容 |
|------|------|
| 核心业务 | ... |
| 产业链位置 | ... |
| 关键能力/产品 | ... |
| 上游需求 | ... |
| 下游应用/客户 | ... |

## 二、合作机会总览

| 合作方向 | 外部企业角色 | 候选企业数 | 主要切入点 |
|---------|-------------|-----------|-----------|

## 三、分方向合作机会

### 3.1 外部企业作为客户：被投企业可供应产品/服务

### 3.2 外部企业作为供应商：被投企业可采购/使用其能力

### 3.3 联合研发与技术协同

### 3.4 客户协同与市场共拓

### 3.5 场景落地与运营配套

## 四、重点推荐

| 优先级 | 被投企业 | 合作模式 | 推荐理由 | 证据 |
|-------|---------|---------|---------|------|

## 五、数据限制与需核验事项
```

## 前端展示

建议展示四块：

1. 外部企业画像卡片
2. 合作方向总览
3. 分组报告
4. RAG 证据明细

证据明细每条展示：

- 合作模式
- 外部企业角色
- 被投企业
- 匹配字段
- 匹配词
- 图谱证据
- 置信度

## 代码改造位置

### 后端

- `modules/industry_chain/routes.py`
  - `industry_chain_opportunities()` 增加外部企业画像构建、多维召回、合并重排序。

- `modules/industry_chain/services/query_templates.py`
  - 增加通用多维外部企业召回 Cypher。

- `modules/industry_chain/services/analyst.py`
  - 外部公司模式的 prompt 改为“外部企业多维合作机会报告”。
  - 接收 `externalProfile` 和 grouped opportunities。

- 新增：
  - `modules/industry_chain/services/external_company_profile.py`
  - `modules/industry_chain/services/opportunity_ranker.py`

### 前端

- `frontend/assets/app.js`
  - 展示 `externalProfile`
  - 展示 grouped opportunities
  - 展示证据明细

- `frontend/index.html`
  - 可保留现有入口，不需要新增一级模块。

## 验收样例

不要只用一个企业验收。至少用以下类型：

1. 半导体材料企业：`奕斯伟材料`
   - 应召回半导体设备、检测量测、光电芯片、硅基材料、Micro-LED、硅光等相关企业。
   - 不应被泛复合材料、陶瓷、纳滤膜等宽词结果占据。

2. 电网企业：`国网陕西省电力公司`
   - 应召回电力设备监测、储能、新能源消纳、无人机巡检、虚拟电厂、配网智能化等相关企业。

3. 车企：`比亚迪`
   - 应召回电池材料、热管理、智能驾驶、车载传感、轻量化材料、充换电、储能等相关企业。

4. 数据中心/算力企业：`西安AI数据中心`
   - 应召回液冷、储能、电源管理、光通信、网络互联、运维监测、算力平台等相关企业。

5. 医疗机构：`西安交通大学第一附属医院`
   - 应召回医疗检测、影像、传感、生物材料、AI诊断、医疗机器人等相关企业。

## 明天优先顺序

1. 先实现规则版 `ExternalCompanyProfile`，不消耗 DeepSeek 配额。
2. 建立通用合作维度和强/弱词机制。
3. 增加通用多维 Neo4j 召回。
4. 实现合并、去重和重排序。
5. 用上述 5 类样例跑召回质量。
6. 再接 DeepSeek 报告提示词。
7. 最后补前端画像和证据展示。
