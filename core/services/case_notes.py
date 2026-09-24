from typing import Optional, Dict, Any
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from core.models import Appointment, CaseNote, Profile
from core.choices import RoleChoices
from .encryption import encrypt_text, decrypt_text
from .audit import log_action


@transaction.atomic
def save_case_note(
    appointment: Appointment,
    counselor: Profile,
    raw_content: str,
    is_confidential: bool = False
) -> CaseNote:
    """
    Counselor author saves clinical case note. Content is encrypted at rest using AES-256-CBC.
    Enforces integrity check: counselor author must match appointment.counselor.
    """
    if counselor.role != RoleChoices.COUNSELOR:
        raise PermissionDenied("Only counselors are authorized to create or modify case notes.")

    if appointment.counselor_id != counselor.id:
        raise PermissionDenied("Integrity error: You are not assigned to this appointment.")

    if not raw_content.strip():
        raise ValidationError("Case note content cannot be empty.")

    encrypted_content = encrypt_text(raw_content)

    case_note, created = CaseNote.objects.update_or_create(
        appointment=appointment,
        counselor=counselor,
        defaults={
            'content': encrypted_content,
            'is_confidential': is_confidential,
        }
    )

    log_action(
        user=counselor,
        action="CASE_NOTE_UPSERT",
        table_name="core_case_note",
        record_id=case_note.id,
        metadata={
            "appointment_id": appointment.id,
            "is_confidential": is_confidential,
            "created": created
        }
    )

    return case_note


def get_decrypted_case_note(
    case_note: CaseNote,
    viewer: Profile
) -> Optional[Dict[str, Any]]:
    """
    Retrieve and decrypt case note according to RLS confidentiality matrix:
    - Author counselor: can read any note they wrote
    - Admin: can read only if NOT confidential
    - Student: can read only if NOT confidential and it belongs to their appointment
    - Others: denied
    """
    is_author = (viewer.id == case_note.counselor_id)
    is_admin = (viewer.role == RoleChoices.ADMIN)
    is_own_student = (viewer.id == case_note.appointment.student_id)

    if is_author:
        # Full access for author
        decrypted = decrypt_text(case_note.content)
        return {
            'id': case_note.id,
            'content': decrypted,
            'is_confidential': case_note.is_confidential,
            'updated_at': case_note.updated_at,
            'counselor_name': case_note.counselor.full_name
        }

    if case_note.is_confidential:
        # Confidential notes are strictly author-only
        return None

    if is_admin or is_own_student:
        decrypted = decrypt_text(case_note.content)
        return {
            'id': case_note.id,
            'content': decrypted,
            'is_confidential': False,
            'updated_at': case_note.updated_at,
            'counselor_name': case_note.counselor.full_name
        }

    return None
