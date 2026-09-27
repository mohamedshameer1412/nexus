"""
nexus_core/urls.py — Mounted at /api/nexus/twin/
"""
from django.urls import path
from .views import DigitalTwinView, AgentDecisionLogView
from users.career_gap_view import CareerGapView

urlpatterns = [
    path("",            DigitalTwinView.as_view(),      name="nexus-twin"),
    path("logs/",       AgentDecisionLogView.as_view(),  name="nexus-twin-logs"),
    path("career-gap/", CareerGapView.as_view(),         name="nexus-career-gap"),
]
