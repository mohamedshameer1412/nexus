"""
analytics/mentor_agent.py
Mentor Agent — class-level intelligence layer.
Aggregates Digital Twin data across all students in a classroom/cohort.
Produces:
  1. Class weakness heatmap — which topics the whole class is failing
  2. At-risk student list — students with dangerously high debt or drift
  3. Intervention recommendations for teachers/mentors
"""
import logging
from typing import List, Dict, Optional
from django.db.models import Avg, Count

logger = logging.getLogger(__name__)


def get_class_weakness_heatmap(classroom_id: str) -> dict:
    """
    Aggregate verified_mastery across all students in a classroom.
    Returns per-topic average mastery and how many students are below threshold.

    Returns: {
        topic_id: {
            avg_mastery: float,
            below_threshold_count: int,
            below_threshold_pct: float,
            severity: str
        }
    }
    """
    try:
        from users.models import Classroom
        from nexus_core.models import LearnerDigitalTwin

        classroom = Classroom.objects.get(id=classroom_id)
        student_ids = classroom.students.values_list("id", flat=True)
        twins = LearnerDigitalTwin.objects.filter(user_id__in=student_ids)

        topic_data: Dict[str, list] = {}
        total_students = twins.count()

        for twin in twins:
            for topic_id, mastery_pct in (twin.verified_mastery or {}).items():
                if topic_id not in topic_data:
                    topic_data[topic_id] = []
                topic_data[topic_id].append(mastery_pct)

        heatmap = {}
        THRESHOLD = 70.0

        for topic_id, scores in topic_data.items():
            avg   = sum(scores) / len(scores)
            below = sum(1 for s in scores if s < THRESHOLD)
            pct   = (below / total_students * 100) if total_students else 0

            if pct >= 60:   severity = "CRITICAL"
            elif pct >= 40: severity = "HIGH"
            elif pct >= 20: severity = "MEDIUM"
            else:            severity = "LOW"

            heatmap[topic_id] = {
                "avg_mastery":           round(avg, 2),
                "below_threshold_count": below,
                "below_threshold_pct":   round(pct, 2),
                "severity":              severity,
                "student_count":         len(scores),
            }

        logger.info(f"[MentorAgent] Heatmap for classroom {classroom_id}: {len(heatmap)} topics")
        return heatmap

    except Exception as e:
        logger.error(f"[MentorAgent] get_class_weakness_heatmap failed: {e}")
        return {}


def get_at_risk_students(
    classroom_id: str,
    debt_threshold: float = 60.0,
    drift_threshold: float = 40.0,
    risk_threshold: float  = 70.0,
) -> List[dict]:
    """
    Identify students who need immediate intervention based on:
    - High learning debt score (struggling broadly)
    - High concept drift (forgetting quickly)
    - High failure risk score

    Returns: list of {student_id, username, debt, drift, risk, flags}
    """
    try:
        from users.models import Classroom
        from nexus_core.models import LearnerDigitalTwin

        classroom   = Classroom.objects.get(id=classroom_id)
        student_ids = classroom.students.values_list("id", flat=True)
        twins = LearnerDigitalTwin.objects.filter(
            user_id__in=student_ids
        ).select_related("user")

        at_risk = []
        for twin in twins:
            flags = []
            if twin.learning_debt_score >= debt_threshold:
                flags.append(f"High debt ({twin.learning_debt_score:.0f})")
            if twin.concept_drift_score >= drift_threshold:
                flags.append(f"High drift ({twin.concept_drift_score:.0f})")
            if twin.failure_risk_score >= risk_threshold:
                flags.append(f"High failure risk ({twin.failure_risk_score:.0f})")

            if flags:
                at_risk.append({
                    "student_id": str(twin.user.id),
                    "username":   twin.user.username,
                    "email":      twin.user.email,
                    "debt":       round(twin.learning_debt_score, 2),
                    "drift":      round(twin.concept_drift_score, 2),
                    "risk":       round(twin.failure_risk_score, 2),
                    "flags":      flags,
                    "severity":   "CRITICAL" if len(flags) >= 2 else "HIGH",
                })

        at_risk.sort(key=lambda x: x["debt"] + x["drift"] + x["risk"], reverse=True)
        logger.info(f"[MentorAgent] {len(at_risk)} at-risk students in classroom {classroom_id}")
        return at_risk

    except Exception as e:
        logger.error(f"[MentorAgent] get_at_risk_students failed: {e}")
        return []


def generate_class_report(classroom_id: str) -> dict:
    """
    Full mentor report combining heatmap + at-risk students + recommendations.
    This is what the teacher/mentor dashboard calls.
    """
    heatmap   = get_class_weakness_heatmap(classroom_id)
    at_risk   = get_at_risk_students(classroom_id)

    # Top 5 most critical class-wide topics
    critical_topics = sorted(
        [(tid, data) for tid, data in heatmap.items() if data["severity"] in ("CRITICAL", "HIGH")],
        key=lambda x: x[1]["below_threshold_pct"],
        reverse=True,
    )[:5]

    recommendations = []
    for topic_id, data in critical_topics:
        recommendations.append(
            f"Schedule a revision session on '{topic_id}' — "
            f"{data['below_threshold_count']} students ({data['below_threshold_pct']:.0f}%) "
            f"are below the 70% threshold."
        )

    if at_risk:
        recommendations.append(
            f"{len(at_risk)} students need 1-on-1 attention: "
            + ", ".join(s["username"] for s in at_risk[:3])
            + ("..." if len(at_risk) > 3 else "")
        )

    return {
        "classroom_id":    classroom_id,
        "heatmap":         heatmap,
        "at_risk_students": at_risk,
        "critical_topics": [t[0] for t in critical_topics],
        "recommendations": recommendations,
        "summary": {
            "total_topics_tracked": len(heatmap),
            "critical_topics_count": sum(1 for d in heatmap.values() if d["severity"] == "CRITICAL"),
            "at_risk_count": len(at_risk),
        },
    }
