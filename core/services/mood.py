"""
Student Mood Check-In Service.
Handles student wellness mood updates:
- 'good' or 'okay': records audit log entry
- 'low': flags counselor attention by creating a StudentMoodAlert
"""
from core.models import Appointment, StudentMoodAlert, Profile
from core.services.audit import log_action


def process_mood_checkin(student_profile, mood, note=None):
    """
    Process a mood check-in.
    mood: "good" | "okay" | "low"
    note: optional string, max 500 chars
    Returns dict with success/alert info.
    """
    if not student_profile.is_active:
        return {
            "status": "error",
            "alert_created": False,
            "ok": False,
            "error": "Only active students can submit mood check-ins.",
            "message": "Only active students can submit mood check-ins.",
        }

    if mood not in ("good", "okay", "low"):
        return {
            "status": "error",
            "alert_created": False,
            "ok": False,
            "error": "Invalid mood value.",
            "message": "Invalid mood value.",
        }

    # Truncate note
    if note and len(note) > 500:
        note = note[:500]

    if mood in ("good", "okay"):
        log_action(
            user=student_profile,
            action="STUDENT_MOOD_CHECKIN",
            table_name="student_mood_alerts",
            metadata={"mood": mood},
        )
        return {
            "status": "success",
            "alert_created": False,
            "ok": True,
            "notified": False,
            "message": "Mood check-in submitted successfully.",
        }

    # mood == "low" → find counselor from latest non-cancelled appointment
    latest_appt = (
        Appointment.objects.filter(student=student_profile)
        .exclude(status="cancelled")
        .order_by("-scheduled_at")
        .select_related("counselor")
        .first()
    )

    if not latest_appt:
        return {
            "status": "warning",
            "alert_created": False,
            "ok": False,
            "notified": False,
            "message": "Please book a guidance appointment with a counselor or visit the front desk.",
            "error": "Please book a guidance appointment with a counselor or visit the front desk.",
        }

    counselor = latest_appt.counselor
    if counselor.role != "counselor":
        return {
            "status": "warning",
            "alert_created": False,
            "ok": False,
            "notified": False,
            "message": "Your assigned counselor is no longer active. Please book a guidance appointment.",
            "error": "Your assigned counselor is no longer active.",
        }

    try:
        alert = StudentMoodAlert.objects.create(
            student=student_profile,
            counselor=counselor,
            note=note or "",
        )
    except Exception:
        return {
            "status": "error",
            "alert_created": False,
            "ok": False,
            "error": "Could not create mood alert.",
            "message": "Could not create mood alert.",
        }

    log_action(
        user=student_profile,
        action="STUDENT_MOOD_ALERT",
        table_name="student_mood_alerts",
        record_id=alert.pk,
        metadata={
            "mood": "low",
            "alert_id": alert.pk,
            "counselor_id": counselor.pk,
        },
    )

    return {
        "status": "alert_dispatched",
        "alert_created": True,
        "ok": True,
        "notified": True,
        "counselor_name": counselor.full_name,
        "message": f"Alert sent to counselor {counselor.full_name}.",
    }
