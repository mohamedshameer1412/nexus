"""
ml_engine/concept_drift.py
Detects when a student's mastery of a previously-learned concept has degraded
between sessions (forgetting curve effect).

Drift detection triggers a re-intervention — NEXUS adds the topic back to
the study plan at HIGH priority even though it was previously mastered.
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def detect_concept_drift(
    current_mastery:  Dict[str, float],
    previous_mastery: Dict[str, float],
    threshold: float = None,
) -> List[dict]:
    """
    Compare current mastery snapshot against a previous snapshot.
    Any topic whose mastery dropped by >= threshold points is flagged.

    Args:
        current_mastery:  {topic_id: pct} — from latest Twin update
        previous_mastery: {topic_id: pct} — from Twin state N sessions ago
        threshold: float — minimum drop to flag (default from NEXUS settings)

    Returns: list of {topic_id, previous, current, drop, severity}
    """
    from django.conf import settings
    if threshold is None:
        threshold = settings.NEXUS.get("CONCEPT_DRIFT_THRESHOLD", 10.0)

    drifted = []

    for topic_id, current_pct in current_mastery.items():
        prev_pct = previous_mastery.get(topic_id)
        if prev_pct is None:
            continue  # topic wasn't tracked before — skip

        drop = prev_pct - current_pct  # positive = degradation
        if drop >= threshold:
            drifted.append({
                "topic_id": topic_id,
                "previous": round(prev_pct, 2),
                "current":  round(current_pct, 2),
                "drop":     round(drop, 2),
                "severity": _severity(drop),
            })

    drifted.sort(key=lambda x: x["drop"], reverse=True)
    return drifted


def _severity(drop: float) -> str:
    if drop >= 30: return "CRITICAL"
    if drop >= 20: return "HIGH"
    if drop >= 10: return "MEDIUM"
    return "LOW"


def compute_overall_drift_score(
    current_mastery:  Dict[str, float],
    previous_mastery: Dict[str, float],
) -> float:
    """
    Single float 0–100 representing overall concept drift.
    Used to update twin.concept_drift_score after each session.
    """
    if not previous_mastery or not current_mastery:
        return 0.0

    drops = []
    for topic_id, prev_pct in previous_mastery.items():
        curr_pct = current_mastery.get(topic_id, prev_pct)
        drop = max(0.0, prev_pct - curr_pct)
        drops.append(drop)

    if not drops:
        return 0.0

    avg_drop = sum(drops) / len(drops)
    # Normalise: a 30-point average drop = 100 drift score
    return min(100.0, round((avg_drop / 30.0) * 100, 2))


def snapshot_mastery(user_id: str) -> Dict[str, float]:
    """
    Save current Twin mastery as a snapshot to compare against next session.
    Stored in MasterySnapshot model.
    """
    try:
        from nexus_core.models import LearnerDigitalTwin
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=user)
        return dict(twin.verified_mastery or {})
    except Exception as e:
        logger.error(f"[ConceptDrift] snapshot_mastery failed: {e}")
        return {}


def check_and_update_drift(
    user_id: str,
    current_mastery: Dict[str, float],
    previous_snapshot: Dict[str, float],
) -> dict:
    """
    Full drift check pipeline:
    1. Detect drifted topics
    2. Compute overall drift score
    3. Update twin.concept_drift_score
    4. Log AgentDecisionLog if any drift found

    Returns: {drift_score, drifted_topics, re_intervention_topics}
    """
    from nexus_core.models import LearnerDigitalTwin, AgentDecisionLog
    from django.contrib.auth import get_user_model

    User  = get_user_model()
    user  = User.objects.get(id=user_id)
    twin, _ = LearnerDigitalTwin.objects.get_or_create(user=user)

    drifted      = detect_concept_drift(current_mastery, previous_snapshot)
    drift_score  = compute_overall_drift_score(current_mastery, previous_snapshot)

    twin.concept_drift_score = drift_score
    twin.retention_scores    = current_mastery  # update retention as proxy
    twin.save(update_fields=["concept_drift_score", "retention_scores"])

    re_intervention = [d["topic_id"] for d in drifted if d["severity"] in ("CRITICAL", "HIGH")]

    if drifted:
        AgentDecisionLog.objects.create(
            user=user,
            twin=twin,
            agent_name="analytics",
            trigger="concept_drift_check",
            input_state={"previous_topics": len(previous_snapshot)},
            decision=(
                f"Concept drift detected: {len(drifted)} topics degraded. "
                f"Overall drift score: {drift_score:.1f}. "
                f"Re-intervening on: {re_intervention}"
            ),
            output={
                "drift_score":       drift_score,
                "drifted_topics":    drifted,
                "re_intervention":   re_intervention,
            },
        )
        logger.warning(
            f"[ConceptDrift] user={user_id}: {len(drifted)} topics drifted, "
            f"score={drift_score:.1f}"
        )

    return {
        "drift_score":          drift_score,
        "drifted_topics":       drifted,
        "re_intervention_topics": re_intervention,
    }
