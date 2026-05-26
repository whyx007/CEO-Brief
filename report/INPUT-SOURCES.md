# CEO参阅输入源方案（Python主线）

## 当前主线
当前后端主线切换为 **Python / FastAPI**。

主服务入口：
- `app.py`

推荐运行环境：
- conda 环境：`ceo-brief-py310`

## 输入源分层
建议把 CEO参阅的输入源拆成三层：

1. **搜索聚合层**
   - SearXNG（作为开放搜索聚合入口之一）
   - 用途：拉取当天行业、公司、政策、融资、供应链相关新闻候选集

2. **结构化数据层**
   - 天气 API
   - 公司/行业内部配置
   - 后续可接数据库、企业知识库、投后事件库

3. **AI处理层**
   - LLM 摘要
   - 去重
   - 相关性排序
   - 待办生成

## 为什么接 SearXNG
SearXNG 适合当前阶段作为输入源之一，因为：
- 是元搜索，可聚合多个搜索引擎结果
- 接入简单，HTTP API 友好
- 易于做 query 模板化
- 对后续 AI 摘要链路友好

## SearXNG API 要点
参考官方文档，SearXNG 支持：
- `GET /search`
- `POST /search`
- `GET /`
- `POST /`

常用参数：
- `q`: 查询词
- `format=json`: 返回 JSON
- `categories`: 搜索分类
- `engines`: 指定引擎
- `language`: 语言
- `time_range=day|month|year`: 时间范围
- `safesearch`

示例：

```text
GET https://<searxng-instance>/search?q=宁德时代+融资&format=json&time_range=day
```

## 在 CEO参阅中的建议接法
建议把 SearXNG 作为 `news_candidates` 的来源之一，而不是直接作为最终结果。

推荐流水线：
1. 根据 target settings 生成 query 列表
2. 调用 SearXNG 获取候选新闻
3. 做 URL 去重 / 标题去重 / 时间过滤
4. 抽正文或摘要
5. 交给 LLM 做：
   - 重要性判断
   - CEO视角摘要
   - 代办建议生成
6. 落库 / 落 JSON 结果

## 建议 Query 模板
围绕以下对象生成组合查询：
- companies
- industries
- keywords
- regions

示例模板：
- `{company} 最新进展`
- `{company} 融资 OR 合作 OR 订单`
- `{industry} 政策`
- `{industry} 供应链`
- `{region} {industry}`

## 下一步代码建议
建议新增 Python 模块：
- `services/searxng_client.py`
- `services/news_pipeline.py`
- `services/llm_pipeline.py`
- `services/weather_client.py`

并新增配置：
- `SEARXNG_BASE_URL`
- `SEARXNG_TIMEOUT_SECONDS`
- `NEWS_TOP_K`
- `LLM_PROVIDER`

## 注意事项
- 公共 SearXNG 实例可能禁用 JSON format，需确认实例能力
- 优先自建或固定可信实例
- 要做超时、重试、限流
- 不要把搜索结果直接作为最终 CEO参阅输出，必须经过筛选与摘要
