from django.db import models


class RoleChoices(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    COUNSELOR = 'counselor', 'Counselor'
    STUDENT = 'student', 'Student'
    RECEPTIONIST = 'receptionist', 'Receptionist'


class AppointmentStatusChoices(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    CANCELLED = 'cancelled', 'Cancelled'
    COMPLETED = 'completed', 'Completed'


class ConcernTypeChoices(models.TextChoices):
    ACADEMIC = 'academic', 'Academic'
    MENTAL_HEALTH = 'mental_health', 'Mental Health'
    CAREER = 'career', 'Career'
    PERSONAL = 'personal', 'Personal'
    OTHER = 'other', 'Other'


ROLE_CHOICES = RoleChoices.choices
STATUS_CHOICES = AppointmentStatusChoices.choices
CONCERN_CHOICES = ConcernTypeChoices.choices
