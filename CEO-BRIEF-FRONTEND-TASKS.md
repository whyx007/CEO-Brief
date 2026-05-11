# CEO参阅 - 前端开工任务单

## 目标
快速做出 CEO参阅首页与设置页，保证前后端可并行开发。

## 一、前端页面

### 1. CEO参阅首页
页面模块：
- 顶部标题区
- 产经信息卡片区
- 目标信息卡片区
- 今日代办卡片区
- 天气情况卡片区
- 刷新按钮 / 重新生成按钮

### 2. 设置页面
页面模块：
- 目标设置表单
- Prompt 设置表单
- 保存按钮
- 恢复默认按钮

---

## 二、组件拆分建议

### 首页组件
- `BriefHeader`
- `IndustrialNewsCard`
- `TargetUpdatesCard`
- `TodoItemsCard`
- `WeatherCard`
- `EmptyState`
- `LoadingState`

### 设置页组件
- `TargetSettingsForm`
- `PromptSettingsForm`
- `SaveBar`

---

## 三、前端联调接口

首页：
- `GET /api/ceo-brief/today`
- `POST /api/ceo-brief/generate`

设置：
- `GET /api/ceo-brief/settings/targets`
- `PUT /api/ceo-brief/settings/targets`
- `GET /api/ceo-brief/settings/prompts`
- `PUT /api/ceo-brief/settings/prompts`
- `POST /api/ceo-brief/settings/prompts/reset`

---

## 四、前端展示要求

### 产经信息
每条新闻展示：
- 标题
- 摘要
- 来源
- 时间
- 关注理由

### 目标信息
每条动态展示：
- 标题
- 摘要
- 命中的目标对象
- 来源
- 时间

### 今日代办
每条待办展示：
- 内容
- 优先级
- 触发原因（可选）

### 天气情况
展示：
- 天气状态
- 温度
- 建议提示

---

## 五、前端优先级

### P0
- 首页静态结构
- 设置页静态结构
- 接口联调
- 空状态与 loading

### P1
- 重新生成交互
- 表单校验
- 恢复默认交互

### P2
- 视觉优化
- 详情展开
- 来源外链

---

## 六、前端注意事项
- 页面必须支持无数据空状态
- 设置保存后要有明确反馈
- 首页四个板块要独立容错，单个模块失败不应导致全页崩掉
- 先保证可用，再做复杂视觉
