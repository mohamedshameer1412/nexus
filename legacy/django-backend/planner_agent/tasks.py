"""
planner_agent/tasks.py
Celery task: generate_study_plan
Sorts topics by Learning Debt score (highest first) to produce an ordered study plan.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def generate_study_plan(self, user_id: str):
    """
    1. Load the student Digital Twin
    2. Sort topics by debt (gap * propagation) descending
    3. Return ordered study plan with time estimates
    4. Log the decision
    """
    try:
        from django.contrib.auth import get_user_model
        from nexus_core.models import LearnerDigitalTwin, AgentDecisionLog
        from analytics.algorithms import get_top_debt_topics

        User = get_user_model()
        user = User.objects.get(id=user_id)
        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=user)

        mastery = twin.verified_mastery or {}
        if not mastery:
            return {"status": "no_mastery_data", "plan": []}

        # Get topics sorted by debt
        debt_topics = get_top_debt_topics(mastery, top_n=len(mastery))

        # Build plan: estimate study time per topic
        plan = []
        total_minutes = 0
        for item in debt_topics:
            if item["debt"] <= 0:
                continue
            # Rough estimate: 1 point of debt ≈ 2 minutes of study
            est_minutes = max(15, int(item["debt"] * 2))
            total_minutes += est_minutes
            plan.append({
                "topic_id":       item["topic_id"],
                "current_mastery": item["mastery"],
                "debt":           item["debt"],
                "estimated_minutes": est_minutes,
                "priority":       _priority_label(item["debt"]),
            })

        AgentDecisionLog.objects.create(
            user=user,
            twin=twin,
            agent_name="planner",
            trigger="generate_study_plan",
            input_state={"mastery_topics": len(mastery)},
            decision=f"Generated study plan: {len(plan)} topics, ~{total_minutes} min total",
            output={"plan": plan, "total_minutes": total_minutes},
        )

        logger.info(f"[PlannerAgent] Study plan generated for user {user_id}: {len(plan)} topics")
        return {
            "status": "success",
            "plan": plan,
            "total_minutes": total_minutes,
        }

    except Exception as exc:
        logger.error(f"[PlannerAgent] generate_study_plan failed: {exc}")
        raise self.retry(exc=exc)


def _priority_label(debt: float) -> str:
    if debt >= 50: return "CRITICAL"
    if debt >= 30: return "HIGH"
    if debt >= 15: return "MEDIUM"
    return "LOW"
