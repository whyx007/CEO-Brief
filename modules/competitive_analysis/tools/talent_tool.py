"""
人才/招聘专项搜索 — 精简版
核心改进：减少搜索次数，防止agent在搜索上超时。
只搜3个最关键的方向，每个方向限2个query。
"""

import json
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .search_tool import multi_search


class TalentInput(BaseModel):
    company: str = Field(description="公司名称")


class TalentSearchTool(BaseTool):
    name: str = "talent_search"
    description: str = (
        "搜索某公司的人才动态：招聘岗位、高管变动、团队扩张、高端人才引进、校企合作。"
        "精简搜索，每个公司只查3个最核心的方向。"
    )
    args_schema: Type[BaseModel] = TalentInput

    def _run(self, company: str) -> str:
        all_results = []

        # ── 精简策略：只搜3个最有效的方向，减少搜索量 ──
        # 策略1：招聘岗位（不限时间）
        hiring_queries = [
            f"{company} 招聘",
            f"{company} BOSS直聘 猎聘",
        ]
        for q in hiring_queries:
            results = multi_search(q, num=3, include_news=False, freshness="")
            for r in results:
                r["category"] = "hiring_long_term"
            all_results.extend(results)

        # 策略2：高管/核心团队/高端人才
        people_queries = [
            f"{company} CTO 首席科学家 加盟 引进",
            f"{company} 高管 技术负责人 变动",
        ]
        for q in people_queries:
            results = multi_search(q, num=3, include_news=True, freshness="oneweek")
            for r in results:
                r["category"] = "people_change"
            all_results.extend(results)

        # 策略3：校企合作/新研发中心
        coop_queries = [
            f"{company} 合作 联合实验室 研究院 研发中心",
        ]
        for q in coop_queries:
            results = multi_search(q, num=3, include_news=True, freshness="oneweek")
            for r in results:
                r["category"] = "cooperation"
            all_results.extend(results)

        # ── 去重 ──
        seen = set()
        unique = []
        for r in all_results:
            link = r.get("link", "")
            if link and link not in seen:
                seen.add(link)
                unique.append(r)

        if not unique:
            return json.dumps({
                "status": "no_results",
                "company": company,
                "note": "未找到该公司的招聘或人才相关信息"
            }, ensure_ascii=False)

        return json.dumps(unique[:15], ensure_ascii=False, indent=2)
