from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

urlpatterns = [
    path("healthz", lambda request: JsonResponse({"ok": True})),
    path("admin/", admin.site.urls),
    path("api/v1/", include("learning.urls")),
]
