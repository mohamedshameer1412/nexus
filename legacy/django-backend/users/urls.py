from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, LogoutView, ProfileView
from .password_views import change_password, request_password_reset, confirm_password_reset
from .learning_dna_views import (
    create_learning_profile,
    start_diagnostic_test,
    submit_diagnostic_answer,
    complete_diagnostic_test,
    get_learning_profile,
    download_diagnostic_report
)
from .mastery_views import (
    update_mastery_after_quiz,
    get_mastery_dashboard,
    get_concept_mastery
)
from .teacher_learning_dna_views import (
    get_student_learning_profile,
    get_student_mastery_data,
    get_classroom_mastery_analytics
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('change-password/', change_password, name='change_password'),
    path('password-reset/', request_password_reset, name='request_password_reset'),
    path('password-reset-confirm/', confirm_password_reset, name='confirm_password_reset'),
    
    # Learning DNA Onboarding (Students)
    path('learning-profile/create/', create_learning_profile, name='create_learning_profile'),
    path('learning-profile/', get_learning_profile, name='get_learning_profile'),
    path('diagnostic-test/start/', start_diagnostic_test, name='start_diagnostic_test'),
    path('diagnostic-test/submit-answer/', submit_diagnostic_answer, name='submit_diagnostic_answer'),
    path('diagnostic-test/complete/', complete_diagnostic_test, name='complete_diagnostic_test'),
    path('diagnostic-test/report/', download_diagnostic_report, name='download_diagnostic_report'),
    
    # Mastery Tracking (Students)
    path('mastery-dashboard/', get_mastery_dashboard, name='mastery_dashboard'),
    path('mastery/<str:concept_id>/', get_concept_mastery, name='concept_mastery'),
    
    # Teacher Views for Learning DNA (Read-only)
    path('teacher/student/<uuid:student_id>/learning-profile/', get_student_learning_profile, name='teacher_student_profile'),
    path('teacher/student/<uuid:student_id>/mastery/', get_student_mastery_data, name='teacher_student_mastery'),
    path('teacher/classroom/<uuid:classroom_id>/mastery-analytics/', get_classroom_mastery_analytics, name='teacher_classroom_analytics'),
]

from rest_framework.routers import DefaultRouter
from .views import (
    ClassroomViewSet, InvitationViewSet, ClassroomQuizAssignmentViewSet, 
    NotificationViewSet, AchievementViewSet
)

router = DefaultRouter()
router.register(r'classrooms', ClassroomViewSet, basename='classroom')
router.register(r'invitations', InvitationViewSet, basename='invitation')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'classroom-quiz-assignments', ClassroomQuizAssignmentViewSet, basename='classroom-quiz-assignment')
router.register(r'achievements', AchievementViewSet, basename='achievement')

urlpatterns += router.urls

