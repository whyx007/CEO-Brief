"""
Pydantic 数据模型
"""

from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """一条竞情证据"""
    company: str = Field(description="公司名称")
    category: str = Field(description="类别：talent/market/tech/bidding/funding")
    title: str = Field(description="标题/要点")
    snippet: str = Field(description="摘要内容")
    url: str = Field(default="", description="来源链接")
    published_at: Optional[str] = Field(default=None, description="发布时间")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="置信度")
    source: str = Field(default="web", description="数据来源")


class CompanyIntel(BaseModel):
    """某公司的竞情汇总"""
    company: str
    aliases: List[str] = Field(default_factory=list)
    evidence: Dict[str, List[EvidenceItem]] = Field(
        default_factory=lambda: {
            "talent": [], "market": [], "tech": [], "bidding": [], "funding": []
        }
    )


class ThreatScore(BaseModel):
    """威胁评分"""
    company: str
    score_total: float = Field(ge=0, le=100)
    score_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="talent/market/tech/bidding/funding 各维度 0-100"
    )
    evidence_count: Dict[str, int] = Field(default_factory=dict)
    highlights: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="各维度核心要点（给 CEO 看的 bullet）"
    )
    risk_flags: List[str] = Field(
        default_factory=list,
        description="红旗警告"
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class BiweeklyReport(BaseModel):
    """周报完整结构"""
    window: str
    generated_at: str
    executive_summary: str = ""
    top3_threats: List[Dict] = Field(default_factory=list)
    radar_summary: Dict[str, str] = Field(default_factory=dict)
    action_items: List[str] = Field(default_factory=list)
    competitor_cards: List[ThreatScore] = Field(default_factory=list)
    evidence_store: List[EvidenceItem] = Field(default_factory=list)