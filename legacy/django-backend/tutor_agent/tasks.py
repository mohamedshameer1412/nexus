"""
tutor_agent/tasks.py
Celery task: prepare_tutor_session
Uses FAISS to retrieve the most relevant syllabus chunks for a topic.
Returns content cards the frontend displays during a tutor session.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def prepare_tutor_session(self, user_id: str, topic_id: str = None):
    """
    1. Identify the highest-debt topic for this student (if topic_id not given)
    2. Query FAISS index for top-5 relevant content chunks
    3. Return structured content cards for the frontend
    4. Log agent decision
    """
    try:
        from django.contrib.auth import get_user_model
        from nexus_core.models import LearnerDigitalTwin, AgentDecisionLog
        from analytics.algorithms import get_top_debt_topics
        from ml_engine.faiss_index import query_index

        User  = get_user_model()
        user  = User.objects.get(id=user_id)
        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=user)

        # ── Step 1: determine focus topic ────────────────────────────────────
        if not topic_id:
            top_debt = get_top_debt_topics(twin.verified_mastery or {}, top_n=1)
            topic_id = top_debt[0]["topic_id"] if top_debt else "general"

        # ── Step 2: FAISS retrieval ───────────────────────────────────────────
        chunks = query_index(query_text=topic_id, top_k=5)

        # ── Step 3: format content cards ─────────────────────────────────────
        content_cards = []
        for i, chunk in enumerate(chunks):
            content_cards.append({
                "card_index": i + 1,
                "topic":      chunk.get("topic", topic_id),
                "text":       chunk.get("text", ""),
                "source":     chunk.get("source", "syllabus"),
                "relevance":  round(1 / (1 + chunk.get("score", 1)), 4),
            })

        if not content_cards:
            # Fallback: no FAISS index yet, return a placeholder card
            content_cards = [{
                "card_index": 1,
                "topic":      topic_id,
                "text":       (
                    f"No indexed content found for '{topic_id}'. "
                    "Upload your syllabus to enable AI-powered content retrieval."
                ),
                "source": "system",
                "relevance": 0.0,
            }]

        # ── Step 4: log decision ──────────────────────────────────────────────
        AgentDecisionLog.objects.create(
            user=user,
            twin=twin,
            agent_name="tutor",
            trigger=f"prepare_tutor_session:topic={topic_id}",
            input_state={"user_id": user_id, "topic_id": topic_id},
            decision=f"Retrieved {len(content_cards)} content chunks for topic '{topic_id}'",
            output={"topic_id": topic_id, "card_count": len(content_cards)},
        )

        logger.info(f"[TutorAgent] {len(content_cards)} cards prepared for user {user_id}, topic '{topic_id}'")
        return {
            "status":        "success",
            "topic_id":      topic_id,
            "content_cards": content_cards,
        }

    except Exception as exc:
        logger.error(f"[TutorAgent] prepare_tutor_session failed: {exc}")
        raise self.retry(exc=exc)


@shared_task
def build_faiss_index_for_user(syllabus_upload_id: str):
    """
    Background task: rebuild the FAISS index after a new syllabus upload.
    Called by the syllabus upload pipeline.
    """
    from ml_engine.faiss_index import build_index_from_syllabus
    result = build_index_from_syllabus(syllabus_upload_id)
    logger.info(f"[TutorAgent] FAISS index rebuilt: {result}")
    return result
