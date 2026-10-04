"""
Receptionist Booking and Student Search Service.
Provides student lookup by ID or name, counselor listing, next-available slot finding,
and walk-in appointment scheduling.
"""
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import Profile, Appointment
from core.choices import RoleChoices, AppointmentStatusChoices
from core.services.slots import is_counselor_slot_free, get_available_slots
from core.services.audit import log_action


def search_students(query, limit=25):
    """
    Search active student profiles by name or student_id (case-insensitive).
    Returns queryset, max 25 results.
    """
    return Profile.objects.filter(
        role=RoleChoices.STUDENT,
        is_active=True,
    ).filter(
        Q(full_name__icontains=query) | Q(student_id__icontains=query)
    )[:limit]


def list_counselors():
    """Return active counselors ordered alphabetically."""
    return Profile.objects.filter(
        role=RoleChoices.COUNSELOR,
        is_active=True,
    ).order_by("full_name", "user__username")


def find_next_available(date_obj, counselors=None):
    """
    Find the first available slot among all counselors (alphabetically).
    Returns (counselor, slot_datetime) or (None, None).
    """
    from core.services.slots import get_first_available_counselor_slot
    res = get_first_available_counselor_slot(date_obj)
    if res:
        return res["counselor"], res["slot"]
    return None, None


def book_receptionist_appointment(receptionist, student, scheduled_at, concern_type, counselor=None, notes=None):
    """
    Receptionist books an appointment on behalf of a student.
    If counselor is None, automatically picks the earliest free counselor alphabetically.
    """
    if isinstance(student, Profile):
        student_profile = student
    else:
        try:
            student_profile = Profile.objects.get(pk=student, role=RoleChoices.STUDENT, is_active=True)
        except Profile.DoesNotExist:
            raise ValidationError("Student not found or inactive.")

    if not student_profile.is_active:
        raise ValidationError("Student not found or inactive.")

    if scheduled_at <= timezone.now():
        raise ValidationError("Please choose a future date and time.")

    # Determine counselor
    if counselor is not None:
        if isinstance(counselor, Profile):
            counselor_profile = counselor
        else:
            try:
                counselor_profile = Profile.objects.get(pk=counselor, role=RoleChoices.COUNSELOR, is_active=True)
            except Profile.DoesNotExist:
                raise ValidationError("Counselor not found or inactive.")

        if not is_counselor_slot_free(counselor_profile.id, scheduled_at):
            raise ValidationError("That counselor is not available at this time.")
    else:
        # Pick earliest free counselor alphabetically
        counselors = list(list_counselors())
        if not counselors:
            raise ValidationError("No active counselors available.")

        counselor_profile = None
        for c in counselors:
            if is_counselor_slot_free(c.id, scheduled_at):
                counselor_profile = c
                break

        if not counselor_profile:
            raise ValidationError("No counselor is free at that time.")

    appointment = Appointment.objects.create(
        student=student_profile,
        counselor=counselor_profile,
        scheduled_at=scheduled_at,
        status=AppointmentStatusChoices.PENDING,
        concern_type=concern_type,
        notes=notes[:2000] if notes else None,
    )

    receptionist_profile = receptionist if isinstance(receptionist, Profile) else None

    log_action(
        user=receptionist_profile,
        action="APPOINTMENT_CREATED_RECEPTION",
        table_name="appointments",
        record_id=appointment.pk,
        metadata={
            "appointment_id": appointment.pk,
            "student_id": student_profile.pk,
            "counselor_id": counselor_profile.pk,
        },
    )

    return appointment


book_for_student = book_receptionist_appointment
