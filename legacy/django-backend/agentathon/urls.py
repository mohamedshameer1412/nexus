from django.urls import path
from . import views

app_name = 'agentathon'

urlpatterns = [
    path('upload/', views.DocumentUploadView.as_view(), name='document_upload'),
    path('status/', views.SessionStatusView.as_view(), name='session_status'),
]
