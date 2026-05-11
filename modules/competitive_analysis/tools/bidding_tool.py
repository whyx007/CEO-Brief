"""
招投标专项搜索工具
"""

import json
import sys
import logging
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .search_tool import multi_search


class BiddingInput(BaseModel):
    company: str = Field(description="公司名称")
    keywords: str = Field(default="", description="额外关键词")


class BiddingSearchTool(BaseTool):
    name: str = "bidding_search"
    description: str = (
        "搜索某公司的招投标信息：中标公告、入围结果、政府/军队采购。"
        "输入公司名称和可选关键词。"
    )
    args_schema: Type[BaseModel] = BiddingInput

    def _run(self, company: str, keywords: str = "") -> str:
        queries = [
            f"{company} 中标 公告 卫星 测控 {keywords}".strip(),
            f"{company} 招标 入围 航天 地面站 {keywords}".strip(),
            f"{company} 政府采购 军队采购 框架协议 {keywords}".strip(),
        ]
        all_results = []

        old_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(max(old_limit, 3000))
            for q in queries:
                try:
                    results = multi_search(q, num=4, include_news=False, include_bidding=True, freshness="oneweek")
                    for r in results:
                        r["search_category"] = "bidding"
                    all_results.extend(results)
                except RecursionError:
                    logging.warning(f"RecursionError for bidding query: {q}")
                    continue
                except Exception as e:
                    logging.warning(f"bidding_tool error for '{q}': {type(e).__name__}")
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
