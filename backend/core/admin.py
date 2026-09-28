from django.contrib import admin

from core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("at", "user_id", "action", "status", "ip")
    list_filter = ("method", "status")
    search_fields = ("action", "path", "ip")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):          # the log is written by the system only
        return False

    def has_change_permission(self, request, obj=None):
        return False
