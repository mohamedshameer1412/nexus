"""
nexus_core/views.py
Endpoints:
  GET  /api/nexus/twin/           -> read own Digital Twin
  PATCH /api/nexus/twin/          -> update self-reported mastery + career goal
  GET  /api/nexus/twin/logs/      -> last 20 agent decision logs for this user
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import LearnerDigitalTwin, AgentDecisionLog
from .serializers import (
    DigitalTwinSerializer,
    SelfMasteryUpdateSerializer,
    AgentDecisionLogSerializer,
)


class DigitalTwinView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the authenticated student's Digital Twin."""
        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=request.user)
        serializer = DigitalTwinSerializer(twin)
        return Response(serializer.data)

    def patch(self, request):
        """
        Student updates their self-reported mastery and/or career goal.
        System does NOT trust these values as verified mastery.
        They are stored separately and used to compute the Confidence-Ability Gap.
        """
        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=request.user)
        serializer = SelfMasteryUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Update self-reported mastery (merge, not replace)
        updated_mastery = twin.self_reported_mastery or {}
        updated_mastery.update(data.get("self_reported_mastery", {}))
        twin.self_reported_mastery = updated_mastery

        if "career_goal" in data:
            twin.career_goal = data["career_goal"]
        if "target_exam_score" in data:
            twin.target_exam_score = data["target_exam_score"]

        # Recompute confidence-ability gap immediately
        twin.confidence_gap = _compute_confidence_gap(
            twin.verified_mastery,
            twin.self_reported_mastery,
        )

        twin.save()
        return Response(DigitalTwinSerializer(twin).data)


class AgentDecisionLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the last 20 agent decisions for the authenticated student."""
        logs = AgentDecisionLog.objects.filter(user=request.user).order_by("-timestamp")[:20]
        serializer = AgentDecisionLogSerializer(logs, many=True)
        return Response(serializer.data)


# ── helpers ──────────────────────────────────────────────────────────────────

def _compute_confidence_gap(verified: dict, self_reported: dict) -> dict:
    """
    For each topic that exists in BOTH dicts, compute:
      gap = self_reported_pct - verified_pct
    Positive gap  -> student overestimates (overconfident)
    Negative gap  -> student underestimates (underconfident)
    """
    gap = {}
    all_topics = set(verified.keys()) | set(self_reported.keys())
    for topic_id in all_topics:
        v = verified.get(topic_id, 0.0)
        s = self_reported.get(topic_id, 0.0)
        gap[topic_id] = round(s - v, 2)
    return gap
