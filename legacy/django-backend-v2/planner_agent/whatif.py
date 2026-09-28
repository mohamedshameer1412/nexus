"""
planner_agent/whatif.py
What-If Learning Simulator.
Compares two study paths and recommends the higher-value option.
"""
from analytics.algorithms import REQUIRED_MASTERY
from django.conf import settings


def simulate_whatif(
    topic_a_id: str,
    topic_b_id: str,
    verified_mastery: dict,
    propagation_map: dict = None,
    criticality_map: dict = None,
) -> dict:
    """
    "If I study Topic A vs Topic B in my next session, which gives more value?"

    Scoring per topic:
      raw_gap  = max(0, 70 - mastery)
      value    = raw_gap * criticality * (1 + propagation * weight)

    Higher value = higher priority recommendation.

    Returns: {
        "recommendation": "A" or "B",
        "topic_a": {...metrics...},
        "topic_b": {...metrics...},
        "reason":  human-readable explanation
    }
    """
    WEIGHT = settings.NEXUS.get("DEBT_PROPAGATION_WEIGHT", 0.4)
    propagation_map = propagation_map or {}
    criticality_map = criticality_map or {}

    def score(topic_id):
        mastery     = verified_mastery.get(topic_id, 0.0)
        gap         = max(0, REQUIRED_MASTERY - mastery)
        crit        = criticality_map.get(topic_id, 1.0)
        propagation = propagation_map.get(topic_id, 0)
        return round(gap * crit * (1 + propagation * WEIGHT), 2), mastery, gap

    score_a, mastery_a, gap_a = score(topic_a_id)
    score_b, mastery_b, gap_b = score(topic_b_id)

    winner = "A" if score_a >= score_b else "B"
    winner_id   = topic_a_id if winner == "A" else topic_b_id
    loser_id    = topic_b_id if winner == "A" else topic_a_id
    winner_gap  = gap_a if winner == "A" else gap_b
    winner_prop = propagation_map.get(winner_id, 0)

    reason = (
        f"Study '{winner_id}' first. "
        f"It has a {winner_gap:.0f}-point gap from required level"
        + (f" and unblocks {winner_prop} downstream topic(s)." if winner_prop > 0 else ".")
    )

    return {
        "recommendation": winner,
        "recommended_topic": winner_id,
        "reason": reason,
        "topic_a": {
            "id": topic_a_id, "mastery": mastery_a,
            "gap": gap_a, "value_score": score_a,
        },
        "topic_b": {
            "id": topic_b_id, "mastery": mastery_b,
            "gap": gap_b, "value_score": score_b,
        },
    }
