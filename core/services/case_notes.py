"""
Case Notes Service — Encrypted clinical note authoring, retrieval, and access verification.
Handles saving encrypted notes and checking counselor authorization.
"""
from core.models import CaseNote, Appointment
from core.services.encryption import encrypt, decrypt
from core.services.audit import log_action


def save_case_note(counselor_profile, appointment_id, content, is_confidential=False):
    """
    Save (upsert) a case note. Encrypts content before storage.
    Returns (case_note, None) on success, (None, error_message) on failure.
    """
    if not counselor_profile.is_active:
        return None, "Only active counselors can write case notes."

    if not content or len(content) > 50000:
        return None, "Content must be between 1 and 50,000 characters."

    try:
        appointment = Appointment.objects.select_related("counselor").get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return None, "Appointment not found."

    # Integrity check: counselor must match
    if appointment.counselor_id != counselor_profile.pk:
        return None, "You are not assigned to this appointment."

    # Encrypt content
    try:
        ciphertext = encrypt(content)
    except Exception:
        return None, "Encryption failed. Check server configuration."

    # Upsert
    note, created = CaseNote.objects.update_or_create(
        appointment=appointment,
        counselor=counselor_profile,
        defaults={
            "content": ciphertext,
            "is_confidential": is_confidential,
        },
    )

    log_action(
        user=counselor_profile,
        action="CASE_NOTE_UPSERT",
        table_name="case_notes",
        metadata={
            "case_note_id": note.pk,
            "appointment_id": appointment_id,
            "created": created,
        },
    )

    return note, None


def get_case_note_decrypted(viewer_profile, appointment_id):
    """
    Retrieve and decrypt a case note based on viewer's permissions.
    Returns (plaintext, note, None) on success, (None, None, error_message) on failure.
    """
    try:
        note = CaseNote.objects.select_related(
            "appointment", "appointment__counselor", "counselor"
        ).get(appointment_id=appointment_id)
    except CaseNote.DoesNotExist:
        return None, None, "Case note not found."

    # Permission check
    is_author = note.counselor_id == viewer_profile.pk
    is_admin = viewer_profile.role == "admin"
    is_student = viewer_profile.role == "student"

    if is_author:
        pass  # Author can always read
    elif is_admin and not note.is_confidential:
        pass  # Admin can read non-confidential
    elif is_student and not note.is_confidential:
        # Student can only see notes from their own appointments
        if note.appointment.student_id != viewer_profile.pk:
            return None, None, "You may not view this note."
    else:
        return None, None, "You may not view this note."

    try:
        plaintext = decrypt(note.content)
    except Exception:
        return None, None, "Could not decrypt note."

    return plaintext, note, None
