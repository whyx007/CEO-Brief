# 问题分析与解决方案

## 问题描述

20260313_biweekly/W11_20260313.pdf 输出内容有问题，显示"格式解析异常兜底生成"，但 crew_raw_output.txt 中包含完整的原始信息。

## 根本原因

1. **crew输出被截断**：crew_raw_output.txt 文件中只有主报告的开始标记 `=== 主报告开始 ===`，但没有结束标记 `=== 主报告结束 ===`。文件在汇总备份表格中间被截断。

2. **正则表达式匹配失败**：main.py 中的正则表达式要求同时匹配开始和结束标记：
   ```python
   main_report_match = re.search(r"=== 主报告开始 ===\s*(.*?)\s*=== 主报告结束 ===", raw_output, re.S)
   ```
   由于没有结束标记，匹配失败，导致 `extracted_ceo_md` 为 None。

3. **兜底逻辑触发**：当无法提取报告内容时，`render_ceo_onepager()` 函数的兜底逻辑被触发，生成了"格式解析异常兜底生成"的提示。

## 解决方案

### 1. 临时修复（已完成）

创建了 `fix_report.py` 脚本，直接从 crew_raw_output.txt 提取主报告内容并生成PDF：

```python
def extract_main_report(raw_output: str) -> str:
    """从原始输出中提取主报告"""
    # 尝试匹配完整的主报告（有结束标记）
    main_report_match = re.search(r"===\s*主报告开始\s*===\s*(.*?)\s*===\s*主报告结束\s*===", raw_output, re.S)

    if main_report_match:
        return main_report_match.group(1).strip()

    # 如果没有找到结束标记，尝试从开始标记到文件末尾
    main_report_match = re.search(r"===\s*主报告开始\s*===\s*(.*)", raw_output, re.S)
    if main_report_match:
        content = main_report_match.group(1).strip()
        # 移除可能的其他备份文件标记
        content = re.sub(r"===\s*商业航天测运控备份文件开始\s*===.*", "", content, flags=re.S)
        content = re.sub(r"===\s*激光通讯终端备份文件开始\s*===.*", "", content, flags=re.S)
        content = re.sub(r"===\s*汇总备份文件开始\s*===.*", "", content, flags=re.S)
        return content.strip()

    return None
```

运行结果：
- 成功提取主报告（11581字符）
- 生成的PDF文件大小从35KB增加到197KB
- 报告内容完整，包含所有章节

### 2. 永久修复（已完成）

修改了 main.py 中的正则表达式匹配逻辑，增加了对截断情况的处理：

```python
# 使用更宽松的正则表达式来匹配分隔符（允许额外的空白字符）
main_report_match = re.search(r"===\s*主报告开始\s*===\s*(.*?)\s*===\s*主报告结束\s*===", raw_output, re.S)

if main_report_match:
    extracted_ceo_md = main_report_match.group(1).strip()
elif re.search(r"===\s*主报告开始\s*===", raw_output):
    # 如果找到开始标记但没有结束标记，提取从开始到文件末尾的内容
    main_report_match = re.search(r"===\s*主报告开始\s*===\s*(.*)", raw_output, re.S)
    if main_report_match:
        content = main_report_match.group(1).strip()
        # 移除可能的其他备份文件标记
        content = re.sub(r"===\s*商业航天测运控备份文件开始\s*===.*", "", content, flags=re.S)
        content = re.sub(r"===\s*激光通讯终端备份文件开始\s*===.*", "", content, flags=re.S)
        content = re.sub(r"===\s*汇总备份文件开始\s*===.*", "", content, flags=re.S)
        extracted_ceo_md = content.strip()
```

这样即使crew输出被截断，也能正确提取主报告内容。

## 为什么会被截断？

可能的原因：
1. **LLM输出长度限制**：DeepSeek模型可能有输出token限制
2. **CrewAI框架限制**：CrewAI可能对单个任务的输出长度有限制
3. **网络传输问题**：API调用过程中可能发生超时或截断

## 建议

1. **监控输出长度**：在main.py中添加日志，记录crew输出的长度和是否完整
2. **分段生成**：考虑将报告生成拆分为多个任务，每个任务生成一部分内容
3. **增加重试机制**：如果检测到输出被截断，自动重试生成
4. **优化prompt**：减少不必要的输出，确保关键内容优先生成

## 验证

运行 `python fix_report.py` 后：
- ✅ 天塔竞情战略半月报.md 内容完整（11581字符）
- ✅ W11_20260313.pdf 生成成功（197KB）
- ✅ PDF包含完整的报告内容，包括：
  - 本期重点信号
  - 1. 外部环境（政策法规、行业发展动态）
  - 2. 竞情态势（融资与订单、经营与组织动向、人才动向）
  - 3. 技术前沿（关键技术动态、前沿方向观察）
  - 4. 预警与建议
  - 参考文献与信息来源
