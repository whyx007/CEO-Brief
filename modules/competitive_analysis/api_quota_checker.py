"""
API配额查询模块 - 查询各个API的剩余配额和余额

支持的API:
- DeepSeek (通过API查询余额)
- 博查 Bocha (通过API查询配额)
- Serper (通过API查询配额)
"""

import requests
import logging
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


def check_deepseek_balance(api_key: str, base_url: str = "https://api.deepseek.com") -> Optional[Dict[str, Any]]:
    """
    查询DeepSeek API余额

    Args:
        api_key: DeepSeek API Key
        base_url: API基础URL

    Returns:
        包含余额信息的字典，如果查询失败返回None
        {
            "balance": 100.50,  # 余额（元）
            "currency": "CNY",  # 货币单位
            "status": "ok"
        }
    """
    try:
        # DeepSeek的余额查询端点
        response = requests.get(
            f"{base_url}/user/balance",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            # DeepSeek返回的数据格式可能是: {"balance_infos": [...]}
            # 或者 {"total_balance": "100.50", "currency": "CNY"}
            # 需要根据实际API响应调整

            # 尝试多种可能的响应格式
            if "total_balance" in data:
                return {
                    "balance": float(data.get("total_balance", 0)),
                    "currency": data.get("currency", "CNY"),
                    "status": "ok"
                }
            elif "balance_infos" in data and len(data["balance_infos"]) > 0:
                balance_info = data["balance_infos"][0]
                return {
                    "balance": float(balance_info.get("total_balance", 0)),
                    "currency": balance_info.get("currency", "CNY"),
                    "status": "ok"
                }
            else:
                # 如果格式不匹配，返回原始数据
                return {
                    "raw_data": data,
                    "status": "ok"
                }
        else:
            logger.warning(f"DeepSeek余额查询失败: HTTP {response.status_code}")
            return None

    except Exception as e:
        logger.warning(f"DeepSeek余额查询异常: {e}")
        return None


def check_bocha_quota(api_key: str) -> Optional[Dict[str, Any]]:
    """
    查询博查API配额

    Args:
        api_key: 博查 API Key

    Returns:
        包含配额信息的字典，如果查询失败返回None
        {
            "remaining": 1000,  # 剩余次数
            "total": 10000,     # 总配额
            "status": "ok"
        }
    """
    try:
        # 博查的配额查询端点（需要根据实际API文档调整）
        response = requests.get(
            "https://api.bochaai.com/v1/user/quota",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            # 根据实际API响应格式调整
            return {
                "remaining": data.get("remaining", 0),
                "total": data.get("total", 0),
                "used": data.get("used", 0),
                "status": "ok"
            }
        else:
            logger.warning(f"博查配额查询失败: HTTP {response.status_code}")
            return None

    except Exception as e:
        logger.warning(f"博查配额查询异常: {e}")
        return None


def check_serper_quota(api_key: str) -> Optional[Dict[str, Any]]:
    """
    查询Serper API配额

    Args:
        api_key: Serper API Key

    Returns:
        包含配额信息的字典，如果查询失败返回None
        {
            "remaining": 500,   # 剩余次数
            "total": 2500,      # 总配额
            "status": "ok"
        }
    """
    try:
        # Serper的配额查询端点
        response = requests.get(
            "https://google.serper.dev/account",
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            # Serper返回的数据格式: {"credits": 500}
            return {
                "remaining": data.get("credits", 0),
                "status": "ok"
            }
        else:
            logger.warning(f"Serper配额查询失败: HTTP {response.status_code}")
            return None

    except Exception as e:
        logger.warning(f"Serper配额查询异常: {e}")
        return None


def estimate_task_cost() -> Dict[str, Any]:
    """
    估算完成一次完整任务所需的API调用次数和成本

    Returns:
        估算信息字典
    """
    # 基于历史数据估算
    # 从日志 "OpenAI API usage: {'prompt_tokens': 16889, 'completion_tokens': 3517, 'total_tokens': 20406}"
    # 可以看出单次任务大约使用20k tokens

    # 一次完整任务的估算:
    # - 9个任务阶段
    # - 每个阶段平均10-20次LLM调用
    # - 每次调用平均5k-10k tokens
    # - 总计约 100-200次LLM调用，500k-1M tokens

    # DeepSeek定价: 约 ¥0.001/1k tokens (输入) + ¥0.002/1k tokens (输出)
    # 假设输入:输出 = 3:1
    # 平均成本: 750k输入 + 250k输出 = 0.75 + 0.5 = ¥1.25

    # 搜索API:
    # - 博查: 每次任务约50-100次搜索
    # - Serper: 每次任务约50-100次搜索

    return {
        "llm_calls": {"min": 100, "max": 200, "avg": 150},
        "llm_tokens": {"min": 500000, "max": 1000000, "avg": 750000},
        "llm_cost_cny": {"min": 1.0, "max": 2.5, "avg": 1.5},
        "search_calls": {"min": 50, "max": 100, "avg": 75},
        "search_calls_per_engine": {"bocha": 40, "serper": 35}
    }


def check_all_quotas() -> Dict[str, Any]:
    """
    查询所有API的配额信息

    Returns:
        包含所有API配额信息的字典
    """
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, BOCHA_API_KEY, SERPER_API_KEY

    results = {
        "deepseek": None,
        "bocha": None,
        "serper": None,
        "estimate": estimate_task_cost()
    }

    # 查询DeepSeek余额
    if DEEPSEEK_API_KEY:
        console.print("[dim]正在查询DeepSeek余额...[/dim]")
        results["deepseek"] = check_deepseek_balance(DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL)

    # 查询博查配额
    if BOCHA_API_KEY:
        console.print("[dim]正在查询博查配额...[/dim]")
        results["bocha"] = check_bocha_quota(BOCHA_API_KEY)

    # 查询Serper配额
    if SERPER_API_KEY:
        console.print("[dim]正在查询Serper配额...[/dim]")
        results["serper"] = check_serper_quota(SERPER_API_KEY)

    return results


def display_quota_table(quota_info: Dict[str, Any]):
    """
    以表格形式显示配额信息

    Args:
        quota_info: 配额信息字典
    """
    table = Table(title="API配额状态", show_header=True, header_style="bold cyan")
    table.add_column("API", style="cyan", width=15)
    table.add_column("状态", width=10)
    table.add_column("剩余/余额", width=20)
    table.add_column("预估消耗", width=20)
    table.add_column("是否充足", width=10)

    estimate = quota_info.get("estimate", {})

    # DeepSeek
    deepseek = quota_info.get("deepseek")
    if deepseek and deepseek.get("status") == "ok":
        balance = deepseek.get("balance", 0)
        currency = deepseek.get("currency", "CNY")
        estimated_cost = estimate.get("llm_cost_cny", {}).get("avg", 1.5)
        sufficient = "OK" if balance >= estimated_cost else "X"
        status_color = "green" if balance >= estimated_cost else "red"

        table.add_row(
            "DeepSeek",
            f"[{status_color}]可用[/{status_color}]",
            f"{balance:.2f} {currency}",
            f"~{estimated_cost:.2f} {currency}",
            f"[{status_color}]{sufficient}[/{status_color}]"
        )
    else:
        table.add_row("DeepSeek", "[yellow]未知[/yellow]", "-", "-", "-")

    # 博查
    bocha = quota_info.get("bocha")
    if bocha and bocha.get("status") == "ok":
        remaining = bocha.get("remaining", 0)
        total = bocha.get("total", 0)
        estimated_calls = estimate.get("search_calls_per_engine", {}).get("bocha", 40)
        sufficient = "OK" if remaining >= estimated_calls else "X"
        status_color = "green" if remaining >= estimated_calls else "red"

        table.add_row(
            "博查 Bocha",
            f"[{status_color}]可用[/{status_color}]",
            f"{remaining}/{total} 次",
            f"~{estimated_calls} 次",
            f"[{status_color}]{sufficient}[/{status_color}]"
        )
    else:
        table.add_row("博查 Bocha", "[yellow]未知[/yellow]", "-", "-", "-")

    # Serper
    serper = quota_info.get("serper")
    if serper and serper.get("status") == "ok":
        remaining = serper.get("remaining", 0)
        estimated_calls = estimate.get("search_calls_per_engine", {}).get("serper", 35)
        sufficient = "OK" if remaining >= estimated_calls else "X"
        status_color = "green" if remaining >= estimated_calls else "red"

        table.add_row(
            "Serper",
            f"[{status_color}]可用[/{status_color}]",
            f"{remaining} 次",
            f"~{estimated_calls} 次",
            f"[{status_color}]{sufficient}[/{status_color}]"
        )
    else:
        table.add_row("Serper", "[yellow]未知[/yellow]", "-", "-", "-")

    console.print("\n")
    console.print(table)
    console.print("\n")


def check_sufficient_quota(quota_info: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    检查配额是否充足

    Args:
        quota_info: 配额信息字典

    Returns:
        (是否充足, 不足的API列表)
    """
    insufficient = []
    estimate = quota_info.get("estimate", {})

    # 检查DeepSeek
    deepseek = quota_info.get("deepseek")
    if deepseek and deepseek.get("status") == "ok":
        balance = deepseek.get("balance", 0)
        estimated_cost = estimate.get("llm_cost_cny", {}).get("avg", 1.5)
        if balance < estimated_cost:
            insufficient.append(f"DeepSeek (余额: {balance:.2f}, 需要: ~{estimated_cost:.2f})")

    # 检查博查
    bocha = quota_info.get("bocha")
    if bocha and bocha.get("status") == "ok":
        remaining = bocha.get("remaining", 0)
        estimated_calls = estimate.get("search_calls_per_engine", {}).get("bocha", 40)
        if remaining < estimated_calls:
            insufficient.append(f"博查 (剩余: {remaining}, 需要: ~{estimated_calls})")

    # 检查Serper
    serper = quota_info.get("serper")
    if serper and serper.get("status") == "ok":
        remaining = serper.get("remaining", 0)
        estimated_calls = estimate.get("search_calls_per_engine", {}).get("serper", 35)
        if remaining < estimated_calls:
            insufficient.append(f"Serper (剩余: {remaining}, 需要: ~{estimated_calls})")

    return len(insufficient) == 0, insufficient
