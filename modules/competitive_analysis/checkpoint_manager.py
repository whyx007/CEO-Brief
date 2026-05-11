"""
断点续传管理器 - 支持任务中断后继续执行
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.prompt import Confirm

console = Console()

class CheckpointManager:
    """管理任务执行状态和断点续传"""

    # 任务阶段定义
    STAGES = [
        "discover",           # 1. 发现竞争对手
        "talent",            # 2. 人才分析
        "market",            # 3. 市场分析
        "tech",              # 4. 技术分析
        "bidding_funding",   # 5. 竞标融资分析
        "policy",            # 6. 政策分析
        "global_tech",       # 6.5. 全球技术趋势
        "scoring",           # 7. 综合评分
        "report",            # 8. CEO报告生成
        "completed",         # 9. 全部完成
    ]

    def __init__(self, output_dir: str):
        """
        初始化checkpoint管理器

        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.checkpoint_file = self.output_dir / "checkpoint.json"
        self.checkpoint_data: Optional[Dict[str, Any]] = None

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        加载checkpoint文件

        Returns:
            checkpoint数据，如果不存在返回None
        """
        if not self.checkpoint_file.exists():
            return None

        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                self.checkpoint_data = json.load(f)
            return self.checkpoint_data
        except Exception as e:
            console.print(f"[yellow]WARNING: 加载checkpoint失败: {e}[/yellow]")
            return None

    def save_checkpoint(self, stage: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """
        保存checkpoint

        Args:
            stage: 当前完成的阶段
            data: 该阶段的输出数据
            metadata: 额外的元数据
        """
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 构建checkpoint数据
        if self.checkpoint_data is None:
            self.checkpoint_data = {
                "start_time": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "current_stage": stage,
                "completed_stages": [],
                "stage_data": {},
                "metadata": metadata or {}
            }

        # 更新checkpoint
        self.checkpoint_data["last_update"] = datetime.now().isoformat()
        self.checkpoint_data["current_stage"] = stage

        # 如果该阶段还未完成，添加到已完成列表
        if stage not in self.checkpoint_data["completed_stages"]:
            self.checkpoint_data["completed_stages"].append(stage)

        # 保存阶段数据
        self.checkpoint_data["stage_data"][stage] = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        # 更新元数据
        if metadata:
            self.checkpoint_data["metadata"].update(metadata)

        # 写入文件
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkpoint_data, f, ensure_ascii=False, indent=2)
            console.print(f"[dim]SAVED: Checkpoint已保存: {stage}[/dim]")
        except Exception as e:
            console.print(f"[yellow]WARNING: 保存checkpoint失败: {e}[/yellow]")

    def get_stage_data(self, stage: str) -> Optional[Dict[str, Any]]:
        """
        获取指定阶段的数据

        Args:
            stage: 阶段名称

        Returns:
            阶段数据，如果不存在返回None
        """
        if self.checkpoint_data is None:
            return None

        stage_info = self.checkpoint_data.get("stage_data", {}).get(stage)
        if stage_info:
            return stage_info.get("data")
        return None

    def get_next_stage(self) -> Optional[str]:
        """
        获取下一个需要执行的阶段

        Returns:
            下一个阶段名称，如果全部完成返回None
        """
        if self.checkpoint_data is None:
            return self.STAGES[0]  # 从第一个阶段开始

        current_stage = self.checkpoint_data.get("current_stage")
        completed_stages = self.checkpoint_data.get("completed_stages", [])

        # 如果当前阶段是completed，说明全部完成
        if current_stage == "completed":
            return None

        # 找到下一个未完成的阶段
        for stage in self.STAGES:
            if stage not in completed_stages:
                return stage

        return None

    def is_completed(self) -> bool:
        """
        检查任务是否已完成

        Returns:
            True如果任务已完成，否则False
        """
        if self.checkpoint_data is None:
            return False

        return self.checkpoint_data.get("current_stage") == "completed"

    def mark_completed(self):
        """标记任务为已完成"""
        if self.checkpoint_data is None:
            self.checkpoint_data = {
                "start_time": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "current_stage": "completed",
                "completed_stages": self.STAGES[:-1],  # 除了completed之外的所有阶段
                "stage_data": {},
                "metadata": {}
            }
        else:
            self.checkpoint_data["current_stage"] = "completed"
            self.checkpoint_data["last_update"] = datetime.now().isoformat()

        # 保存
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkpoint_data, f, ensure_ascii=False, indent=2)
            console.print("[green]DONE: 任务已标记为完成[/green]")
        except Exception as e:
            console.print(f"[yellow]WARNING: 保存checkpoint失败: {e}[/yellow]")

    def clear_checkpoint(self):
        """清除checkpoint文件"""
        if self.checkpoint_file.exists():
            try:
                self.checkpoint_file.unlink()
                console.print("[dim]DELETED: Checkpoint已清除[/dim]")
            except Exception as e:
                console.print(f"[yellow]WARNING: 清除checkpoint失败: {e}[/yellow]")
        self.checkpoint_data = None

    def get_progress_info(self) -> Dict[str, Any]:
        """
        获取任务进度信息

        Returns:
            包含进度信息的字典
        """
        if self.checkpoint_data is None:
            return {
                "status": "not_started",
                "progress": 0,
                "current_stage": None,
                "completed_stages": [],
                "total_stages": len(self.STAGES) - 1  # 不包括completed
            }

        completed_stages = self.checkpoint_data.get("completed_stages", [])
        current_stage = self.checkpoint_data.get("current_stage")
        total_stages = len(self.STAGES) - 1  # 不包括completed

        progress = int((len(completed_stages) / total_stages) * 100)

        return {
            "status": "completed" if current_stage == "completed" else "in_progress",
            "progress": progress,
            "current_stage": current_stage,
            "completed_stages": completed_stages,
            "total_stages": total_stages,
            "start_time": self.checkpoint_data.get("start_time"),
            "last_update": self.checkpoint_data.get("last_update")
        }

    def prompt_resume_or_restart(self) -> bool:
        """
        询问用户是继续还是重新开始

        Returns:
            True表示继续，False表示重新开始
        """
        if self.checkpoint_data is None:
            return False

        progress_info = self.get_progress_info()

        console.print("\n[bold yellow]📋 发现未完成的任务[/bold yellow]")
        console.print(f"[dim]开始时间: {progress_info['start_time']}[/dim]")
        console.print(f"[dim]最后更新: {progress_info['last_update']}[/dim]")
        console.print(f"[dim]当前进度: {progress_info['progress']}% ({len(progress_info['completed_stages'])}/{progress_info['total_stages']})[/dim]")
        console.print(f"[dim]当前阶段: {progress_info['current_stage']}[/dim]")
        console.print(f"[dim]已完成阶段: {', '.join(progress_info['completed_stages'])}[/dim]\n")

        # 非交互场景（如 HTTP 接口触发）默认重开，避免阻塞在 stdin
        if not sys.stdin or not sys.stdin.isatty():
            console.print("[yellow][AUTO] 检测到非交互环境，自动重新开始任务...[/yellow]")
            self.clear_checkpoint()
            return False

        # 询问用户
        resume = Confirm.ask(
            "[bold cyan]是否继续之前的任务？[/bold cyan]",
            default=True
        )

        if not resume:
            console.print("[yellow][RESET] 将重新开始任务...[/yellow]")
            self.clear_checkpoint()
        else:
            console.print("[green][RESUME] 继续之前的任务...[/green]")

        return resume


def check_and_prompt_resume(output_dir: str) -> tuple[CheckpointManager, bool]:
    """
    检查是否有未完成的任务，并询问用户是否继续

    Args:
        output_dir: 输出目录路径

    Returns:
        (CheckpointManager实例, 是否继续之前的任务)
    """
    manager = CheckpointManager(output_dir)
    checkpoint = manager.load_checkpoint()

    if checkpoint is None:
        # 没有checkpoint，从头开始
        return manager, False

    # 检查是否已完成
    if manager.is_completed():
        console.print("[green]DONE: 之前的任务已完成[/green]")
        if not sys.stdin or not sys.stdin.isatty():
            console.print("[yellow][AUTO] 检测到非交互环境，自动重新开始新的任务...[/yellow]")
            manager.clear_checkpoint()
            return manager, False
        # 询问是否重新开始
        restart = Confirm.ask(
            "[bold cyan]是否重新开始新的任务？[/bold cyan]",
            default=False
        )
        if restart:
            manager.clear_checkpoint()
            return manager, False
        else:
            console.print("[dim]使用之前的结果...[/dim]")
            return manager, True

    # 有未完成的任务，询问是否继续
    resume = manager.prompt_resume_or_restart()
    return manager, resume
