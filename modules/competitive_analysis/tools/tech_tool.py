"""
技术/专利/产品搜索工具
"""

import json
import sys
import logging
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .search_tool import multi_search


class TechInput(BaseModel):
    company: str = Field(description="公司名称")


class TechSearchTool(BaseTool):
    name: str = "tech_search"
    description: str = (
        "搜索某公司的技术方向动态：新产品发布、专利申请、技术架构升级、"
        "大模型/AI 能力、平台化进展、学术论文等。使用 SearXNG + 百度新闻多源搜索。"
    )
    args_schema: Type[BaseModel] = TechInput

    def _run(self, company: str) -> str:
        queries = [
            f"{company} 在轨管理 平台 技术 发布 升级 新产品",
            f"{company} 卫星 大模型 AI 智能化 专利 论文",
            f"{company} 测控 软件 系统架构 数字孪生 仿真",
            f"{company} 专利 发明 航天器 管理 控制",
        ]
        all_results = []
        
        old_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(max(old_limit, 3000))
            for q in queries:
                try:
                    results = multi_search(q, num=5, freshness="oneweek")
                    for r in results:
                        r["search_category"] = "tech"
                    all_results.extend(results)
                except RecursionError:
                    logging.warning(f"RecursionError for tech query: {q}")
                    continue
                except Exception as e:
                    logging.warning(f"tech_tool error for '{q}': {type(e).__name__}")
                    continue
        finally:
            sys.setrecursionlimit(old_limit)

        seen = set()
        unique = []
        for r in all_results:
            link = r.get("link", "")
            if link and link not in seen:
                seen.add(link)
                unique.append(r)

        return json.dumps(unique[:10], ensure_ascii=False, indent=2)