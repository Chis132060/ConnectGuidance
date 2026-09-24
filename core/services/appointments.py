from typing import Optional, Tuple
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from core.models import Appointment, Profile
from core.choices import RoleChoices, AppointmentStatusChoices
from .slots import is_counselor_slot_free
from .audit import log_action

ALLOWED_TRANSITIONS = {
    AppointmentStatusChoices.PENDING: [
        AppointmentStatusChoices.CONFIRMED,
        AppointmentStatusChoices.CANCELLED,
    ],
    AppointmentStatusChoices.CONFIRMED: [
        AppointmentStatusChoices.COMPLETED,
        AppointmentStatusChoices.CANCELLED,
    ],
    AppointmentStatusChoices.COMPLETED: [],
    AppointmentStatusChoices.CANCELLED: [],
}


def can_transition(current_status: str, target_status: str) -> bool:
    allowed = ALLOWED_TRANSITIONS.get(current_status, [])
    return target_status in allowed


@transaction.atomic
def book_appointment(
    student: Profile,
    counselor: Profile,
    scheduled_at,
    concern_type: str,
    notes: Optional[str] = None,
    created_by_receptionist: bool = False,
    actor: Optional[Profile] = None
) -> Appointment:
    """
    Validate slot availability and book appointment. Logs audit action.
    """
    if student.role != RoleChoices.STUDENT:
        raise ValidationError("Only students may be booked for guidance sessions.")
    if counselor.role != RoleChoices.COUNSELOR:
        raise ValidationError("Selected provider must be a licensed counselor.")
    if not counselor.is_active:
        raise ValidationError("This counselor is currently inactive.")

    if not is_counselor_slot_free(counselor, scheduled_at):
        raise ValidationError("The requested time slot is no longer available. Please select another time.")

    appt = Appointment.objects.create(
        student=student,
        counselor=counselor,
        scheduled_at=scheduled_at,
        status=AppointmentStatusChoices.PENDING,
        concern_type=concern_type,
        notes=notes or ""
    )

    action = "APPOINTMENT_CREATED_RECEPTION" if created_by_receptionist else "APPOINTMENT_CREATED"
    effective_actor = actor or (student if not created_by_receptionist else None)

    log_action(
        user=effective_actor,
        action=action,
        table_name="core_appointment",
        record_id=appt.id,
        metadata={
            "student_id": student.id,
            "counselor_id": counselor.id,
            "scheduled_at": scheduled_at.isoformat(),
            "concern_type": concern_type,
            "created_by_receptionist": created_by_receptionist
        }
    )

    return appt


@transaction.atomic
def student_cancel_appointment(appointment: Appointment, student: Profile) -> Appointment:
    """
    Student self-cancellation: allowed only on own appointment in pending/confirmed status.
    """
    if appointment.student_id != student.id:
        raise ValidationError("You are not authorized to cancel this appointment.")

    if appointment.status in [AppointmentStatusChoices.COMPLETED, AppointmentStatusChoices.CANCELLED]:
        raise ValidationError(f"Cannot cancel an appointment that is already {appointment.status}.")

    old_status = appointment.status
    appointment.status = AppointmentStatusChoices.CANCELLED
    appointment.save(update_fields=['status'])

    log_action(
        user=student,
        action="APPOINTMENT_CANCELLED_STUDENT",
        table_name="core_appointment",
        record_id=appointment.id,
        metadata={
            "old_status": old_status,
            "new_status": AppointmentStatusChoices.CANCELLED
        }
    )

    return appointment


@transaction.atomic
def counselor_update_status(
    appointment: Appointment,
    new_status: str,
    counselor: Profile
) -> Appointment:
    """
    Counselor status update strictly enforcing state machine transitions.
    """
    if appointment.counselor_id != counselor.id:
        raise ValidationError("You can only update appointments assigned to your workspace.")

    if not can_transition(appointment.status, new_status):
        raise ValidationError(
            f"Invalid transition from '{appointment.status}' to '{new_status}'. Allowed transitions: {ALLOWED_TRANSITIONS.get(appointment.status, 'None (terminal)')}."
        )

    old_status = appointment.status
    appointment.status = new_status
    appointment.save(update_fields=['status'])

    log_action(
        user=counselor,
        action="APPOINTMENT_STATUS_UPDATED",
        table_name="core_appointment",
        record_id=appointment.id,
        metadata={
            "old_status": old_status,
            "new_status": new_status,
            "counselor_id": counselor.id
        }
    )

    return appointment
