# CEO参阅 - 后端开工任务单

## 目标
为 CEO参阅模块提供最小可用后端能力，支撑首页展示与设置页配置。

## 一、后端职责
- 提供 CEO参阅数据聚合接口
- 提供目标设置接口
- 提供 Prompt 设置接口
- 提供手动生成/刷新接口
- 提供天气数据接口封装

---

## 二、建议接口

### 1. 获取 CEO参阅首页数据
`GET /api/ceo-brief/today`

返回：
- industrialNews
- targetUpdates
- todoItems
- weather
- generatedAt

### 2. 手动生成 CEO参阅
`POST /api/ceo-brief/generate`

入参：
- date（可选）
- forceRefresh（可选）

### 3. 获取目标设置
`GET /api/ceo-brief/settings/targets`

### 4. 保存目标设置
`PUT /api/ceo-brief/settings/targets`

字段建议：
- companies: string[]
- industries: string[]
- keywords: string[]
- regions: string[]

### 5. 获取 Prompt 设置
`GET /api/ceo-brief/settings/prompts`

### 6. 保存 Prompt 设置
`PUT /api/ceo-brief/settings/prompts`

字段建议：
- newsFilterPrompt
- newsSummaryPrompt
- todoPrompt

### 7. 恢复默认 Prompt
`POST /api/ceo-brief/settings/prompts/reset`

---

## 三、数据结构建议

### ceo_brief_run
- id
- run_date
- status
- industrial_news_json
- target_updates_json
- todo_items_json
- weather_json
- prompt_snapshot_json
- generated_at

### ceo_brief_target_settings
- id
- companies_json
- industries_json
- keywords_json
- regions_json
- updated_at

### ceo_brief_prompt_settings
- id
- news_filter_prompt
- news_summary_prompt
- todo_prompt
- updated_at

---

## 四、后端实现优先级

### P0
- 设置读取/保存
- 首页聚合返回结构
- 手动生成接口
- 天气数据接入

### P1
- prompt 快照留存
- 空状态处理
- 错误兜底返回

### P2
- 生成历史
- 二次缓存
- 来源点击追踪

---

## 五、后端注意事项
- Prompt 设置必须持久化
- 每次生成建议记录 prompt_snapshot，便于回溯
- 天气接口先轻量接入，避免引入复杂依赖
- 所有首页板块都要支持空状态，不能因为某一块失败导致整页不可用
