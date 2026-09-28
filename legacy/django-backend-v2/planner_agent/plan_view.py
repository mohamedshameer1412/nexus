"""
planner_agent/plan_view.py
GET /api/nexus/planner/plan/
Returns the study plan synchronously from the current Twin state.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from nexus_core.models import LearnerDigitalTwin
from analytics.algorithms import get_top_debt_topics


class StudyPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=request.user)
        mastery  = twin.verified_mastery or {}

        if not mastery:
            return Response({"plan": [], "total_minutes": 0, "message": "No mastery data yet."})

        debt_topics  = get_top_debt_topics(mastery, top_n=len(mastery))
        plan         = []
        total_minutes = 0

        for item in debt_topics:
            if item["debt"] <= 0:
                continue
            est = max(15, int(item["debt"] * 2))
            total_minutes += est

            if   item["debt"] >= 50: priority = "CRITICAL"
            elif item["debt"] >= 30: priority = "HIGH"
            elif item["debt"] >= 15: priority = "MEDIUM"
            else:                    priority = "LOW"

            plan.append({
                "topic_id":          item["topic_id"],
                "current_mastery":   item["mastery"],
                "debt":              item["debt"],
                "priority":          priority,
                "estimated_minutes": est,
            })

        return Response({"plan": plan, "total_minutes": total_minutes})
