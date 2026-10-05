from django.contrib import admin
from accounts.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user_no', 'full_name', 'role', 'student_id', 'department', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'department')
    search_fields = ('full_name', 'student_id', 'user__email', 'user__username')
    ordering = ('user_no',)
