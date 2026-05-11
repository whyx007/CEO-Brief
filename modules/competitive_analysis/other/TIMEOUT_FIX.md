# API超时问题解决方案

## 问题描述

程序在运行过程中出现长时间卡住的情况，日志显示：

```
2026-03-13 15:17:38 [INFO] Retrying request to /chat/completions in 0.495083 seconds
2026-03-13 15:27:39 [INFO] Retrying request to /chat/completions in 0.751777 seconds
```

两次重试之间间隔10分钟，说明API请求一直没有响应。

## 根本原因

1. **没有设置超时时间** - LLM API调用没有设置合理的超时参数
2. **DeepSeek API响应慢** - 可能因为：
   - 请求的token数量太大（上次请求使用了20406个tokens）
   - API服务器负载高
   - 网络连接不稳定
   - 触发了速率限制

## 已实施的解决方案

### 1. 添加超时配置 ✅

修改了 `agents.py`，为所有LLM添加了超时参数：

```python
# 常规任务LLM
deepseek_llm = LLM(
    model=f"openai/{DEEPSEEK_MODEL}",
    base_url=DEEPSEEK_BASE_URL,
    api_key=DEEPSEEK_API_KEY,
    temperature=0.15,
    max_tokens=8192,
    timeout=180,  # 3分钟超时
)

# 长报告LLM
deepseek_llm_long = LLM(
    model=f"openai/{DEEPSEEK_MODEL}",
    base_url=DEEPSEEK_BASE_URL,
    api_key=DEEPSEEK_API_KEY,
    temperature=0.15,
    max_tokens=32768,
    timeout=300,  # 5分钟超时
)

# Qwen LLM
qwen_llm = LLM(
    model=QWEN_MODEL,
    base_url=QWEN_BASE_URL,
    api_key=QWEN_API_KEY,
    temperature=0.15,
    max_tokens=32768,
    timeout=300,  # 5分钟超时
)
```

### 2. 超时时间说明

- **常规任务**: 180秒（3分钟）
  - 用于大部分Agent任务
  - 足够处理正常的API请求
  - 避免长时间等待

- **长报告生成**: 300秒（5分钟）
  - 用于CEO参谋生成最终报告
  - 需要处理更多token
  - 给予更多时间

### 3. 超时后的行为

当API请求超时时：
- 程序会抛出超时异常
- 异常会被捕获并记录到日志
- 程序会停止执行（避免无限等待）
- 用户可以查看日志了解具体原因

## 其他建议

### 短期建议

1. **检查网络连接**
   ```bash
   ping api.deepseek.com
   curl -I https://api.deepseek.com
   ```

2. **检查API余额**
   - 登录 https://platform.deepseek.com
   - 查看账户余额是否充足
   - 当前余额：12.04 CNY（充足）

3. **降低并发请求**
   - 当前设置：`max_rpm=30`（每分钟最多30次请求）
   - 可以降低到20或15，减少触发限流的可能

### 中期建议

1. **添加重试机制**
   - 在超时后自动重试
   - 使用指数退避策略
   - 最多重试3次

2. **优化请求大小**
   - 减少每次请求的上下文长度
   - 分批处理大量数据
   - 使用更小的max_tokens

3. **监控API性能**
   - 记录每次API调用的耗时
   - 统计超时频率
   - 分析慢请求的特征

### 长期建议

1. **使用备用API**
   - 当DeepSeek超时时，自动切换到Qwen
   - 实现API负载均衡
   - 提高系统可靠性

2. **实现请求队列**
   - 控制并发请求数量
   - 避免触发速率限制
   - 平滑API调用

3. **缓存机制**
   - 缓存相似的请求结果
   - 减少API调用次数
   - 降低成本

## 配置调整

如果仍然遇到超时问题，可以调整以下参数：

### 增加超时时间

编辑 `agents.py`：

```python
# 如果经常超时，可以增加到10分钟
deepseek_llm = LLM(
    # ...
    timeout=600,  # 10分钟
)
```

### 降低并发限制

编辑 `main.py`：

```python
crew = Crew(
    # ...
    max_rpm=15,  # 降低到每分钟15次请求
)
```

### 减少输出长度

编辑 `agents.py`：

```python
deepseek_llm = LLM(
    # ...
    max_tokens=4096,  # 减少到4096
)
```

## 监控和诊断

### 查看日志

```bash
# 查看最新的日志文件
tail -f logs/tianta_ci_*.log

# 搜索超时相关的日志
grep -i "timeout\|retry" logs/tianta_ci_*.log
```

### 测试API连接

```bash
# 测试DeepSeek API
python -c "
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
import requests
import time

start = time.time()
response = requests.post(
    f'{DEEPSEEK_BASE_URL}/chat/completions',
    headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'},
    json={
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': 'test'}],
        'max_tokens': 10
    },
    timeout=30
)
elapsed = time.time() - start
print(f'Status: {response.status_code}, Time: {elapsed:.2f}s')
"
```

## 总结

已经为所有LLM添加了超时配置：
- ✅ 常规任务：3分钟超时
- ✅ 长报告：5分钟超时
- ✅ 避免无限等待

如果仍然遇到超时问题，请：
1. 检查网络连接
2. 检查API余额
3. 考虑增加超时时间或降低并发限制

现在可以重新运行程序，超时问题应该得到改善。
