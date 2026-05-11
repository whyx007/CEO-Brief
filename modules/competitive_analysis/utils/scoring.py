"""
威胁评分引擎
"""

from config import THREAT_WEIGHTS


def compute_threat_score(score_breakdown: dict[str, float]) -> float:
    """
    加权计算总威胁分（0-100）
    score_breakdown: {"talent": 0-100, "market": 0-100, ...}
    """
    total = 0.0
    for dim, weight in THREAT_WEIGHTS.items():
        val = float(score_breakdown.get(dim, 0))
        val = max(0.0, min(100.0, val))
        total += weight * val
    return round(total, 2)


def parse_score(score_value) -> float:
    """
    Parse score value, handling both numeric and percentage string formats.
    Returns float value (0-100 range).
    """
    if score_value is None:
        return 0.0
    try:
        return float(str(score_value).replace('%', ''))
    except (TypeError, ValueError):
        return 0.0


def get_risk_level(score: float) -> str:
    """
    Classify threat score into risk levels.
    Returns emoji + Chinese label.
    """
    if score >= 70:
        return "🔴高危"
    elif score >= 45:
        return "🟡中度"
    else:
        return "🟢可控"


def sort_cards_by_score(cards: list[dict], reverse: bool = True, limit: int = None) -> list[dict]:
    """
    Sort competitor cards by score_total.

    Args:
        cards: List of competitor card dicts
        reverse: True for descending (highest first)
        limit: Optional limit on results (e.g., TOP 5, TOP 15)

    Returns:
        Sorted list of cards
    """
    sorted_cards = sorted(cards, key=lambda x: parse_score(x.get("score_total", 0)), reverse=reverse)
    return sorted_cards[:limit] if limit else sorted_cards