"""
analytics/mentor_view.py
GET /api/nexus/analytics/class-report/<classroom_id>/
Returns class weakness heatmap + at-risk students for teachers/mentors.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .mentor_agent import generate_class_report


class ClassReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, classroom_id):
        report = generate_class_report(classroom_id)
        return Response(report)
