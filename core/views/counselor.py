"""
Counselor views — workspace, appointments registry, case notes, wellness monitoring, and profile.
Handles counselor appointment management, session status updates, and encrypted case notes.
"""
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from core.guards import role_required
from core.models import Appointment, StudentMoodAlert, CaseNote, Profile
from core.services.appointments import update_appointment_status
from core.services.case_notes import save_case_note, get_case_note_decrypted
from core.services.encryption import decrypt


@role_required("counselor")
def workspace_view(request):
    """Counselor workspace — stats, alerts, today's sessions, tables."""
    profile = request.profile
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    if request.method == "POST":
        action = request.POST.get("action")
        appt_id = request.POST.get("appointment_id")

        if action in ("confirmed", "cancelled", "completed"):
            try:
                update_appointment_status(appt_id, action, profile)
                messages.success(request, f"Appointment {action}.")
            except Exception as e:
                msg = getattr(e, "message", str(e))
                messages.error(request, msg)
        return redirect("/counselor/")

    # Stats
    today_count = Appointment.objects.filter(
        counselor=profile,
        scheduled_at__gte=today_start,
        scheduled_at__lt=today_end,
    ).count()

    upcoming_count = Appointment.objects.filter(
        counselor=profile,
        status__in=["pending", "confirmed"],
        scheduled_at__gte=now,
    ).count()

    past_count = Appointment.objects.filter(
        counselor=profile,
        status__in=["completed", "cancelled"],
    ).count()

    # Mood alerts
    mood_alerts = StudentMoodAlert.objects.filter(
        counselor=profile,
    ).select_related("student").order_by("-created_at")[:10]

    # Today's sessions
    today_sessions = Appointment.objects.filter(
        counselor=profile,
        scheduled_at__gte=today_start,
        scheduled_at__lt=today_end,
    ).select_related("student").order_by("scheduled_at")

    # Upcoming appointments
    upcoming = Appointment.objects.filter(
        counselor=profile,
        status__in=["pending", "confirmed"],
        scheduled_at__gte=now,
    ).exclude(
        scheduled_at__gte=today_start,
        scheduled_at__lt=today_end,
    ).select_related("student").order_by("scheduled_at")[:20]

    # Past appointments
    past = Appointment.objects.filter(
        counselor=profile,
    ).filter(
        status__in=["completed", "cancelled"],
    ).select_related("student").order_by("-scheduled_at")[:20]

    return render(request, "counselor/workspace.html", {
        "profile": profile,
        "today_count": today_count,
        "upcoming_count": upcoming_count,
        "past_count": past_count,
        "mood_alerts": mood_alerts,
        "today_sessions": today_sessions,
        "upcoming": upcoming,
        "past": past,
    })


@role_required("counselor")
def case_note_view(request, appointment_id):
    """Case note editor — write/view encrypted notes."""
    profile = request.profile

    appointment = get_object_or_404(
        Appointment.objects.select_related("student", "counselor"),
        pk=appointment_id,
        counselor=profile,
    )

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        is_confidential = request.POST.get("is_confidential") == "on"

        if not content:
            messages.error(request, "Note content cannot be empty.")
            return redirect(f"/counselor/case-notes/{appointment_id}/")

        note, error = save_case_note(profile, appointment_id, content, is_confidential)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Case note saved successfully.")
        return redirect(f"/counselor/case-notes/{appointment_id}/")

    # GET — try to load existing note
    plaintext = ""
    existing_note = None
    plaintext_data, note_obj, error = get_case_note_decrypted(profile, appointment_id)
    if note_obj:
        existing_note = note_obj
        plaintext = plaintext_data or ""

    return render(request, "counselor/case_note.html", {
        "profile": profile,
        "appointment": appointment,
        "plaintext": plaintext,
        "existing_note": existing_note,
    })


@role_required("counselor")
def appointments_view(request):
    """Counselor full appointment registry with status filtering."""
    profile = request.profile
    status_filter = request.GET.get("status", "all")

    qs = Appointment.objects.filter(counselor=profile).select_related("student").order_by("-scheduled_at")
    
    counts = {
        "all": qs.count(),
        "pending": qs.filter(status="pending").count(),
        "confirmed": qs.filter(status="confirmed").count(),
        "completed": qs.filter(status="completed").count(),
        "cancelled": qs.filter(status="cancelled").count(),
    }

    if status_filter != "all" and status_filter in counts:
        filtered_qs = qs.filter(status=status_filter)
    else:
        filtered_qs = qs

    return render(request, "counselor/appointments.html", {
        "profile": profile,
        "appointments": filtered_qs,
        "counts": counts,
        "active_filter": status_filter,
    })


@role_required("counselor")
def case_notes_list_view(request):
    """Counselor case notes repository."""
    profile = request.profile
    notes_qs = CaseNote.objects.filter(counselor=profile).select_related("appointment__student").order_by("-created_at")

    notes_data = []
    for n in notes_qs:
        try:
            preview = decrypt(n.content)
        except Exception:
            preview = "[Encrypted Content]"
        notes_data.append({
            "note": n,
            "preview": preview[:150] + "..." if len(preview) > 150 else preview,
        })

    stats = {
        "total_notes": notes_qs.count(),
        "confidential_count": notes_qs.filter(is_confidential=True).count(),
        "standard_count": notes_qs.filter(is_confidential=False).count(),
    }

    return render(request, "counselor/case_notes_list.html", {
        "profile": profile,
        "notes": notes_data,
        "stats": stats,
    })


@role_required("counselor")
def wellness_view(request):
    """Counselor wellness alerts and student mood patterns."""
    profile = request.profile
    alerts = StudentMoodAlert.objects.filter(counselor=profile).select_related("student").order_by("-created_at")

    stats = {
        "total_alerts": alerts.count(),
        "unique_students": alerts.values("student").distinct().count(),
    }

    return render(request, "counselor/wellness.html", {
        "profile": profile,
        "alerts": alerts,
        "stats": stats,
    })


@role_required("counselor")
def profile_view(request):
    """Counselor profile page."""
    return render(request, "counselor/profile.html", {
        "profile": request.profile,
    })
