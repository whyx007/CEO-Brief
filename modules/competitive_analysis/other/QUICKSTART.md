# 断点续传功能 - 快速开始指南

## 功能说明

程序现在支持断点续传功能，可以在任务中断后继续执行，避免重复工作。

## 已完成的工作

1. **checkpoint_manager.py** - Checkpoint管理器
   - 保存和加载任务执行状态
   - 跟踪任务进度
   - 询问用户是否继续之前的任务

2. **resumable_executor.py** - 可恢复执行器
   - 检查是否可以使用缓存结果
   - 保存Crew执行结果

3. **main.py** - 已集成checkpoint功能
   - 在程序启动时检查是否有未完成的任务
   - 在Crew执行完成后保存checkpoint

## 使用方法

### 正常使用（无需修改）

直接运行程序即可，checkpoint功能会自动工作：

```bash
python main.py
```

### 工作流程

#### 第一次运行（正常执行）

```
$ python main.py
🛰️ 中科天塔竞情分析半月报
... 执行任务 ...
SAVED: Checkpoint已保存: report
DONE: 任务已标记为完成
✅ 报告生成完毕！
```

#### 第二次运行（任务已完成）

```
$ python main.py
📋 发现未完成的任务
开始时间: 2026-03-13T10:33:51
最后更新: 2026-03-13T12:05:47
当前进度: 100% (9/9)
当前阶段: completed
已完成阶段: discover, talent, market, tech, bidding_funding, policy, global_tech, scoring, report

是否继续之前的任务？ [Y/n]: y
✅ 使用缓存的执行结果，跳过Crew执行
... 直接生成报告 ...
```

#### 中途中断后继续

```
第一次运行:
$ python main.py
... 执行到一半 ...
^C ⚠️ 用户中断执行

第二次运行:
$ python main.py
📋 发现未完成的任务
开始时间: 2026-03-13T10:33:51
当前进度: 0% (0/9)

是否继续之前的任务？ [Y/n]: n
🔄 将重新开始任务...
DELETED: Checkpoint已清除
... 从头执行 ...
```

## Checkpoint文件位置

Checkpoint文件保存在输出目录中：

```
output/
└── 20260313_biweekly/
    ├── checkpoint.json          ← Checkpoint文件
    ├── 天塔竞情战略半月报.md
    ├── raw_data.json
    └── ...
```

## 注意事项

### 当前版本限制

1. **只支持完整任务的缓存**: 如果任务完整执行完成，下次运行可以直接使用结果
2. **不支持中间阶段恢复**: 如果任务在中间阶段中断，需要从头重新执行
3. **checkpoint按日期隔离**: 每天的输出目录独立，checkpoint也独立

### 何时使用缓存结果

- 任务已完整执行完成
- 想要重新生成报告（使用相同的数据）
- 想要查看之前的执行结果

### 何时重新开始

- 任务中途中断
- 想要获取最新的数据
- 发现之前的结果有问题

## 手动管理Checkpoint

如果需要手动清除checkpoint：

```bash
# 删除checkpoint文件
rm output/20260313_biweekly/checkpoint.json

# 或删除整个输出目录
rm -rf output/20260313_biweekly/
```

## 故障排查

### 问题1: 提示checkpoint文件损坏

```
WARNING: 加载checkpoint失败: ...
```

解决方法：删除checkpoint文件，重新开始

```bash
rm output/*/checkpoint.json
```

### 问题2: 想要强制重新执行

在程序询问时选择"n"（不继续），或手动删除checkpoint文件。

### 问题3: 磁盘空间不足

Checkpoint文件可能较大（包含完整的执行结果）。定期清理旧的输出目录：

```bash
# 只保留最近7天的输出
find output/ -name "*_biweekly" -type d -mtime +7 -exec rm -rf {} \;
```

## 技术细节

### Checkpoint文件结构

```json
{
  "start_time": "2026-03-13T10:33:51.123456",
  "last_update": "2026-03-13T12:05:47.654321",
  "current_stage": "completed",
  "completed_stages": ["discover", "talent", "market", "tech", "bidding_funding", "policy", "global_tech", "scoring", "report"],
  "stage_data": {
    "report": {
      "timestamp": "2026-03-13T12:05:47.654321",
      "data": {
        "output": "... 完整的报告内容 ..."
      }
    }
  },
  "metadata": {}
}
```

### 任务阶段

程序包含以下9个阶段：

1. discover - 发现竞争对手
2. talent - 人才分析
3. market - 市场分析
4. tech - 技术分析
5. bidding_funding - 竞标融资分析
6. policy - 政策分析
7. global_tech - 全球技术趋势
8. scoring - 综合评分
9. report - CEO报告生成

## 总结

断点续传功能已经集成到main.py中，无需额外配置即可使用。程序会自动检测是否有未完成的任务，并询问用户是否继续。

如有问题，请查看CHECKPOINT_README.md获取更详细的文档。
