"""
evaluator_agent/tasks.py
Celery task: evaluate_session
Fires in parallel with update_digital_twin after quiz submission.
Identifies root causes for every topic the student underperformed on.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def evaluate_session(self, session_id: str):
    """
    1. Find all topics the student scored below threshold this session
    2. Load the prerequisite graph for their syllabus
    3. For each weak topic, find root cause via backwards BFS
    4. Log the diagnosis to AgentDecisionLog
    Returns: list of root-cause diagnoses
    """
    try:
        from quiz.models import QuizSession, Response
        from nexus_core.models import LearnerDigitalTwin, AgentDecisionLog
        from analytics.algorithms import compute_topic_mastery
        from syllabus.models import SyllabusUpload
        from .graph import build_prerequisite_graph, find_root_cause

        session = QuizSession.objects.select_related("quiz", "user").get(id=session_id)
        user = session.user
        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=user)

        # Step 1 — get session mastery
        responses = Response.objects.filter(session=session).select_related("question")
        session_mastery = compute_topic_mastery(responses)

        THRESHOLD = 70.0
        weak_topics = [tid for tid, pct in session_mastery.items() if pct < THRESHOLD]

        if not weak_topics:
            return {"status": "no_weak_topics", "session_id": session_id}

        # Step 2 — build prerequisite graph from latest syllabus
        topics_data = _load_topics_for_user(user)
        G = build_prerequisite_graph(topics_data)

        # Step 3 — diagnose each weak topic
        diagnoses = []
        for topic_id in weak_topics:
            result = find_root_cause(
                G=G,
                failed_topic_id=topic_id,
                verified_mastery=twin.verified_mastery,
                mastery_threshold=THRESHOLD,
            )
            diagnoses.append(result)

        # Step 4 — log the decision
        summary = f"Found {len(diagnoses)} root-cause chains for session {session_id}"
        AgentDecisionLog.objects.create(
            user=user,
            twin=twin,
            agent_name="evaluator",
            trigger=f"quiz_session:{session_id}",
            input_state={
                "session_id": session_id,
                "weak_topics": weak_topics,
            },
            decision=summary,
            output={"diagnoses": diagnoses},
        )

        logger.info(f"[EvaluatorAgent] {summary}")
        return {"status": "success", "diagnoses": diagnoses}

    except Exception as exc:
        logger.error(f"[EvaluatorAgent] evaluate_session failed: {exc}")
        raise self.retry(exc=exc)


def _load_topics_for_user(user) -> list:
    """
    Load syllabus topics for the user as a list of dicts with prerequisite info.
    Falls back to empty list if no syllabus uploaded yet.
    """
    try:
        from syllabus.models import SyllabusUpload, Topic
        latest = SyllabusUpload.objects.filter(user=user).order_by("-uploaded_at").first()
        if not latest:
            return []

        topics = Topic.objects.filter(syllabus=latest).prefetch_related("prerequisites")
        return [
            {
                "id": str(t.id),
                "name": t.name,
                "prerequisites": [str(p.id) for p in t.prerequisites.all()],
            }
            for t in topics
        ]
    except Exception as e:
        logger.warning(f"[EvaluatorAgent] Could not load topics: {e}")
        return []
