#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试阿里 Qwen 3.5-Plus 模型可用性
"""

import os
from dotenv import load_dotenv

load_dotenv()

# 检查环境变量
print("=" * 60)
print("🔍 检查环境变量配置")
print("=" * 60)

qwen_api_key = os.getenv("QWEN_API_KEY", "")
qwen_base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
qwen_model = os.getenv("QWEN_MODEL", "qwen-plus")

print(f"✓ QWEN_API_KEY: {qwen_api_key[:20]}{'...' if len(qwen_api_key) > 20 else ''} (长度: {len(qwen_api_key)})")
print(f"✓ QWEN_BASE_URL: {qwen_base_url}")
print(f"✓ QWEN_MODEL: {qwen_model}")

if not qwen_api_key:
    print("\n❌ 错误：QWEN_API_KEY 未设置！")
    print("请在 .env 文件中添加: QWEN_API_KEY=your_api_key")
    exit(1)

print("\n✅ 环境变量配置完整\n")

# 测试 LLM 初始化
print("=" * 60)
print("🚀 测试 LLM 初始化")
print("=" * 60)

try:
    from crewai import LLM
    from config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL
    
    qwen_llm = LLM(
        model=QWEN_MODEL,
        base_url=QWEN_BASE_URL,
        api_key=QWEN_API_KEY,
        temperature=0.15,
        max_tokens=8192,
    )
    
    print("✅ LLM 对象创建成功\n")
    
except Exception as e:
    print(f"❌ LLM 初始化失败: {e}\n")
    exit(1)

# 测试 LLM 调用
print("=" * 60)
print("💬 测试 LLM 调用")
print("=" * 60)

try:
    response = qwen_llm.call(
        messages=[
            {
                "role": "user",
                "content": "你好，please test if you can respond to this message. 请用中文回复。"
            }
        ]
    )
    
    print(f"✅ LLM 调用成功！\n")
    print(f"响应内容:\n{response}\n")
    
except Exception as e:
    print(f"❌ LLM 调用失败: {e}\n")
    import traceback
    traceback.print_exc()
    exit(1)

# 测试大规模输出以验证令牌上限
print("=" * 60)
print("🧪 测试大输出（令牌容量）")
print("=" * 60)

try:
    # 让模型生成一个很长的字符串，至少包含5000个汉字。
    long_prompt = (
        "请生成一个至少包含500个汉字的随机字符串，" 
        "不要解释，只生成正文。"
    )
    response2 = qwen_llm.call(
        messages=[{"role": "user", "content": long_prompt}]
    )
    print("✅ 大输出调用成功！")
    print(f"生成字符数: {len(response2)}")
    # 显示前一部分以确认
    print(response2[:1000] + "...\n")

except Exception as e:
    print(f"❌ 大输出调用失败: {e}\n")
    import traceback
    traceback.print_exc()
    exit(1)

print("=" * 60)
print("✅ 所有测试通过！Qwen 模型可用")
print("=" * 60)
