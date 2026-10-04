"""
Appointment Service — Booking, cancellation, and workflow state transitions.
Validates schedule slots, applies clash protection, and manages status progression.
"""
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.models import Appointment, Profile
from core.choices import ALLOWED_TRANSITIONS, AppointmentStatusChoices
from core.services.slots import has_clash
from core.services.audit import log_action


def book_appointment(student, counselor, scheduled_at, concern_type, notes=None, created_by_receptionist=False, actor=None):
    """
    Book an appointment for a student.
    student: Profile or ID
    counselor: Profile or ID
    """
    if isinstance(student, Profile):
        student_profile = student
    else:
        student_profile = Profile.objects.get(pk=student)

    if not student_profile.is_active:
        raise ValidationError("Only active students can book appointments.")

    if scheduled_at <= timezone.now():
        raise ValidationError("Please choose a future date and time.")

    if isinstance(counselor, Profile):
        counselor_profile = counselor
    else:
        try:
            counselor_profile = Profile.objects.get(pk=counselor, role="counselor", is_active=True)
        except Profile.DoesNotExist:
            raise ValidationError("That counselor is not available.")

    if has_clash(counselor_profile.id, scheduled_at):
        raise ValidationError("That time was just taken. Please choose another slot.")

    appointment = Appointment.objects.create(
        student=student_profile,
        counselor=counselor_profile,
        scheduled_at=scheduled_at,
        status=AppointmentStatusChoices.PENDING,
        concern_type=concern_type,
        notes=notes[:2000] if notes else None,
    )

    action_type = "APPOINTMENT_CREATED_RECEPTION" if created_by_receptionist else "APPOINTMENT_CREATED"
    acting_user = actor or (student_profile if not created_by_receptionist else None)

    log_action(
        user=acting_user,
        action=action_type,
        table_name="appointments",
        record_id=appointment.pk,
        metadata={"appointment_id": appointment.pk, "counselor_id": counselor_profile.pk},
    )

    return appointment


def student_cancel_appointment(appointment_or_id, student_profile):
    """
    Student cancels their own appointment.
    appointment_or_id: Appointment instance or ID
    student_profile: Profile instance
    """
    if isinstance(appointment_or_id, Appointment):
        appt = appointment_or_id
    else:
        try:
            appt = Appointment.objects.get(pk=appointment_or_id)
        except Appointment.DoesNotExist:
            raise ValidationError("Appointment not found.")

    if appt.student_id != student_profile.id:
        raise ValidationError("Not authorized to cancel this appointment.")

    if appt.status in (AppointmentStatusChoices.COMPLETED, AppointmentStatusChoices.CANCELLED):
        raise ValidationError(f"This appointment is already {appt.status}.")

    appt.status = AppointmentStatusChoices.CANCELLED
    appt.save(update_fields=["status"])

    log_action(
        user=student_profile,
        action="APPOINTMENT_CANCELLED_STUDENT",
        table_name="appointments",
        record_id=appt.pk,
        metadata={"appointment_id": appt.pk},
    )

    return appt


cancel_appointment_student = student_cancel_appointment


def counselor_update_status(appointment_or_id, new_status, counselor_profile):
    """
    Counselor updates appointment status (state machine enforced).
    """
    if isinstance(appointment_or_id, Appointment):
        appt = appointment_or_id
    else:
        try:
            appt = Appointment.objects.get(pk=appointment_or_id)
        except Appointment.DoesNotExist:
            raise ValidationError("Appointment not found.")

    if appt.counselor_id != counselor_profile.id:
        raise ValidationError("You can only update appointments assigned to your workspace.")

    if not counselor_profile.is_active:
        raise ValidationError("Only active counselors can update appointments.")

    current = appt.status
    allowed = ALLOWED_TRANSITIONS.get(current, set())

    if current in (AppointmentStatusChoices.COMPLETED, AppointmentStatusChoices.CANCELLED):
        raise ValidationError("Cannot update an appointment in a terminal state.")

    if new_status not in allowed:
        raise ValidationError(f"Cannot transition from '{current}' to '{new_status}'.")

    appt.status = new_status
    appt.save(update_fields=["status"])

    log_action(
        user=counselor_profile,
        action="APPOINTMENT_STATUS_UPDATED",
        table_name="appointments",
        record_id=appt.pk,
        metadata={
            "appointment_id": appt.pk,
            "from_status": current,
            "to_status": new_status,
        },
    )

    return appt


update_appointment_status = counselor_update_status
