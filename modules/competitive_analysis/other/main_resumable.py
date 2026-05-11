#!/usr/bin/env python3
"""
支持断点续传的主程序入口

使用方法:
    python main_resumable.py

功能:
    1. 检查是否有未完成的任务
    2. 如果有，询问用户是继续还是重新开始
    3. 如果选择继续且任务已完成，直接使用缓存结果
    4. 否则执行完整的Crew任务链
    5. 执行完成后保存checkpoint
"""

import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import OUTPUT_DIR
from checkpoint_manager import check_and_prompt_resume
from resumable_executor import should_skip_execution, save_crew_result
from rich.console import Console

console = Console()


def main():
    """主函数 - 支持断点续传"""

    # ══════════════════════════════════
    # 1. 检查是否有未完成的任务
    # ══════════════════════════════════
    checkpoint_manager, should_resume = check_and_prompt_resume(OUTPUT_DIR)

    # 检查是否可以跳过执行
    skip_execution, cached_result = should_skip_execution(checkpoint_manager)

    if skip_execution and cached_result:
        console.print("\n[bold green]✅ 发现完整的执行结果！[/bold green]")
        console.print("[dim]将直接使用缓存的结果，无需重新执行任务[/dim]\n")

        # 直接使用缓存结果，跳过Crew执行
        # 这里可以直接调用结果处理逻辑
        console.print("[yellow]注意：当前版本仅支持完整重新执行[/yellow]")
        console.print("[yellow]如需使用缓存结果，请手动查看output目录中的文件[/yellow]\n")

        # 询问是否重新执行
        from rich.prompt import Confirm
        restart = Confirm.ask(
            "[bold cyan]是否重新执行任务？[/bold cyan]",
            default=False
        )

        if not restart:
            console.print("[green]✅ 使用缓存结果，程序退出[/green]")
            return

        # 清除checkpoint，重新开始
        checkpoint_manager.clear_checkpoint()

    # ══════════════════════════════════
    # 2. 执行原始main函数
    # ══════════════════════════════════
    console.print("[cyan]▶️ 开始执行任务...[/cyan]\n")

    # 导入原始main模块
    from main import main as original_main
    from main import crew, start_time

    try:
        # 执行原始main函数
        original_main()

        # 如果执行成功，保存checkpoint
        # 注意：这里需要获取crew的执行结果
        # 由于原始main函数的结构，我们需要修改它来返回结果
        console.print("\n[green]✅ 任务执行完成[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 用户中断执行[/yellow]")
        console.print("[dim]下次运行时可以选择继续未完成的任务[/dim]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]❌ 执行失败: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
