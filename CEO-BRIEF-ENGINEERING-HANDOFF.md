# CEO参阅开发启动包（发工程师版）

各位，先不要再扩范围，直接启动 **CEO参阅** 第一版开发。

## 本轮目标
做出一个可演示、可联调的 CEO参阅 MVP，覆盖 4 个首页板块：
1. 产经信息
2. 目标信息
3. 今日代办
4. 天气情况

并提供 1 个设置页面，支持：
- 目标信息中的目标对象可设置
- 新闻内容 Prompt 可设置

---

## 本轮范围
### 要做
- CEO参阅首页
- CEO参阅设置页
- 首页数据接口
- 设置读写接口
- 手动重新生成接口
- 前后端联调

### 先不做
- 历史版本
- 审批流
- 复杂权限
- 自动订阅推送
- 复杂消息系统
- Prompt 审批和版本管理

---

## 页面要求
### 首页
模块优先级：
1. 目标信息
2. 产经信息
3. 今日代办
4. 天气情况

### 设置页
分两块：
- 目标设置
- Prompt 设置

---

## 后端先做什么
请先完成这些接口：
- `GET /api/ceo-brief/today`
- `POST /api/ceo-brief/generate`
- `GET /api/ceo-brief/settings/targets`
- `PUT /api/ceo-brief/settings/targets`
- `GET /api/ceo-brief/settings/prompts`
- `PUT /api/ceo-brief/settings/prompts`
- `POST /api/ceo-brief/settings/prompts/reset`

数据模型参考：
- `ceo_brief_run`
- `ceo_brief_target_settings`
- `ceo_brief_prompt_settings`

要求：
- 模块级失败不拖垮整页
- 支持 `partial_success`
- 记录 prompt_snapshot
- 天气先轻量接入

---

## 前端先做什么
请先完成：
- CEO参阅首页骨架
- 设置页骨架
- 首页 4 个模块卡片
- 设置页双分区表单
- loading / empty / error 状态

联调顺序：
1. 先接 `GET /today`
2. 再接设置接口
3. 再接 `reset`
4. 最后接 `generate`

---

## UI/UX 先交什么
请先交：
- 首页线框结构
- 设置页线框结构
- 四个模块优先级与布局
- 空状态 / loading / error 说明

布局建议：
- 左侧主列：目标信息 + 产经信息
- 右侧侧栏：今日代办 + 天气情况

---

## QA 关注点
- 四个模块是否都能展示
- 单模块失败时整页是否仍可用
- 设置保存后是否生效
- 恢复默认是否正常
- 重新生成是否有反馈

---

## 排期（5个工作日）
### Day 1
- 范围冻结
- UI/UX 出线框
- 前后端搭骨架

### Day 2
- 后端接口初版
- 前端静态页

### Day 3
- 首轮联调

### Day 4
- 生成链路打通
- 状态与边界收口

### Day 5
- 回归、修复、演示收口

---

## 文档索引
实现时请同步参考以下文件：
- `ceo-brief/CEO-BRIEF-FEATURE-SPEC.md`
- `ceo-brief/CEO-BRIEF-UIUX-SPEC.md`
- `ceo-brief/CEO-BRIEF-BACKEND-API-DATA-MODEL.md`
- `ceo-brief/CEO-BRIEF-FRONTEND-FIELDS-INTEGRATION.md`
- `ceo-brief/CEO-BRIEF-DELIVERY-PLAN.md`

---

## 交付标准
本轮最低交付标准：
- 首页能展示 4 个板块
- 设置页可保存目标设置与 Prompt 设置
- 支持手动重新生成
- 前后端完成首轮联调
- 页面达到可演示状态
