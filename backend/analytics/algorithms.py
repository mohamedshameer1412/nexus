"""
analytics/algorithms.py
Core NEXUS algorithms — no ML, pure Python math.
  1. compute_topic_mastery   — correctness rate per topic from quiz responses
  2. compute_learning_debt   — weighted gap with propagation factor
  3. compute_confidence_gap  — self-reported vs verified mastery delta
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Required mastery level (%) to consider a topic "learned"
REQUIRED_MASTERY = 70.0


def compute_topic_mastery(responses) -> Dict[str, float]:
    """
    Group quiz responses by topic.
    Mastery = (correct responses / total responses) * 100 per topic.
    Returns: {topic_id: mastery_pct}
    """
    topic_stats: Dict[str, dict] = {}

    for resp in responses:
        topic_id = None

        # Try to get topic from question
        q = resp.question
        if hasattr(q, "subtopic") and q.subtopic:
            topic_id = str(q.subtopic)
        elif hasattr(q, "topic") and q.topic:
            topic_id = str(q.topic)
        else:
            topic_id = "uncategorized"

        if topic_id not in topic_stats:
            topic_stats[topic_id] = {"correct": 0, "total": 0}

        topic_stats[topic_id]["total"] += 1

        # is_correct may be stored as boolean or computed from score
        is_correct = getattr(resp, "is_correct", None)
        if is_correct is None:
            # Fallback: compare marks_obtained to question marks
            obtained = getattr(resp, "marks_obtained", 0) or 0
            total_marks = getattr(resp.question, "marks", 1) or 1
            is_correct = obtained >= (total_marks * 0.5)  # 50% threshold

        if is_correct:
            topic_stats[topic_id]["correct"] += 1

    mastery = {}
    for topic_id, stats in topic_stats.items():
        if stats["total"] > 0:
            mastery[topic_id] = round(
                (stats["correct"] / stats["total"]) * 100, 2
            )

    return mastery


def compute_learning_debt(
    verified_mastery: Dict[str, float],
    criticality_map: Dict[str, float] = None,
    propagation_map: Dict[str, int] = None,
) -> float:
    """
    Learning Debt Score (0–100 overall).

    Formula per topic:
      raw_debt = max(0, REQUIRED_MASTERY - mastery_pct)
      debt_i   = raw_debt * criticality * (1 + propagation_factor * WEIGHT)

    Final score = average of all topic debts, clamped to 0–100.

    Args:
        verified_mastery:  {topic_id: mastery_pct}
        criticality_map:   {topic_id: weight 0.0–2.0} (default 1.0 for all)
        propagation_map:   {topic_id: n_downstream_topics} (default 0 for all)

    Returns: float 0.0–100.0
    """
    from django.conf import settings
    WEIGHT = settings.NEXUS.get("DEBT_PROPAGATION_WEIGHT", 0.4)

    if not verified_mastery:
        return 0.0

    criticality_map  = criticality_map  or {}
    propagation_map  = propagation_map  or {}
    debts = []

    for topic_id, mastery_pct in verified_mastery.items():
        raw_gap     = max(0.0, REQUIRED_MASTERY - mastery_pct)
        criticality = criticality_map.get(topic_id, 1.0)
        propagation = propagation_map.get(topic_id, 0)

        topic_debt  = raw_gap * criticality * (1 + propagation * WEIGHT)
        debts.append(topic_debt)

    if not debts:
        return 0.0

    # Normalize: max possible raw_gap is 70 (0% mastery, criticality=1, propagation=0)
    # We scale so 70 raw = 100 debt
    raw_avg = sum(debts) / len(debts)
    normalized = min(100.0, round((raw_avg / 70.0) * 100, 2))
    return normalized


def compute_confidence_gap(
    verified_mastery: Dict[str, float],
    self_reported_mastery: Dict[str, float],
) -> Dict[str, float]:
    """
    Confidence-Ability Gap per topic.
      gap > 0  -> student overestimates (overconfident — Dunning-Kruger zone)
      gap < 0  -> student underestimates (underconfident — imposter syndrome zone)
      gap = 0  -> well-calibrated

    Returns: {topic_id: gap_value}
    """
    gap = {}
    all_topics = set(verified_mastery.keys()) | set(self_reported_mastery.keys())

    for topic_id in all_topics:
        v = verified_mastery.get(topic_id, 0.0)
        s = self_reported_mastery.get(topic_id, 0.0)
        gap[topic_id] = round(s - v, 2)

    return gap


def get_top_debt_topics(
    verified_mastery: Dict[str, float],
    top_n: int = 5,
) -> list:
    """
    Returns top N topics sorted by raw gap (highest debt first).
    Used by the Planner Agent to prioritize study order.
    """
    gaps = [
        {
            "topic_id": tid,
            "mastery": pct,
            "debt": round(max(0, REQUIRED_MASTERY - pct), 2),
        }
        for tid, pct in verified_mastery.items()
    ]
    gaps.sort(key=lambda x: x["debt"], reverse=True)
    return gaps[:top_n]
