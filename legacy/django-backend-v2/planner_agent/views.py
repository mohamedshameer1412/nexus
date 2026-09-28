"""
planner_agent/views.py
POST /api/nexus/planner/whatif/
Body: { "topic_a": "recursion", "topic_b": "graph_traversal" }
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from nexus_core.models import LearnerDigitalTwin
from .whatif import simulate_whatif


class WhatIfView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        topic_a = request.data.get("topic_a", "").strip()
        topic_b = request.data.get("topic_b", "").strip()

        if not topic_a or not topic_b:
            return Response({"error": "Provide both topic_a and topic_b"}, status=400)
        if topic_a == topic_b:
            return Response({"error": "Topics must be different"}, status=400)

        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=request.user)
        result = simulate_whatif(
            topic_a_id=topic_a,
            topic_b_id=topic_b,
            verified_mastery=twin.verified_mastery or {},
        )
        return Response(result)
