"""
可恢复的任务执行器 - 支持断点续传

由于CrewAI的限制，我们采用简化策略：
1. 在Crew执行前检查checkpoint
2. 如果有完整的checkpoint，直接使用结果
3. 如果没有或不完整，重新执行整个Crew
4. 在Crew执行完成后保存完整结果到checkpoint
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from rich.console import Console

from checkpoint_manager import CheckpointManager

console = Console()


def should_skip_execution(checkpoint_manager: CheckpointManager) -> tuple[bool, Optional[str]]:
    """
    检查是否应该跳过执行（使用缓存的结果）

    Args:
        checkpoint_manager: checkpoint管理器

    Returns:
        (是否跳过, 缓存的结果)
    """
    # 检查是否有完整的checkpoint
    if checkpoint_manager.is_completed():
        # 获取report阶段的数据（最终输出）
        report_data = checkpoint_manager.get_stage_data("report")
        if report_data:
            console.print("[green]✅ 发现完整的执行结果，将使用缓存数据[/green]")
            return True, report_data.get("output")

    return False, None


def save_crew_result(checkpoint_manager: CheckpointManager, result: Any):
    """
    保存Crew执行结果到checkpoint

    Args:
        checkpoint_manager: checkpoint管理器
        result: Crew执行结果
    """
    # 提取结果文本
    if hasattr(result, "raw"):
        raw_output = result.raw
    elif hasattr(result, "output"):
        raw_output = result.output
    else:
        raw_output = str(result)

    # 保存到report阶段
    checkpoint_manager.save_checkpoint(
        stage="report",
        data={
            "output": raw_output,
            "timestamp": datetime.now().isoformat()
        }
    )

    # 标记为完成
    checkpoint_manager.mark_completed()
    console.print("[green]💾 执行结果已保存到checkpoint[/green]")
