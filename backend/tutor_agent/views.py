"""
tutor_agent/views.py
GET  /api/nexus/tutor/session/?topic_id=<id>
     -> returns content cards for the requested topic
POST /api/nexus/tutor/session/
     -> triggers async Celery task and returns task_id for WebSocket
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ml_engine.faiss_index import query_index
from nexus_core.models import LearnerDigitalTwin
from analytics.algorithms import get_top_debt_topics


class TutorSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Synchronous: return content cards immediately."""
        topic_id = request.query_params.get("topic_id", "").strip()
        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=request.user)

        if not topic_id:
            top = get_top_debt_topics(twin.verified_mastery or {}, top_n=1)
            topic_id = top[0]["topic_id"] if top else "general"

        chunks = query_index(topic_id, top_k=5)
        cards = [
            {
                "card_index": i + 1,
                "topic":      c.get("topic", topic_id),
                "text":       c.get("text", ""),
                "source":     c.get("source", "syllabus"),
                "relevance":  round(1 / (1 + c.get("score", 1)), 4),
            }
            for i, c in enumerate(chunks)
        ] or [{
            "card_index": 1,
            "topic": topic_id,
            "text": f"Upload your syllabus to get AI content for '{topic_id}'.",
            "source": "system",
            "relevance": 0.0,
        }]

        return Response({
            "topic_id":      topic_id,
            "content_cards": cards,
            "twin_debt":     twin.learning_debt_score,
        })
