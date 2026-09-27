from django.urls import path
from . import views

app_name = 'sih'

urlpatterns = [
    # Onboarding
    path('onboarding/', views.onboarding, name='onboarding'),
    path('roles/', views.get_roles, name='roles'),
    path('domains/', views.get_domains, name='domains'),

    # Diagnostic Assessment
    path('diagnostic/questions/', views.get_diagnostic_questions, name='diagnostic-questions'),
    path('diagnostic/submit/', views.submit_diagnostic, name='diagnostic-submit'),

    # Digital Twin
    path('twin/', views.get_digital_twin, name='digital-twin'),

    # Learning Debt + Gap Analysis
    path('gaps/', views.get_learning_gaps, name='learning-gaps'),

    # Learning Pathway (iGOT + TPAC)
    path('pathway/', views.get_learning_pathway, name='learning-pathway'),

    # Verify & Replan
    path('verify/', views.verify_and_replan, name='verify-replan'),

    # Career Record
    path('career/', views.get_career_record, name='career-record'),
    path('career/report/', views.download_career_report, name='career-report'),
]
