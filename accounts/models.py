from django.db import models
from django.contrib.auth.models import User
from django.db.models import Max
from accounts.choices import RoleChoices
from accounts.constants import FSUU_PROGRAM_CHOICES


class Profile(models.Model):
    """
    User Profile extending auth.User with role-based access control.
    Maps to core_profile table to preserve database continuity.
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
    department = models.CharField(
        max_length=200,
        choices=FSUU_PROGRAM_CHOICES,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    user_no = models.BigIntegerField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_profile'
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
        return f"{self.full_name} ({self.get_role_display()})"
