from django.urls import path
from .views import TutorSessionView

urlpatterns = [
    path("session/", TutorSessionView.as_view(), name="nexus-tutor-session"),
]
