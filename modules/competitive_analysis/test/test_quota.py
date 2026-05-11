#!/usr/bin/env python3
"""
测试API配额查询功能
"""

import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from api_quota_checker import (
    check_deepseek_balance,
    check_bocha_quota,
    check_serper_quota,
    check_all_quotas,
    display_quota_table,
    check_sufficient_quota,
    estimate_task_cost
)
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, BOCHA_API_KEY, SERPER_API_KEY
from rich.console import Console

console = Console()


def test_individual_apis():
    """测试单个API的配额查询"""
    console.print("\n[bold cyan]测试1: 单个API配额查询[/bold cyan]\n")

    # 测试DeepSeek
    if DEEPSEEK_API_KEY:
        console.print("[dim]查询DeepSeek余额...[/dim]")
        result = check_deepseek_balance(DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL)
        if result:
            console.print(f"[green]DeepSeek余额: {result}[/green]")
        else:
            console.print("[yellow]DeepSeek余额查询失败（可能API不支持余额查询端点）[/yellow]")
    else:
        console.print("[yellow]DeepSeek API Key未配置[/yellow]")

    console.print()

    # 测试博查
    if BOCHA_API_KEY:
        console.print("[dim]查询博查配额...[/dim]")
        result = check_bocha_quota(BOCHA_API_KEY)
        if result:
            console.print(f"[green]博查配额: {result}[/green]")
        else:
            console.print("[yellow]博查配额查询失败（可能API不支持配额查询端点）[/yellow]")
    else:
        console.print("[yellow]博查 API Key未配置[/yellow]")

    console.print()

    # 测试Serper
    if SERPER_API_KEY:
        console.print("[dim]查询Serper配额...[/dim]")
        result = check_serper_quota(SERPER_API_KEY)
        if result:
            console.print(f"[green]Serper配额: {result}[/green]")
        else:
            console.print("[yellow]Serper配额查询失败（可能API不支持配额查询端点）[/yellow]")
    else:
        console.print("[yellow]Serper API Key未配置[/yellow]")

    console.print()


def test_cost_estimation():
    """测试成本估算"""
    console.print("\n[bold cyan]测试2: 任务成本估算[/bold cyan]\n")

    estimate = estimate_task_cost()
    console.print("[dim]估算信息:[/dim]")
    console.print(f"  LLM调用次数: {estimate['llm_calls']['min']}-{estimate['llm_calls']['max']} (平均: {estimate['llm_calls']['avg']})")
    console.print(f"  LLM Token数: {estimate['llm_tokens']['min']}-{estimate['llm_tokens']['max']} (平均: {estimate['llm_tokens']['avg']})")
    console.print(f"  LLM成本(CNY): {estimate['llm_cost_cny']['min']}-{estimate['llm_cost_cny']['max']} (平均: {estimate['llm_cost_cny']['avg']})")
    console.print(f"  搜索调用次数: {estimate['search_calls']['min']}-{estimate['search_calls']['max']} (平均: {estimate['search_calls']['avg']})")
    console.print(f"  博查调用: ~{estimate['search_calls_per_engine']['bocha']} 次")
    console.print(f"  Serper调用: ~{estimate['search_calls_per_engine']['serper']} 次")
    console.print()


def test_all_quotas():
    """测试查询所有配额"""
    console.print("\n[bold cyan]测试3: 查询所有API配额[/bold cyan]\n")

    quota_info = check_all_quotas()

    # 显示表格
    display_quota_table(quota_info)

    # 检查是否充足
    sufficient, insufficient_list = check_sufficient_quota(quota_info)

    if sufficient:
        console.print("[bold green]配额充足，可以执行任务[/bold green]\n")
    else:
        console.print("[bold yellow]配额可能不足：[/bold yellow]")
        for item in insufficient_list:
            console.print(f"  • {item}")
        console.print()


def main():
    """运行所有测试"""
    console.print("\n[bold]API配额查询功能测试[/bold]")
    console.print("="*60 + "\n")

    console.print("[dim]注意：某些API可能不提供配额查询端点，这是正常的[/dim]")
    console.print("[dim]如果查询失败，程序会使用估算值继续执行[/dim]\n")

    try:
        test_individual_apis()
        test_cost_estimation()
        test_all_quotas()

        console.print("="*60)
        console.print("[bold green]测试完成[/bold green]")
        console.print("="*60 + "\n")

    except Exception as e:
        console.print(f"\n[bold red]测试异常: {e}[/bold red]\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
