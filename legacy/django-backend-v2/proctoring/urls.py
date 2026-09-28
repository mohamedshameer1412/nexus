from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProctoringViewSet

router = DefaultRouter()
router.register(r'events', ProctoringViewSet, basename='proctoring-event')

urlpatterns = [
    path('', include(router.urls)),
]
