from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TopicViewSet, SubtopicViewSet, QuestionViewSet,
    QuizViewSet, QuizSessionViewSet
)
from .pdf_import_views import PDFQuestionImportView, PDFQuestionImportStatusView, PDFQuestionConfirmView
from users.mastery_views import update_mastery_after_quiz
from .ai_views import (
    generate_questions, save_generated_questions,
    get_ai_generated_questions, approve_ai_question
)
from .text_views import (
    submit_text_answer, get_pending_reviews, teacher_review_response
)
from .auto_grading_views import (
    auto_grade_response, generate_model_answer, batch_auto_grade
)


router = DefaultRouter()
router.register(r'topics', TopicViewSet, basename='topic')
router.register(r'subtopics', SubtopicViewSet, basename='subtopic')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'sessions', QuizSessionViewSet, basename='session')


urlpatterns = [
    path('', include(router.urls)),
    path('import-pdf/', PDFQuestionImportView.as_view(), name='import-pdf'),
    path('import-pdf/status/', PDFQuestionImportStatusView.as_view(), name='import-pdf-status'),
    path('import-pdf/confirm/', PDFQuestionConfirmView.as_view(), name='import-pdf-confirm'),
    path('sessions/<uuid:session_id>/update-mastery/', update_mastery_after_quiz, name='update-mastery'),
    
    # AI Quiz Generation
    path('generate-questions/', generate_questions, name='generate-questions'),
    path('save-generated-questions/', save_generated_questions, name='save-generated-questions'),
    path('ai-generated-questions/', get_ai_generated_questions, name='ai-generated-questions'),
    path('ai-generated-questions/<uuid:question_id>/approve/', approve_ai_question, name='approve-ai-question'),
    
    # Text-Based Questions
    path('sessions/<uuid:session_id>/submit-text-answer/', submit_text_answer, name='submit-text-answer'),
    path('pending-reviews/', get_pending_reviews, name='pending-reviews'),
    path('sessions/<uuid:session_id>/pending-reviews/', get_pending_reviews, name='session-pending-reviews'),
    path('responses/<int:response_id>/teacher-review/', teacher_review_response, name='teacher-review'),
    
    # Auto-Grading with Gemini AI
    path('responses/<uuid:response_id>/auto-grade/', auto_grade_response, name='auto-grade-response'),
    path('questions/generate-model-answer/', generate_model_answer, name='generate-model-answer'),
    path('responses/batch-auto-grade/', batch_auto_grade, name='batch-auto-grade'),
]

