import uuid
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, CaseNote, AuditLog
from apps.common.choices import RoleChoices


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Parity with Supabase trigger `on_auth_user_created_profile`:
    Auto-creates a student Profile when a new auth.User is registered.
    """
    if created:
        if not hasattr(instance, 'profile'):
            full_name = instance.get_full_name() or instance.username
            Profile.objects.create(
                user=instance,
                role=RoleChoices.STUDENT,
                full_name=full_name,
                is_active=True
            )
