"""
main.py 集成checkpoint功能的最小化修改示例

只需要在main.py中添加以下几处修改即可实现断点续传功能
"""

# ═══════════════════════════════════════════════════════════
# 修改1: 在文件开头的导入部分添加
# ═══════════════════════════════════════════════════════════

from checkpoint_manager import check_and_prompt_resume
from resumable_executor import should_skip_execution, save_crew_result


# ═══════════════════════════════════════════════════════════
# 修改2: 在main()函数开头添加checkpoint检查
# ═══════════════════════════════════════════════════════════

def main():
    console.print(Panel.fit(
        f"[bold cyan]🛰️ 中科天塔竞情分析半月报[/bold cyan]\n\n"
        # ... 原有代码 ...
    ))

    # ========== 新增代码开始 ==========
    # 检查是否有未完成的任务
    checkpoint_manager, should_resume = check_and_prompt_resume(OUTPUT_DIR)

    # 检查是否可以使用缓存结果
    skip_execution, cached_result = should_skip_execution(checkpoint_manager)

    if skip_execution and cached_result:
        console.print("[green]✅ 使用缓存的执行结果，跳过Crew执行[/green]\n")
        raw_output = cached_result
        # 跳转到结果解析部分（见修改4）
        goto_result_parsing = True
    else:
        goto_result_parsing = False
    # ========== 新增代码结束 ==========

    # ══════════════════════════════════
    # 1. 检查 API Key
    # ══════════════════════════════════
    # ========== 修改：添加条件判断 ==========
    if not goto_result_parsing:
        from config import DEEPSEEK_API_KEY, BOCHA_API_KEY
        # ... 原有的API验证代码 ...


# ═══════════════════════════════════════════════════════════
# 修改3: 在Crew执行部分添加checkpoint保存
# ═══════════════════════════════════════════════════════════

    # ══════════════════════════════════
    # 3. 启动 Crew
    # ══════════════════════════════════
    # ========== 修改：添加条件判断 ==========
    if not goto_result_parsing:
        start_time = datetime.now()
        logger.info(f"任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            result = crew.kickoff()
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"任务完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"总耗时: {duration}")

            # ========== 新增代码：保存checkpoint ==========
            save_crew_result(checkpoint_manager, result)
            # ========== 新增代码结束 ==========

        except KeyboardInterrupt:
            console.print("\n[bold yellow]⚠️ 用户中断执行[/bold yellow]")
            logger.warning("用户中断执行")
            sys.exit(0)
        except Exception as e:
            logger.error("Crew execution failed: %s", e, exc_info=True)
            console.print(f"\n[bold red]❌ 执行失败: {e}[/bold red]")
            console.print("[dim]请检查 API Key 配置和网络连接[/dim]")
            sys.exit(1)


# ═══════════════════════════════════════════════════════════
# 修改4: 在结果解析部分添加标签（用于跳转）
# ═══════════════════════════════════════════════════════════

    # ══════════════════════════════════
    # 4. 解析结果
    # ══════════════════════════════════
    # ========== 修改：添加条件判断 ==========
    if not goto_result_parsing:
        console.print("\n[bold green]✅ 智能体执行完成，正在解析结果...[/bold green]\n")
        logger.info("开始解析结果")

        # 从 CrewAI 结果中提取原始文本
        if hasattr(result, "raw"):
            raw_output = result.raw
        elif hasattr(result, "output"):
            raw_output = result.output
        else:
            raw_output = str(result)

    # ========== 从这里开始，无论是否跳过执行，都会执行 ==========
    # 解析JSON、渲染报告、生成PDF等后续步骤...
    console.print(f"[dim]原始输出长度: {len(raw_output)} 字符[/dim]")
    report_data = extract_json(raw_output)
    # ... 后续代码保持不变 ...


# ═══════════════════════════════════════════════════════════
# 完整的修改总结
# ═══════════════════════════════════════════════════════════

"""
总共需要修改4处：

1. 导入checkpoint相关模块（2行）
2. 在main()开头添加checkpoint检查（约10行）
3. 在Crew执行部分添加checkpoint保存（1行）
4. 在API验证和Crew执行部分添加条件判断（if not goto_result_parsing）

修改后的效果：
- 如果任务完整执行完成，下次运行可以直接使用缓存结果
- 如果任务中途中断，下次运行会询问是否重新开始
- 不影响原有的功能和逻辑
"""
