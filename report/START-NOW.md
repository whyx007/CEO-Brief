# CEO参阅 - 立即开工说明

现在开始，不再等更多方案。

## 前端立即做
1. 用 `mock/ceo-brief-today.json` 做首页
2. 用 `mock/ceo-brief-target-settings.json` 和 `mock/ceo-brief-prompt-settings.json` 做设置页
3. 完成：
   - 首页 4 个模块
   - 设置页 2 个分区
   - loading / empty / error
   - 重新生成按钮占位

## 后端立即做
1. 按 `CEO-BRIEF-BACKEND-API-DATA-MODEL.md` 建接口骨架
2. 先把 3 个 GET 接口 mock 化跑通
3. 再补 PUT / POST
4. 最后接生成逻辑

## UI/UX 立即做
1. 按 `CEO-BRIEF-UIUX-SPEC.md` 出线框或高保真说明
2. 重点先定首页布局和设置页表单层级

## 联调顺序
1. 首页 mock 联调
2. 设置页 mock 联调
3. 切真实 GET
4. 切真实 PUT/POST
5. 接 generate
