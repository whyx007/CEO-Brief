# CEO参阅 - 前端字段清单与接口联调稿

## 文档目的
本文件用于指导前端工程师完成 CEO参阅首页与设置页的字段映射、状态处理和接口联调。

适用角色：
- `frontend-web`
- `ui-ux`
- `backend-platform`
- `qa-testing`

---

# 一、页面范围
前端本期需要完成两个页面：
1. CEO参阅首页
2. CEO参阅设置页

---

# 二、首页字段映射

# 2.1 页面接口

## 获取首页数据
`GET /api/ceo-brief/today`

## 手动重新生成
`POST /api/ceo-brief/generate`

---

# 2.2 首页顶层状态字段

接口返回顶层字段：
- `date`
- `generatedAt`
- `status`
- `industrialNews`
- `targetUpdates`
- `todoItems`
- `weather`

## 前端页面状态建议
```ts
interface BriefPageState {
  loading: boolean;
  regenerating: boolean;
  error: string | null;
  data: BriefTodayResponse | null;
}
```

---

# 2.3 顶部标题区字段

## 展示字段来源
- 页面标题：固定文案 `CEO参阅`
- 日期：`date`
- 最近更新时间：`generatedAt`

## 按钮交互
- `重新生成` -> `POST /api/ceo-brief/generate`
- `设置` -> 跳转设置页

## 展示建议
- 日期和更新时间放在标题下方或右侧
- 重新生成时按钮进入 loading 状态

---

# 2.4 目标信息模块字段

## 数据源
`targetUpdates: TargetUpdateItem[]`

## 字段结构建议
```ts
interface TargetUpdateItem {
  id: string;
  title: string;
  summary: string;
  matchedTargets: string[];
  source: string;
  publishedAt: string;
  relevanceReason: string;
}
```

## 页面展示字段
每条卡片展示：
- `title`
- `summary`
- `matchedTargets`
- `source`
- `publishedAt`
- `relevanceReason`

## 前端处理建议
- `matchedTargets` 以 tag 形式展示
- `publishedAt` 前端格式化显示
- 默认展示前 3~5 条

## 空状态
当 `targetUpdates.length === 0` 时显示：
- `今天还没有命中目标对象的重点动态。`
- 可附文案：`你可以去设置页调整关注目标。`

---

# 2.5 产经信息模块字段

## 数据源
`industrialNews: IndustrialNewsItem[]`

## 字段结构建议
```ts
interface IndustrialNewsItem {
  id: string;
  title: string;
  summary: string;
  source: string;
  publishedAt: string;
  importanceReason: string;
}
```

## 页面展示字段
每条卡片展示：
- `title`
- `summary`
- `source`
- `publishedAt`
- `importanceReason`

## 前端处理建议
- 第一条可以高亮为“今日重点”
- 其余用普通列表卡片展示

## 空状态
当 `industrialNews.length === 0` 时显示：
- `今天暂未整理出重点产经信息。`

---

# 2.6 今日代办模块字段

## 数据源
`todoItems: TodoItem[]`

## 字段结构建议
```ts
interface TodoItem {
  id: string;
  content: string;
  priority: 'high' | 'medium' | 'low';
  reason?: string;
}
```

## 页面展示字段
每条待办展示：
- `content`
- `priority`
- `reason`（可选）

## 前端处理建议
- `priority` 用标签颜色区分
- 不做复杂勾选逻辑，先做阅读型待办卡片

## 空状态
当 `todoItems.length === 0` 时显示：
- `今天暂无新增待办建议。`

---

# 2.7 天气情况模块字段

## 数据源
`weather: WeatherInfo | null`

## 字段结构建议
```ts
interface WeatherInfo {
  location: string;
  condition: string;
  temperatureMin: number;
  temperatureMax: number;
  advice: string;
}
```

## 页面展示字段
- `location`
- `condition`
- `temperatureMin`
- `temperatureMax`
- `advice`

## 前端处理建议
- 用简洁小卡片展示
- 温度合并显示为区间

## 空状态
当 `weather == null` 时显示：
- `今日天气信息暂不可用。`

---

# 三、设置页字段映射

# 3.1 设置页接口

## 目标设置
- `GET /api/ceo-brief/settings/targets`
- `PUT /api/ceo-brief/settings/targets`

## Prompt 设置
- `GET /api/ceo-brief/settings/prompts`
- `PUT /api/ceo-brief/settings/prompts`
- `POST /api/ceo-brief/settings/prompts/reset`

---

# 3.2 目标设置字段

## 接口结构
```ts
interface TargetSettingsResponse {
  companies: string[];
  industries: string[];
  keywords: string[];
  regions: string[];
  updatedAt: string;
}
```

## 表单项映射
- 目标企业 -> `companies`
- 目标行业 -> `industries`
- 目标关键词 -> `keywords`
- 关注地区 -> `regions`

## 表单交互建议
- 多值标签输入
- 可新增 / 删除
- 保存后 toast 提示成功

---

# 3.3 Prompt 设置字段

## 接口结构
```ts
interface PromptSettingsResponse {
  newsFilterPrompt: string;
  newsSummaryPrompt: string;
  todoPrompt: string;
  updatedAt: string;
}
```

## 表单项映射
- 新闻筛选 Prompt -> `newsFilterPrompt`
- 新闻摘要 Prompt -> `newsSummaryPrompt`
- 今日代办 Prompt -> `todoPrompt`

## 表单交互建议
- 多行文本框
- 有默认说明
- 保存后 toast 提示
- 恢复默认后需要同步刷新表单值

---

# 四、状态处理建议

# 4.1 首页状态

## 初始加载
- `loading = true`
- 展示 skeleton

## 成功
- `loading = false`
- 正常渲染 4 个模块

## 部分成功
当 `status === 'partial_success'`：
- 页面正常展示
- 某些模块走空状态或错误提示

## 失败
当整页失败：
- 展示整页错误态
- 提供重试按钮

---

# 4.2 设置页状态

## 初始加载
- 获取目标设置
- 获取 Prompt 设置
- 表单进入 loading 状态

## 保存中
- 保存按钮 disabled
- 按钮显示 loading

## 保存成功
- toast：`保存成功`

## 保存失败
- toast：`保存失败，请稍后重试`

---

# 五、前端类型建议

建议统一定义：
```ts
type BriefStatus = 'success' | 'partial_success' | 'empty' | 'failed';
```

```ts
interface BriefTodayResponse {
  date: string;
  generatedAt: string;
  status: BriefStatus;
  industrialNews: IndustrialNewsItem[];
  targetUpdates: TargetUpdateItem[];
  todoItems: TodoItem[];
  weather: WeatherInfo | null;
}
```

---

# 六、联调顺序建议

## 第一阶段
- 先联调 `GET /today`
- 把首页四块内容渲染出来

## 第二阶段
- 联调 `POST /generate`
- 实现重新生成按钮

## 第三阶段
- 联调目标设置读写
- 联调 Prompt 设置读写
- 联调恢复默认

## 第四阶段
- 补齐 loading / empty / error
- 处理边界情况

---

# 七、前端实现注意事项

- 不要假设某一模块一定有数据
- 所有数组字段都应有空数组兜底
- 时间字段统一做格式化
- Prompt 设置保存后，前端应提示“下次生成生效”
- 目标设置保存后，不必自动重跑首页，避免不必要复杂度

---

# 八、给 QA 的重点验收点

- 四个模块是否都能独立展示/空状态/报错状态
- 设置页保存后是否真的生效
- 恢复默认是否覆盖当前表单值
- 手动重新生成按钮是否有 loading 和结果反馈
- `partial_success` 时页面是否仍然可用
