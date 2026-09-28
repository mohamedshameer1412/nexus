from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI schema
schema_view = get_schema_view(
    openapi.Info(
        title="Adaptive Exam AI API",
        default_version='v1',
        description="Complete API documentation for Adaptive Exam AI platform with ML-powered adaptive quizzing",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@adaptiveexam.ai"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/users/', include('users.urls')),
    path('api/quiz/', include('quiz.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/proctoring/', include('proctoring.urls')),
    path('api/learning/', include('learning.urls')),

    # NEXUS — Agentic Learner Intelligence OS
    path('api/nexus/syllabus/', include('syllabus.urls')),
    path('api/nexus/workspace/', include('workspace.urls')),
    path('api/nexus/tutor/', include('tutor_agent.urls')),
    path('api/nexus/evaluator/', include('evaluator_agent.urls')),
    path('api/nexus/planner/', include('planner_agent.urls')),
    path('api/nexus/twin/', include('nexus_core.urls')),
    
    # Swagger/OpenAPI documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='api-docs'),  # Root redirects to Swagger
]

# Serve media files in development
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
