# API配额查询功能使用说明

## 功能概述

程序现在支持在执行任务前查询各个API的剩余配额和余额，帮助你提前了解是否有足够的额度来完成任务。

## 支持的API

### 1. DeepSeek API - 余额查询
- **查询内容**: 账户余额（CNY）
- **查询端点**: `https://api.deepseek.com/user/balance`
- **测试结果**: ✅ 成功（余额: 12.04 CNY）

### 2. Serper API - 配额查询
- **查询内容**: 剩余搜索次数
- **查询端点**: `https://google.serper.dev/account`
- **测试结果**: ✅ 成功（剩余: 0次）

### 3. 博查 Bocha API - 配额查询
- **查询内容**: 剩余搜索次数/总配额
- **查询端点**: `https://api.bochaai.com/v1/user/quota`
- **测试结果**: ⚠️ 404（API可能不提供此端点）

## 工作流程

### 1. 程序启动时自动查询

运行程序时，会自动执行以下步骤：

```
1. API可用性验证
   ├─ DeepSeek API验证
   ├─ Qwen API验证（可选）
   ├─ 博查 API验证
   └─ Serper API验证

2. API配额查询 ← 新增
   ├─ 查询DeepSeek余额
   ├─ 查询博查配额
   ├─ 查询Serper配额
   └─ 显示配额表格

3. 配额充足性检查
   ├─ 对比预估消耗
   ├─ 判断是否充足
   └─ 询问是否继续（如果不足）

4. 执行任务
```

### 2. 配额表格示例

```
┌─────────────────────────────────────────────────────────┐
│                    API配额状态                          │
├───────────┬────────┬──────────────┬──────────┬─────────┤
│ API       │ 状态   │ 剩余/余额    │ 预估消耗 │ 是否充足│
├───────────┼────────┼──────────────┼──────────┼─────────┤
│ DeepSeek  │ 可用   │ 12.04 CNY    │ ~1.50 CNY│ OK      │
│ 博查 Bocha│ 未知   │ -            │ -        │ -       │
│ Serper    │ 可用   │ 0 次         │ ~35 次   │ X       │
└───────────┴────────┴──────────────┴──────────┴─────────┘
```

### 3. 配额不足时的处理

如果检测到配额可能不足，程序会：

1. 显示警告信息
2. 列出不足的API
3. 询问是否继续执行

```
⚠️ 警告：部分API配额可能不足
以下API配额可能不足以完成本次任务：
  • Serper (剩余: 0, 需要: ~35)

注意：这只是基于历史数据的估算，实际消耗可能有所不同

是否继续执行任务？ [Y/n]:
```

## 任务成本估算

基于历史数据，程序会估算完成一次完整任务所需的资源：

### LLM (DeepSeek)
- **调用次数**: 100-200次（平均150次）
- **Token消耗**: 500k-1M tokens（平均750k）
- **预估成本**: ¥1.0-2.5（平均¥1.5）

### 搜索API
- **总调用次数**: 50-100次（平均75次）
- **博查**: ~40次
- **Serper**: ~35次

## 使用方法

### 自动使用（推荐）

无需任何配置，直接运行程序即可：

```bash
python main.py
```

程序会自动：
1. 验证API可用性
2. 查询API配额
3. 显示配额表格
4. 检查是否充足
5. 询问是否继续（如果不足）

### 手动查询配额

如果只想查询配额而不执行任务：

```bash
python test_quota.py
```

或在Python代码中：

```python
from api_quota_checker import check_all_quotas, display_quota_table

# 查询所有配额
quota_info = check_all_quotas()

# 显示表格
display_quota_table(quota_info)

# 检查是否充足
from api_quota_checker import check_sufficient_quota
sufficient, insufficient_list = check_sufficient_quota(quota_info)

if not sufficient:
    print("配额不足:", insufficient_list)
```

## 注意事项

### 1. API端点可能不存在

某些API可能不提供配额查询端点，这是正常的：
- **博查**: 404错误（可能不支持）
- 如果查询失败，程序会继续执行，只是无法显示准确的配额信息

### 2. 估算值仅供参考

- 预估消耗基于历史数据
- 实际消耗可能因任务复杂度而异
- 建议保留一定余量

### 3. 配额查询可能失败

如果配额查询失败：
- 程序会显示"未知"状态
- 不会阻止任务执行
- 建议手动检查API账户

## 配额查询API文档

### DeepSeek余额查询

```bash
curl -X GET https://api.deepseek.com/user/balance \
  -H "Authorization: Bearer YOUR_API_KEY"
```

响应示例：
```json
{
  "total_balance": "12.04",
  "currency": "CNY"
}
```

### Serper配额查询

```bash
curl -X GET https://google.serper.dev/account \
  -H "X-API-KEY: YOUR_API_KEY"
```

响应示例：
```json
{
  "credits": 500
}
```

### 博查配额查询

```bash
curl -X GET https://api.bochaai.com/v1/user/quota \
  -H "Authorization: Bearer YOUR_API_KEY"
```

注意：此端点可能不存在（返回404）

## 故障排查

### 问题1: 配额查询失败

```
WARNING: DeepSeek余额查询失败: HTTP 401
```

**原因**: API Key无效或已过期

**解决方法**:
1. 检查.env文件中的API Key
2. 登录API平台确认Key是否有效
3. 重新生成API Key

### 问题2: 显示"未知"状态

```
│ 博查 Bocha│ 未知   │ -            │ -        │ -       │
```

**原因**: API不提供配额查询端点，或查询失败

**解决方法**:
1. 手动登录API平台查看配额
2. 程序会继续执行，不影响功能

### 问题3: 配额不足警告

```
⚠️ 警告：部分API配额可能不足
```

**解决方法**:
1. 充值API账户
2. 选择继续执行（可能会失败）
3. 使用备用API

## 测试结果

根据实际测试：

```
✅ DeepSeek余额查询: 成功
   - 余额: 12.04 CNY
   - 预估消耗: ~1.5 CNY
   - 状态: 充足

⚠️ 博查配额查询: 失败（404）
   - 可能API不支持此端点
   - 建议手动查看

✅ Serper配额查询: 成功
   - 剩余: 0次
   - 预估消耗: ~35次
   - 状态: 不足
```

## 总结

API配额查询功能已经集成到main.py中，可以帮助你：

1. ✅ 提前了解API配额状态
2. ✅ 避免因配额不足导致任务失败
3. ✅ 合理规划API使用
4. ✅ 及时充值账户

如有问题，请查看日志文件或联系开发团队。
