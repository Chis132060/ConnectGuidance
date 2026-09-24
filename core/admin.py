from django.contrib import admin
from .models import Profile, Appointment, CaseNote, AuditLog, ChatbotSession, StudentMoodAlert


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user_no', 'full_name', 'role', 'is_active', 'department', 'student_id', 'created_at')
    list_filter = ('role', 'is_active', 'department')
    search_fields = ('full_name', 'student_id', 'user__username', 'user__email')
    ordering = ('user_no',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'counselor', 'scheduled_at', 'status', 'concern_type', 'created_at')
    list_filter = ('status', 'concern_type', 'scheduled_at')
    search_fields = ('student__full_name', 'counselor__full_name', 'notes')
    ordering = ('-scheduled_at',)


@admin.register(CaseNote)
class CaseNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'counselor', 'is_confidential', 'updated_at')
    list_filter = ('is_confidential', 'updated_at')
    search_fields = ('counselor__full_name', 'appointment__student__full_name')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'user', 'action', 'table_name')
    list_filter = ('action', 'table_name', 'created_at')
    search_fields = ('user__full_name', 'action', 'table_name')
    readonly_fields = ('created_at',)


@admin.register(ChatbotSession)
class ChatbotSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'created_at')
    search_fields = ('student__full_name',)


@admin.register(StudentMoodAlert)
class StudentMoodAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'counselor', 'created_at')
    search_fields = ('student__full_name', 'counselor__full_name')
    list_filter = ('created_at',)
