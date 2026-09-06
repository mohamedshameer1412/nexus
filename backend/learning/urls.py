from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LearningModuleViewSet, StudentModuleProgressViewSet, FlashcardDeckViewSet

router = DefaultRouter()
router.register(r'modules', LearningModuleViewSet, basename='learning-module')
router.register(r'progress', StudentModuleProgressViewSet, basename='student-progress')
router.register(r'flashcards', FlashcardDeckViewSet, basename='flashcard-deck')

urlpatterns = [
    path('', include(router.urls)),
]
