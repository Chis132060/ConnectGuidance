import uuid
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.models import Profile, CaseNote, AuditLog


@receiver(post_save, sender=Profile)
def audit_profile_save(sender, instance, created, **kwargs):
    """
    Parity with Supabase trigger `trg_audit_profiles_changes`:
    Logs INSERT and UPDATE operations on Profile.
    """
    action = 'PROFILE_CREATED' if created else 'PROFILE_UPDATED'
    try:
        AuditLog.objects.create(
            user=instance,
            action=action,
            table_name='core_profile',
            record_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"profile-{instance.id}"),
            metadata={
                'user_no': instance.user_no,
                'role': instance.role,
                'is_active': instance.is_active,
                'full_name': instance.full_name
            }
        )
    except Exception:
        # Auditing must never break the primary transaction
        pass


@receiver(post_save, sender=CaseNote)
def audit_casenote_save(sender, instance, created, **kwargs):
    """
    Parity with Supabase trigger `trg_audit_case_notes_changes`:
    Logs CASE_NOTE_CREATED and CASE_NOTE_UPDATED.
    """
    action = 'CASE_NOTE_CREATED' if created else 'CASE_NOTE_UPDATED'
    try:
        AuditLog.objects.create(
            user=instance.counselor,
            action=action,
            table_name='core_case_note',
            record_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"casenote-{instance.id}"),
            metadata={
                'appointment_id': instance.appointment_id,
                'is_confidential': instance.is_confidential
            }
        )
    except Exception:
        pass


@receiver(post_delete, sender=CaseNote)
def audit_casenote_delete(sender, instance, **kwargs):
    try:
        AuditLog.objects.create(
            user=instance.counselor,
            action='CASE_NOTE_DELETED',
            table_name='core_case_note',
            record_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"casenote-{instance.id}"),
            metadata={
                'appointment_id': instance.appointment_id
            }
        )
    except Exception:
        pass
