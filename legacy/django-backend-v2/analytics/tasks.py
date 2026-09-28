"""
analytics/tasks.py
Celery task: update_digital_twin
Fires after every quiz session completes.
Full pipeline:
  1. Compute topic mastery from session responses (EMA merge)
  2. Compute Learning Debt Score
  3. Compute Confidence-Ability Gap
  4. Run Concept Drift Detection vs previous snapshot
  5. Run At-Risk Prediction (Random Forest / rule-based)
  6. Log AgentDecisionLog
"""
from celery import shared_task
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def update_digital_twin(self, session_id: str):
    try:
        from quiz.models import QuizSession, Response
        from nexus_core.models import LearnerDigitalTwin, AgentDecisionLog
        from .algorithms import (
            compute_topic_mastery,
            compute_learning_debt,
            compute_confidence_gap,
        )
        from ml_engine.concept_drift import compute_overall_drift_score, detect_concept_drift
        from ml_engine.weak_topic_predictor import predict_at_risk_topics

        session = QuizSession.objects.select_related("quiz", "user").get(id=session_id)
        user    = session.user
        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=user)

        # ── Step 1: responses ────────────────────────────────────────────────
        responses = Response.objects.filter(session=session).select_related("question")
        if not responses.exists():
            logger.warning(f"[AnalyticsAgent] No responses for session {session_id}")
            return {"status": "skipped", "reason": "no responses"}

        # ── Step 2: compute mastery & EMA merge ──────────────────────────────
        session_mastery  = compute_topic_mastery(responses)
        ALPHA            = 0.3
        prev_mastery     = dict(twin.verified_mastery or {})  # snapshot before update
        current          = prev_mastery.copy()

        for topic_id, new_score in session_mastery.items():
            old_score = current.get(topic_id, new_score)
            current[topic_id] = round((1 - ALPHA) * old_score + ALPHA * new_score, 2)

        twin.verified_mastery = current

        # ── Step 3: Debt + Confidence Gap ────────────────────────────────────
        twin.learning_debt_score = compute_learning_debt(current)
        twin.confidence_gap      = compute_confidence_gap(
            current, twin.self_reported_mastery or {}
        )

        # ── Step 4: Concept Drift ────────────────────────────────────────────
        if prev_mastery:
            drift_score    = compute_overall_drift_score(current, prev_mastery)
            drifted_topics = detect_concept_drift(current, prev_mastery)
            twin.concept_drift_score = drift_score
            twin.retention_scores    = current
        else:
            drifted_topics = []

        # ── Step 5: At-Risk Prediction ───────────────────────────────────────
        twin_state = {
            "verified_mastery":   current,
            "retention_scores":   twin.retention_scores or {},
            "concept_drift_score": twin.concept_drift_score,
        }
        at_risk_topics = predict_at_risk_topics(twin_state, top_n=3)

        # Compute failure risk score from at-risk predictions
        if at_risk_topics:
            avg_risk = sum(t["risk_score"] for t in at_risk_topics) / len(at_risk_topics)
            twin.failure_risk_score = round(avg_risk * 100, 2)

        twin.save()

        # ── Step 6: Log ──────────────────────────────────────────────────────
        with transaction.atomic():
            AgentDecisionLog.objects.create(
                user=user,
                twin=twin,
                agent_name="analytics",
                trigger=f"quiz_session:{session_id}",
                input_state={
                    "session_id":     session_id,
                    "response_count": responses.count(),
                },
                decision=(
                    f"Updated {len(session_mastery)} topics. "
                    f"Debt={twin.learning_debt_score:.1f}, "
                    f"Drift={twin.concept_drift_score:.1f}, "
                    f"Risk={twin.failure_risk_score:.1f}. "
                    f"{len(drifted_topics)} drifted topics detected."
                ),
                output={
                    "topics_updated":   list(session_mastery.keys()),
                    "debt_score":       twin.learning_debt_score,
                    "drift_score":      twin.concept_drift_score,
                    "failure_risk":     twin.failure_risk_score,
                    "drifted_topics":   [d["topic_id"] for d in drifted_topics],
                    "at_risk_topics":   [t["topic_id"] for t in at_risk_topics],
                },
            )

        logger.info(
            f"[AnalyticsAgent] Twin updated: user={user.id}, "
            f"topics={len(session_mastery)}, debt={twin.learning_debt_score:.1f}"
        )
        return {
            "status":         "success",
            "user_id":        str(user.id),
            "topics_updated": len(session_mastery),
            "debt_score":     twin.learning_debt_score,
            "drift_score":    twin.concept_drift_score,
            "at_risk_topics": at_risk_topics,
        }

    except Exception as exc:
        logger.error(f"[AnalyticsAgent] update_digital_twin failed: {exc}")
        raise self.retry(exc=exc)
