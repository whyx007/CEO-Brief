# CEO参阅 - 后端接口和数据模型正式稿

## 文档目的
本文件用于给后端工程师提供可直接开工的接口与数据模型说明，覆盖 CEO参阅模块的一期 MVP。

适用角色：
- `backend-platform`
- `frontend-web`
- `qa-testing`

---

# 一、范围说明
一期 CEO参阅模块后端需支持以下能力：
1. 获取首页参阅数据
2. 手动生成 CEO参阅
3. 保存/读取目标设置
4. 保存/读取 Prompt 设置
5. 恢复默认 Prompt

首页数据需覆盖：
- 产经信息
- 目标信息
- 今日代办
- 天气情况

---

# 二、接口设计

# 2.1 获取 CEO参阅首页数据

## 接口
`GET /api/ceo-brief/today`

## 用途
获取当前展示用的 CEO参阅首页数据。

## Query 参数（可选）
- `date`: string，格式 `YYYY-MM-DD`

## Response 示例
```json
{
  "date": "2026-04-15",
  "generatedAt": "2026-04-15T09:30:00+08:00",
  "status": "success",
  "industrialNews": [
    {
      "id": "news_001",
      "title": "某产业重大动态",
      "summary": "摘要内容",
      "source": "来源名称",
      "publishedAt": "2026-04-15T08:00:00+08:00",
      "importanceReason": "为什么值得关注"
    }
  ],
  "targetUpdates": [
    {
      "id": "target_001",
      "title": "目标企业相关动态",
      "summary": "摘要内容",
      "matchedTargets": ["某企业", "新能源"],
      "source": "来源名称",
      "publishedAt": "2026-04-15T07:40:00+08:00",
      "relevanceReason": "为何命中目标"
    }
  ],
  "todoItems": [
    {
      "id": "todo_001",
      "content": "跟进某企业合作进展",
      "priority": "high",
      "reason": "目标企业动态出现合作信号"
    }
  ],
  "weather": {
    "location": "上海",
    "condition": "多云",
    "temperatureMin": 18,
    "temperatureMax": 26,
    "advice": "适合外出，注意早晚温差"
  }
}
```

## 字段说明
- `status`: `success | partial_success | empty | failed`
- `industrialNews`: 产经信息列表
- `targetUpdates`: 目标信息列表
- `todoItems`: 今日代办列表
- `weather`: 天气信息对象

## 返回要求
- 即使单个模块为空，也应返回完整结构
- 单个模块失败时，优先返回 `partial_success`，避免整页不可用

---

# 2.2 手动生成 CEO参阅

## 接口
`POST /api/ceo-brief/generate`

## 用途
手动触发 CEO参阅生成。

## Request 示例
```json
{
  "date": "2026-04-15",
  "forceRefresh": true
}
```

## 字段说明
- `date`: 可选，不传则默认当天
- `forceRefresh`: 可选，是否强制刷新

## Response 示例
```json
{
  "runId": "run_20260415_001",
  "status": "started",
  "message": "CEO参阅生成任务已开始"
}
```

## 一期建议
MVP 可先同步返回结果，或采用“开始生成 + 前端轮询”的轻量模式。

---

# 2.3 获取目标设置

## 接口
`GET /api/ceo-brief/settings/targets`

## Response 示例
```json
{
  "companies": ["某被投企业"],
  "industries": ["新能源", "半导体"],
  "keywords": ["融资", "订单", "合作"],
  "regions": ["上海", "苏州"],
  "updatedAt": "2026-04-15T09:00:00+08:00"
}
```

---

# 2.4 保存目标设置

## 接口
`PUT /api/ceo-brief/settings/targets`

## Request 示例
```json
{
  "companies": ["某被投企业"],
  "industries": ["新能源", "半导体"],
  "keywords": ["融资", "订单", "合作"],
  "regions": ["上海", "苏州"]
}
```

## Response 示例
```json
{
  "success": true,
  "message": "目标设置已保存"
}
```

## 校验建议
- 所有字段均可为空数组
- 每项长度建议做基础限制
- 去重后存储

---

# 2.5 获取 Prompt 设置

## 接口
`GET /api/ceo-brief/settings/prompts`

## Response 示例
```json
{
  "newsFilterPrompt": "请筛选最值得CEO关注的产经信息...",
  "newsSummaryPrompt": "请将新闻总结为适合CEO快速阅读的摘要...",
  "todoPrompt": "请基于重点信息生成今日待办建议...",
  "updatedAt": "2026-04-15T09:00:00+08:00"
}
```

---

# 2.6 保存 Prompt 设置

## 接口
`PUT /api/ceo-brief/settings/prompts`

## Request 示例
```json
{
  "newsFilterPrompt": "请筛选最值得CEO关注的产经信息...",
  "newsSummaryPrompt": "请将新闻总结为适合CEO快速阅读的摘要...",
  "todoPrompt": "请基于重点信息生成今日待办建议..."
}
```

## Response 示例
```json
{
  "success": true,
  "message": "Prompt 设置已保存"
}
```

## 校验建议
- Prompt 不允许全为空
- 长度建议限制，避免异常超长

---

# 2.7 恢复默认 Prompt

## 接口
`POST /api/ceo-brief/settings/prompts/reset`

## Response 示例
```json
{
  "success": true,
  "message": "已恢复默认 Prompt",
  "data": {
    "newsFilterPrompt": "默认值...",
    "newsSummaryPrompt": "默认值...",
    "todoPrompt": "默认值..."
  }
}
```

---

# 三、数据模型设计

# 3.1 ceo_brief_run

## 用途
记录每次 CEO参阅生成结果。

## 字段建议
- `id` varchar / uuid
- `run_date` date
- `status` varchar
- `industrial_news_json` json
- `target_updates_json` json
- `todo_items_json` json
- `weather_json` json
- `prompt_snapshot_json` json
- `generated_at` datetime
- `created_at` datetime
- `updated_at` datetime

## 说明
- `prompt_snapshot_json` 用于记录本次生成时实际使用的 Prompt
- 推荐保留完整结果，便于后续追溯

---

# 3.2 ceo_brief_target_settings

## 用途
保存目标设置。

## 字段建议
- `id` varchar / uuid
- `companies_json` json
- `industries_json` json
- `keywords_json` json
- `regions_json` json
- `updated_at` datetime

## 说明
一期如果只服务单租户/单组织，可先做单记录模式。

---

# 3.3 ceo_brief_prompt_settings

## 用途
保存 Prompt 设置。

## 字段建议
- `id` varchar / uuid
- `news_filter_prompt` text
- `news_summary_prompt` text
- `todo_prompt` text
- `updated_at` datetime

---

# 四、服务层建议

建议拆成以下服务：

## 4.1 BriefGenerationService
职责：
- 负责拉取设置
- 组织生成流程
- 汇总 4 个板块结果
- 写入 ceo_brief_run

## 4.2 BriefSettingsService
职责：
- 处理目标设置读写
- 处理 Prompt 设置读写
- 处理默认 Prompt 恢复

## 4.3 WeatherService
职责：
- 获取天气信息
- 标准化天气返回结构

## 4.4 NewsAggregationService
职责：
- 获取新闻输入
- 按 Prompt 处理筛选和摘要
- 输出产经信息与目标信息

## 4.5 TodoGenerationService
职责：
- 基于前面结果生成今日代办

---

# 五、错误处理要求

## 原则
- 模块级失败不拖垮整页
- 统一返回结构
- 前端可据此渲染部分成功状态

## 建议策略
### 产经信息失败
- `industrialNews` 返回空数组
- 记录错误日志

### 目标信息失败
- `targetUpdates` 返回空数组
- 提示可调整目标设置

### 今日代办失败
- `todoItems` 返回空数组

### 天气失败
- `weather` 返回 null 或默认结构

---

# 六、一期实现建议

## 必做
- `/today`
- `/generate`
- 目标设置读写
- Prompt 设置读写
- Prompt 恢复默认
- 生成结果留存

## 可选优化
- 生成历史查询
- 重新生成防抖
- 缓存策略

---

# 七、联调注意事项

- 前端需要严格依赖统一返回结构
- 空数组与空对象状态要提前约定
- `status` 字段必须稳定
- 时间字段统一使用 ISO 格式
- Prompt 设置保存后，需在下次生成中生效

---

# 八、待人工确认项
- 新闻源/产经信息来源的具体接入方式
- 天气接口来源和默认城市逻辑
- 是否需要支持多用户/多组织的独立设置
- Prompt 设置是否需要简单的变更留痕
