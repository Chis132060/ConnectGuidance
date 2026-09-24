from typing import Dict, Any, Optional
from django.core.exceptions import ValidationError
from django.db import transaction
from core.models import Profile, Appointment, StudentMoodAlert
from core.choices import RoleChoices, AppointmentStatusChoices
from .audit import log_action


@transaction.atomic
def process_mood_checkin(
    student: Profile,
    mood: str,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handles wellness mood check-in.
    'good' and 'okay' update the audit log.
    'low' alerts the counselor of the student's latest non-cancelled appointment.
    """
    if student.role != RoleChoices.STUDENT:
        raise ValidationError("Only students may submit mood check-ins.")

    valid_moods = ['good', 'okay', 'low']
    if mood not in valid_moods:
        raise ValidationError(f"Invalid mood value. Allowed values are: {', '.join(valid_moods)}.")

    cleaned_note = (note or "").strip()[:500]

    log_action(
        user=student,
        action="STUDENT_MOOD_CHECKIN",
        table_name="student_mood",
        metadata={
            "mood": mood,
            "has_note": bool(cleaned_note)
        }
    )

    if mood in ['good', 'okay']:
        return {
            'status': 'success',
            'mood': mood,
            'alert_created': False,
            'message': 'Thank you for checking in! Keep maintaining your positive momentum.'
        }

    # Low mood branch: find counselor from latest non-cancelled appointment
    latest_appt = Appointment.objects.filter(
        student=student
    ).exclude(
        status=AppointmentStatusChoices.CANCELLED
    ).order_by('-scheduled_at').first()

    if not latest_appt:
        return {
            'status': 'warning',
            'mood': 'low',
            'alert_created': False,
            'message': 'We noticed you are feeling low. We could not find an assigned counselor on record for you. Please book a guidance appointment so a counselor can support you.'
        }

    alert = StudentMoodAlert.objects.create(
        student=student,
        counselor=latest_appt.counselor,
        note=cleaned_note if cleaned_note else "Student reported low mood via check-in."
    )

    log_action(
        user=student,
        action="STUDENT_MOOD_ALERT",
        table_name="core_student_mood_alert",
        record_id=alert.id,
        metadata={
            "counselor_id": latest_appt.counselor.id,
            "appointment_id": latest_appt.id
        }
    )

    return {
        'status': 'alert_dispatched',
        'mood': 'low',
        'alert_created': True,
        'counselor_name': latest_appt.counselor.full_name,
        'message': f"Your counselor {latest_appt.counselor.full_name} has been gently notified that you are feeling low and may follow up with you."
    }
