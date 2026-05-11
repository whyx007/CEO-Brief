#!/usr/bin/env python3
"""
测试LLM超时配置
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents import deepseek_llm, deepseek_llm_long, qwen_llm

def test_timeout_config():
    """测试超时配置是否正确设置"""
    print("检查LLM超时配置...\n")

    # 检查deepseek_llm
    print("1. deepseek_llm (常规任务):")
    print(f"   - Model: {deepseek_llm.model}")
    print(f"   - Max tokens: {deepseek_llm.max_tokens}")
    if hasattr(deepseek_llm, 'timeout'):
        print(f"   - Timeout: {deepseek_llm.timeout}秒")
    else:
        print("   - Timeout: 未设置（可能使用默认值）")
    print()

    # 检查deepseek_llm_long
    print("2. deepseek_llm_long (长报告):")
    print(f"   - Model: {deepseek_llm_long.model}")
    print(f"   - Max tokens: {deepseek_llm_long.max_tokens}")
    if hasattr(deepseek_llm_long, 'timeout'):
        print(f"   - Timeout: {deepseek_llm_long.timeout}秒")
    else:
        print("   - Timeout: 未设置（可能使用默认值）")
    print()

    # 检查qwen_llm
    print("3. qwen_llm:")
    print(f"   - Model: {qwen_llm.model}")
    print(f"   - Max tokens: {qwen_llm.max_tokens}")
    if hasattr(qwen_llm, 'timeout'):
        print(f"   - Timeout: {qwen_llm.timeout}秒")
    else:
        print("   - Timeout: 未设置（可能使用默认值）")
    print()

    print("=" * 60)
    print("配置检查完成")
    print("=" * 60)

if __name__ == "__main__":
    test_timeout_config()
