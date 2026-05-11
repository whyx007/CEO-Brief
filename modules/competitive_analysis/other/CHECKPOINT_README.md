# 断点续传功能使用说明

## 功能概述

为了解决程序运行过程中可能因为各种原因（API超时、网络中断、用户中断等）导致的任务中断问题，我们添加了断点续传功能。

## 核心组件

### 1. `checkpoint_manager.py` - Checkpoint管理器

负责管理任务执行状态和断点数据：

- **保存checkpoint**: 在关键阶段完成后保存执行结果
- **加载checkpoint**: 程序启动时检查是否有未完成的任务
- **进度跟踪**: 记录任务执行进度和已完成的阶段
- **用户交互**: 询问用户是继续还是重新开始

### 2. `resumable_executor.py` - 可恢复执行器

提供任务执行和结果缓存功能：

- **检查缓存**: 判断是否可以使用之前的执行结果
- **保存结果**: 将Crew执行结果保存到checkpoint

### 3. Checkpoint文件结构

Checkpoint文件保存在输出目录中（`output/<日期>_biweekly/checkpoint.json`），包含以下信息：

```json
{
  "start_time": "2026-03-13T10:33:51.123456",
  "last_update": "2026-03-13T12:05:47.654321",
  "current_stage": "report",
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

## 使用方法

### 方法1: 修改现有main.py（推荐）

在`main.py`的开头添加checkpoint检查逻辑：

```python
from checkpoint_manager import check_and_prompt_resume
from resumable_executor import should_skip_execution, save_crew_result

def main():
    # ... 原有的欢迎信息 ...

    # 添加checkpoint检查
    checkpoint_manager, should_resume = check_and_prompt_resume(OUTPUT_DIR)

    # 检查是否可以跳过执行
    skip_execution, cached_result = should_skip_execution(checkpoint_manager)

    if skip_execution and cached_result:
        console.print("[green]✅ 使用缓存的执行结果[/green]")
        raw_output = cached_result
        # 跳转到结果解析部分
        goto_result_parsing = True
    else:
        goto_result_parsing = False

    # 如果不跳过，执行正常流程
    if not goto_result_parsing:
        # ... API验证 ...
        # ... Crew执行 ...

        try:
            result = crew.kickoff()
            # 保存checkpoint
            save_crew_result(checkpoint_manager, result)
        except Exception as e:
            # 错误处理
            pass

    # ... 结果解析和报告生成 ...
```

### 方法2: 使用独立的入口脚本

运行`main_resumable.py`而不是`main.py`：

```bash
python main_resumable.py
```

### 方法3: 手动管理checkpoint

如果你想更精细地控制checkpoint，可以直接使用CheckpointManager：

```python
from checkpoint_manager import CheckpointManager

# 创建管理器
manager = CheckpointManager("output/20260313_biweekly")

# 加载checkpoint
checkpoint = manager.load_checkpoint()

if checkpoint:
    print(f"发现未完成的任务，进度: {manager.get_progress_info()}")

    # 获取某个阶段的数据
    discover_data = manager.get_stage_data("discover")

    # 保存新的checkpoint
    manager.save_checkpoint(
        stage="talent",
        data={"output": "人才分析结果..."}
    )

    # 标记为完成
    manager.mark_completed()

    # 清除checkpoint
    manager.clear_checkpoint()
```

## 工作流程

### 正常执行流程

1. 用户运行程序
2. 程序检查是否有checkpoint文件
3. 如果没有，从头开始执行
4. 执行完成后保存checkpoint并标记为完成

### 中断后继续流程

1. 用户运行程序
2. 程序检查到有未完成的checkpoint
3. 显示任务进度信息
4. 询问用户：是继续还是重新开始？
5. 如果选择继续：
   - 检查是否有完整的执行结果
   - 如果有，直接使用缓存结果
   - 如果没有，从头重新执行（当前版本）
6. 如果选择重新开始：
   - 清除checkpoint
   - 从头开始执行

## 注意事项

### 当前版本限制

由于CrewAI框架的限制，当前版本的断点续传功能有以下限制：

1. **只支持完整任务的缓存**: 如果任务完整执行完成，下次运行可以直接使用结果
2. **不支持中间阶段恢复**: 如果任务在中间阶段中断，需要从头重新执行
3. **checkpoint按日期隔离**: 每天的输出目录独立，checkpoint也独立

### 未来改进方向

1. **细粒度checkpoint**: 在每个Agent任务完成后保存checkpoint
2. **增量执行**: 只执行未完成的任务，跳过已完成的任务
3. **多版本管理**: 支持保存多个checkpoint版本
4. **自动恢复**: 检测到异常时自动保存checkpoint

## 示例场景

### 场景1: 任务完整执行完成

```
第一次运行:
$ python main.py
🛰️ 中科天塔竞情分析半月报
... 执行任务 ...
✅ 报告生成完毕！
💾 执行结果已保存到checkpoint

第二次运行:
$ python main.py
📋 发现未完成的任务
开始时间: 2026-03-13T10:33:51
当前进度: 100% (9/9)
当前阶段: completed

是否继续之前的任务？ [Y/n]: y
✅ 使用缓存的执行结果
... 直接生成报告 ...
```

### 场景2: 任务中途中断

```
第一次运行:
$ python main.py
🛰️ 中科天塔竞情分析半月报
... 执行到一半 ...
^C ⚠️ 用户中断执行

第二次运行:
$ python main.py
📋 发现未完成的任务
开始时间: 2026-03-13T10:33:51
当前进度: 0% (0/9)
当前阶段: discover

是否继续之前的任务？ [Y/n]: n
🔄 将重新开始任务...
... 从头执行 ...
```

### 场景3: 选择重新开始

```
$ python main.py
📋 发现未完成的任务
开始时间: 2026-03-13T10:33:51
当前进度: 100% (9/9)
当前阶段: completed

是否继续之前的任务？ [Y/n]: n
🔄 将重新开始任务...
🗑️ Checkpoint已清除
... 从头执行 ...
```

## 故障排查

### 问题1: Checkpoint文件损坏

如果checkpoint文件损坏，程序会自动忽略并从头开始：

```
⚠️ 加载checkpoint失败: ...
```

解决方法：手动删除checkpoint文件

```bash
rm output/20260313_biweekly/checkpoint.json
```

### 问题2: 缓存结果不正确

如果发现缓存的结果不正确，可以选择重新开始，或手动删除checkpoint文件。

### 问题3: 磁盘空间不足

Checkpoint文件可能会占用较多空间（包含完整的执行结果）。定期清理旧的输出目录：

```bash
# 只保留最近7天的输出
find output/ -name "*_biweekly" -type d -mtime +7 -exec rm -rf {} \;
```

## API参考

### CheckpointManager

```python
class CheckpointManager:
    def __init__(self, output_dir: str)
    def load_checkpoint(self) -> Optional[Dict[str, Any]]
    def save_checkpoint(self, stage: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None)
    def get_stage_data(self, stage: str) -> Optional[Dict[str, Any]]
    def get_next_stage(self) -> Optional[str]
    def is_completed(self) -> bool
    def mark_completed(self)
    def clear_checkpoint(self)
    def get_progress_info(self) -> Dict[str, Any]
    def prompt_resume_or_restart(self) -> bool
```

### 辅助函数

```python
def check_and_prompt_resume(output_dir: str) -> tuple[CheckpointManager, bool]
def should_skip_execution(checkpoint_manager: CheckpointManager) -> tuple[bool, Optional[str]]
def save_crew_result(checkpoint_manager: CheckpointManager, result: Any)
```

## 总结

断点续传功能可以有效避免因为各种原因导致的任务中断带来的时间浪费。虽然当前版本只支持完整任务的缓存，但已经可以在大多数场景下提供帮助。

如有问题或建议，请查看代码注释或联系开发团队。
