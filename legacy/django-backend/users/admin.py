from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'full_name', 'created_at', 'last_active')
    list_filter = ('role', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'updated_at', 'last_active')

from .models import Classroom

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'created_at')
    search_fields = ('name', 'teacher__username')
    readonly_fields = ('created_at',)

from .models import ClassroomInvitation

@admin.register(ClassroomInvitation)
class ClassroomInvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'classroom', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('email', 'classroom__name')
