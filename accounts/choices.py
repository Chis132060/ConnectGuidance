from django.db import models


class RoleChoices(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    COUNSELOR = 'counselor', 'Counselor'
    STUDENT = 'student', 'Student'
    RECEPTIONIST = 'receptionist', 'Receptionist'


ROLE_CHOICES = RoleChoices.choices
