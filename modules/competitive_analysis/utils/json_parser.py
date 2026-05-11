"""
JSON extraction utilities for parsing LLM outputs
"""

import json
import re


def extract_json(text: str) -> dict | list | None:
    """从 LLM 输出中健壮地提取 JSON"""
    if not text or not isinstance(text, str):
        return None

    # 1) 直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2) 从 markdown code fence 中提取
    patterns = [
        r"```json\s*\n?(.*?)\n?```",        # ```json ... ```
        r"```\s*\n?(.*?)\n?```",             # ``` ... ```
        r"(\[\s*\{[\s\S]*?\}\s*\])",         # JSON 数组
        r"(\{\s*\"[\s\S]*?\})",              # JSON 对象
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except (json.JSONDecodeError, TypeError):
                continue

    return None
