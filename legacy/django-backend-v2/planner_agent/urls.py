from django.urls import path
from .views import WhatIfView
from .plan_view import StudyPlanView

urlpatterns = [
    path("whatif/", WhatIfView.as_view(),    name="nexus-whatif"),
    path("plan/",   StudyPlanView.as_view(), name="nexus-plan"),
]
