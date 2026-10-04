"""
Django Signals for GuidanceConnect.
1. Auto-creates user Profile upon registration.
2. Creates audit records for profile modifications and case note updates.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models import Max


@receiver(post_save, sender=User)
def create_profile_on_user_create(sender, instance, created, **kwargs):
    """Automatically initialize a Student Profile when a new Django User is created."""
    if created:
        from .models import Profile
        if not hasattr(instance, 'profile'):
            max_no = Profile.objects.aggregate(m=Max("user_no"))["m"] or 0
            Profile.objects.create(
                user=instance,
                role="student",
                full_name=instance.get_full_name() or instance.username,
                is_active=True,
                user_no=max_no + 1,
            )


@receiver(post_save, sender='core.Profile')
def audit_profile_save(sender, instance, created, **kwargs):
    """Record an audit trail whenever a Profile is created or modified."""
    from .services.audit import log_action
    action = "PROFILE_CREATED" if created else "PROFILE_UPDATED"
    log_action(
        user=instance,
        action=action,
        table_name="core_profile",
        record_id=instance.pk,
        metadata={"full_name": instance.full_name, "role": instance.role, "profile_id": instance.pk},
    )


@receiver(post_delete, sender='core.Profile')
def audit_profile_delete(sender, instance, **kwargs):
    """Record an audit trail whenever a Profile is removed."""
    from .services.audit import log_action
    log_action(
        user=None,
        action="PROFILE_DELETED",
        table_name="core_profile",
        record_id=instance.pk,
        metadata={"profile_id": instance.pk, "role": instance.role},
    )


@receiver(post_save, sender='core.CaseNote')
def audit_case_note_save(sender, instance, created, **kwargs):
    """Record an audit trail when a counselor writes or edits a Case Note."""
    from .services.audit import log_action
    action = "CASE_NOTE_CREATED" if created else "CASE_NOTE_UPDATED"
    log_action(
        user=instance.counselor,
        action=action,
        table_name="core_case_note",
        record_id=instance.pk,
        metadata={"case_note_id": instance.pk, "appointment_id": instance.appointment_id},
    )


@receiver(post_delete, sender='core.CaseNote')
def audit_case_note_delete(sender, instance, **kwargs):
    """Record an audit trail when a Case Note is removed."""
    from .services.audit import log_action
    log_action(
        user=instance.counselor,
        action="CASE_NOTE_DELETED",
        table_name="core_case_note",
        record_id=instance.pk,
        metadata={"case_note_id": instance.pk, "appointment_id": instance.appointment_id},
    )
