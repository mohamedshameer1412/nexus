"""
users/career_gap_view.py
POST /api/nexus/twin/career-gap/
Body: { "job_description": "..." }
Returns: matched/missing skills against Digital Twin
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from nexus_core.models import LearnerDigitalTwin
from .career_gap import analyze_career_gap


class CareerGapView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        jd = request.data.get("job_description", "").strip()
        if not jd:
            return Response({"error": "Provide job_description"}, status=400)
        if len(jd) < 50:
            return Response({"error": "Job description too short (min 50 chars)"}, status=400)

        twin, _ = LearnerDigitalTwin.objects.get_or_create(user=request.user)
        result  = analyze_career_gap(
            verified_skills = twin.verified_skills or [],
            job_description = jd,
        )
        return Response(result)
