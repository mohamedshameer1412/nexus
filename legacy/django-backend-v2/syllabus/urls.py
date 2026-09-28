from django.urls import path
from . import views

urlpatterns = [
    # Academic Subjects
    path('subjects/', views.subject_list, name='nexus-subject-list'),
    path('subjects/<str:subject_id>/', views.subject_detail, name='nexus-subject-detail'),

    # Syllabus Upload & Extraction
    path('upload/', views.syllabus_upload, name='nexus-syllabus-upload'),
    path('status/<str:upload_id>/', views.syllabus_status, name='nexus-syllabus-status'),

    # Roadmap
    path('<str:upload_id>/roadmap/', views.roadmap_detail, name='nexus-roadmap-detail'),
    path('<str:upload_id>/roadmap/edit/', views.roadmap_edit, name='nexus-roadmap-edit'),
    path('<str:upload_id>/confirm/', views.roadmap_confirm, name='nexus-roadmap-confirm'),
]
