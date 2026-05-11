#!/usr/bin/env python3
"""
测试checkpoint功能

运行此脚本来测试checkpoint管理器的基本功能
"""

import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from checkpoint_manager import CheckpointManager
from rich.console import Console

console = Console()


def test_checkpoint_basic():
    """测试基本的checkpoint功能"""
    console.print("[bold cyan]测试1: 基本checkpoint功能[/bold cyan]\n")

    # 创建测试目录
    test_dir = "output/test_checkpoint"
    Path(test_dir).mkdir(parents=True, exist_ok=True)

    # 创建管理器
    manager = CheckpointManager(test_dir)

    # 测试1: 加载不存在的checkpoint
    console.print("1. 加载不存在的checkpoint...")
    checkpoint = manager.load_checkpoint()
    assert checkpoint is None, "应该返回None"
    console.print("[green]✓ 通过[/green]\n")

    # 测试2: 保存checkpoint
    console.print("2. 保存checkpoint...")
    manager.save_checkpoint(
        stage="discover",
        data={"output": "测试数据", "companies": ["公司A", "公司B"]}
    )
    console.print("[green]✓ 通过[/green]\n")

    # 测试3: 加载checkpoint
    console.print("3. 加载checkpoint...")
    checkpoint = manager.load_checkpoint()
    assert checkpoint is not None, "应该能加载checkpoint"
    assert "discover" in checkpoint["completed_stages"], "应该包含discover阶段"
    console.print(f"[dim]Checkpoint内容: {checkpoint}[/dim]")
    console.print("[green]✓ 通过[/green]\n")

    # 测试4: 获取阶段数据
    console.print("4. 获取阶段数据...")
    data = manager.get_stage_data("discover")
    assert data is not None, "应该能获取discover阶段的数据"
    assert data["output"] == "测试数据", "数据应该匹配"
    console.print(f"[dim]阶段数据: {data}[/dim]")
    console.print("[green]✓ 通过[/green]\n")

    # 测试5: 获取进度信息
    console.print("5. 获取进度信息...")
    progress = manager.get_progress_info()
    console.print(f"[dim]进度: {progress['progress']}%[/dim]")
    console.print(f"[dim]当前阶段: {progress['current_stage']}[/dim]")
    console.print(f"[dim]已完成: {progress['completed_stages']}[/dim]")
    console.print("[green]✓ 通过[/green]\n")

    # 测试6: 保存多个阶段
    console.print("6. 保存多个阶段...")
    for stage in ["talent", "market", "tech"]:
        manager.save_checkpoint(
            stage=stage,
            data={"output": f"{stage}的测试数据"}
        )
    progress = manager.get_progress_info()
    console.print(f"[dim]进度: {progress['progress']}%[/dim]")
    console.print("[green]✓ 通过[/green]\n")

    # 测试7: 标记为完成
    console.print("7. 标记为完成...")
    manager.mark_completed()
    assert manager.is_completed(), "应该标记为已完成"
    console.print("[green]✓ 通过[/green]\n")

    # 测试8: 清除checkpoint
    console.print("8. 清除checkpoint...")
    manager.clear_checkpoint()
    checkpoint = manager.load_checkpoint()
    assert checkpoint is None, "应该已清除"
    console.print("[green]✓ 通过[/green]\n")

    console.print("[bold green]✅ 所有测试通过！[/bold green]\n")


def test_checkpoint_resume():
    """测试断点续传流程"""
    console.print("[bold cyan]测试2: 断点续传流程[/bold cyan]\n")

    test_dir = "output/test_resume"
    Path(test_dir).mkdir(parents=True, exist_ok=True)

    # 模拟第一次运行（中途中断）
    console.print("1. 模拟第一次运行（中途中断）...")
    manager1 = CheckpointManager(test_dir)
    manager1.save_checkpoint("discover", {"output": "发现了10家公司"})
    manager1.save_checkpoint("talent", {"output": "人才分析完成"})
    console.print("[green]✓ 保存了2个阶段的checkpoint[/green]\n")

    # 模拟第二次运行（继续执行）
    console.print("2. 模拟第二次运行（检查checkpoint）...")
    manager2 = CheckpointManager(test_dir)
    checkpoint = manager2.load_checkpoint()

    if checkpoint:
        progress = manager2.get_progress_info()
        console.print(f"[yellow]发现未完成的任务[/yellow]")
        console.print(f"[dim]进度: {progress['progress']}%[/dim]")
        console.print(f"[dim]已完成: {progress['completed_stages']}[/dim]")

        # 继续执行剩余任务
        console.print("\n3. 继续执行剩余任务...")
        for stage in ["market", "tech", "bidding_funding"]:
            # 检查是否已完成
            existing = manager2.get_stage_data(stage)
            if existing:
                console.print(f"[dim]跳过已完成的阶段: {stage}[/dim]")
            else:
                console.print(f"[cyan]执行阶段: {stage}[/cyan]")
                manager2.save_checkpoint(stage, {"output": f"{stage}完成"})

        # 标记为完成
        manager2.mark_completed()
        console.print("[green]✓ 任务完成[/green]\n")

    # 模拟第三次运行（任务已完成）
    console.print("4. 模拟第三次运行（任务已完成）...")
    manager3 = CheckpointManager(test_dir)
    checkpoint = manager3.load_checkpoint()

    if manager3.is_completed():
        console.print("[green]✓ 任务已完成，可以直接使用结果[/green]\n")

    # 清理
    manager3.clear_checkpoint()
    console.print("[bold green]✅ 断点续传流程测试通过！[/bold green]\n")


def main():
    """运行所有测试"""
    console.print("\n[bold]Checkpoint功能测试[/bold]\n")
    console.print("="*60 + "\n")

    try:
        test_checkpoint_basic()
        test_checkpoint_resume()

        console.print("="*60)
        console.print("[bold green]所有测试通过！[/bold green]")
        console.print("="*60 + "\n")

    except AssertionError as e:
        console.print(f"\n[bold red]测试失败: {e}[/bold red]\n")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]测试异常: {e}[/bold red]\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
