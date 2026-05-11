# CEO参阅 Mock 数据

前后端可以先直接使用以下 mock 文件联调：

- `ceo-brief-today.json`
- `ceo-brief-target-settings.json`
- `ceo-brief-prompt-settings.json`

## 建议联调顺序
1. 首页先用 `ceo-brief-today.json`
2. 设置页先用 target/prompt settings 两个 mock
3. 等后端接口 ready 后再切真实接口

## 建议接口对照
- `GET /api/ceo-brief/today` -> `ceo-brief-today.json`
- `GET /api/ceo-brief/settings/targets` -> `ceo-brief-target-settings.json`
- `GET /api/ceo-brief/settings/prompts` -> `ceo-brief-prompt-settings.json`
