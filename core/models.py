"""
GuidanceConnect Domain Models.
Defines models for user profiles, counseling appointments, encrypted case notes,
system audit logs, wellness chatbot sessions, and student mood alerts.
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .choices import ROLE_CHOICES, STATUS_CHOICES, CONCERN_CHOICES


class Profile(models.Model):
    """Extended user profile linked one-to-one with Django auth.User."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    full_name = models.CharField(max_length=200)
    student_id = models.CharField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=200, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    user_no = models.BigIntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.role})"


class Appointment(models.Model):
    """Counseling session appointment scheduled between a student and counselor."""
    student = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="appointments_as_student"
    )
    counselor = models.ForeignKey(
        Profile, on_delete=models.PROTECT, related_name="appointments_as_counselor"
    )
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    concern_type = models.CharField(max_length=50, choices=CONCERN_CHOICES, default="other")
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["counselor"]),
            models.Index(fields=["scheduled_at"]),
        ]

    def __str__(self):
        return f"Appointment #{self.pk} — {self.student} with {self.counselor} at {self.scheduled_at}"


class CaseNote(models.Model):
    """Encrypted counseling notes recorded for an appointment."""
    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="case_notes"
    )
    counselor = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="case_notes"
    )
    content = models.TextField()  # Encrypted ciphertext storage
    is_confidential = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["appointment", "counselor"],
                name="uniq_case_note_appt_counselor",
            ),
        ]

    def clean(self):
        """Ensure the case note author matches the appointment's designated counselor."""
        if self.appointment_id and self.counselor_id:
            if self.counselor_id != self.appointment.counselor_id:
                raise ValidationError(
                    "Case note counselor must match the appointment's assigned counselor."
                )

    def __str__(self):
        return f"CaseNote for Appointment #{self.appointment_id}"


class AuditLog(models.Model):
    """System activity audit log capturing user actions and security events."""
    user = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    action = models.CharField(max_length=100)
    table_name = models.CharField(max_length=100)
    record_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.action}] {self.table_name} by {self.user}"


class ChatbotSession(models.Model):
    """Wellness assistant conversation history for a student."""
    student = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="chatbot_sessions"
    )
    messages = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat session for {self.student}"


class StudentMoodAlert(models.Model):
    """Daily mood check-in alert flagged for counselor attention."""
    student = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="mood_alerts_as_student"
    )
    counselor = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="mood_alerts"
    )
    note = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["counselor", "-created_at"]),
            models.Index(fields=["student", "-created_at"]),
        ]

    def __str__(self):
        return f"Mood alert: {self.student} → {self.counselor}"
