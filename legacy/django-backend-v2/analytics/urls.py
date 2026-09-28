from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalyticsViewSet
from .mentor_view import ClassReportView

router = DefaultRouter()
router.register('', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('class-report/<str:classroom_id>/', ClassReportView.as_view(), name='class-report'),
    path('', include(router.urls)),
]
