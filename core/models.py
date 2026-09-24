from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Max
from .choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices


class Profile(models.Model):
    """
    Profile extension for auth.User, providing role-based access control
    and user metadata matching GuidanceConnect schema.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.STUDENT,
        db_index=True
    )
    full_name = models.CharField(max_length=200)
    student_id = models.CharField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=200, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    user_no = models.BigIntegerField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['user_no']
        indexes = [
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['user_no']),
        ]

    def save(self, *args, **kwargs):
        if not self.user_no:
            max_no = Profile.objects.aggregate(Max('user_no'))['user_no__max']
            self.user_no = (max_no or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.role}) - #{self.user_no}"


class Appointment(models.Model):
    """
    Appointments between students and counselors with strict status lifecycle.
    """
    student = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='appointments_as_student',
        db_index=True
    )
    counselor = models.ForeignKey(
        Profile,
        on_delete=models.PROTECT,
        related_name='appointments_as_counselor',
        db_index=True
    )
    scheduled_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatusChoices.choices,
        default=AppointmentStatusChoices.PENDING,
        db_index=True
    )
    concern_type = models.CharField(
        max_length=50,
        choices=ConcernTypeChoices.choices,
        default=ConcernTypeChoices.ACADEMIC
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['student', 'scheduled_at']),
            models.Index(fields=['counselor', 'scheduled_at']),
            models.Index(fields=['status']),
        ]

    def clean(self):
        if self.notes and len(self.notes) > 2000:
            raise ValidationError({'notes': 'Notes cannot exceed 2000 characters.'})

    def __str__(self):
        return f"Appt #{self.id} | {self.student.full_name} with {self.counselor.full_name} ({self.status})"


class CaseNote(models.Model):
    """
    Confidential or shared clinical case notes authored by counselors.
    Stores AES-256 encrypted ciphertext at rest.
    """
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='case_notes'
    )
    counselor = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='case_notes'
    )
    content = models.TextField(help_text="Encrypted ciphertext payload")
    is_confidential = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['appointment', 'counselor'],
                name='uniq_case_note_appt_counselor'
            )
        ]
        ordering = ['-updated_at']

    def clean(self):
        if self.appointment_id and self.counselor_id:
            if self.counselor_id != self.appointment.counselor_id:
                raise ValidationError({
                    'counselor': 'Counselor author must match the counselor assigned to the appointment.'
                })

    def __str__(self):
        return f"CaseNote for Appt #{self.appointment_id} by {self.counselor.full_name}"


class AuditLog(models.Model):
    """
    Append-only security and operational audit trail.
    """
    user = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=100, db_index=True)
    table_name = models.CharField(max_length=100)
    record_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        actor = self.user.full_name if self.user else 'System'
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {actor} -> {self.action} on {self.table_name}"


class ChatbotSession(models.Model):
    """
    Student AI conversation sessions with persisted message histories.
    """
    student = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='chatbot_sessions'
    )
    messages = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', '-created_at']),
        ]

    def __str__(self):
        return f"ChatSession #{self.id} for {self.student.full_name} ({len(self.messages)} msgs)"


class StudentMoodAlert(models.Model):
    """
    Dispatched when a student reports 'low' mood during wellness check-ins.
    Assigned to the counselor of their latest non-cancelled appointment.
    """
    student = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='student_mood_alerts'
    )
    counselor = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='counselor_mood_alerts'
    )
    note = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['counselor', '-created_at']),
            models.Index(fields=['student', '-created_at']),
        ]

    def clean(self):
        if self.note and len(self.note) > 500:
            raise ValidationError({'note': 'Note cannot exceed 500 characters.'})

    def __str__(self):
        return f"MoodAlert #{self.id}: {self.student.full_name} -> {self.counselor.full_name}"
