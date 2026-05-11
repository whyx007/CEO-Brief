"""
融资信息搜索工具
"""

import json
import sys
import logging
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .search_tool import multi_search


class FundingInput(BaseModel):
    company: str = Field(description="公司名称")


class FundingSearchTool(BaseTool):
    name: str = "funding_search"
    description: str = (
        "搜索某公司的融资、投资、股权变更、估值、IPO 等资本动态。"
    )
    args_schema: Type[BaseModel] = FundingInput

    def _run(self, company: str) -> str:
        queries = [
            f"{company} 融资 投资 A轮 B轮 C轮 估值",
            f"{company} 股权变更 增资 国资 产业基金 IPO",
            f"{company} 借壳 重组 并购 收购 合并",
        ]
        all_results = []

        old_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(max(old_limit, 3000))
            for q in queries:
                try:
                    results = multi_search(q, num=4, freshness="oneweek")
                    for r in results:
                        r["search_category"] = "funding"
                    all_results.extend(results)
                except RecursionError:
                    logging.warning(f"RecursionError for funding query: {q}")
                    continue
                except Exception as e:
                    logging.warning(f"funding_tool error for '{q}': {type(e).__name__}")
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

        return json.dumps(unique[:8], ensure_ascii=False, indent=2)
