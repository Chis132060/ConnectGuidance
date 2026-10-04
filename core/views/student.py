"""
Student views — dashboard, appointments, profile, front desk, and chatbot.
Handles student counseling appointment bookings, cancellation, mood check-in, and profile viewing.
"""
from datetime import datetime, date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from core.guards import role_required
from core.models import Appointment, CaseNote, Profile
from core.services.appointments import book_appointment, cancel_appointment_student
from core.services.slots import get_available_slots
from core.services.mood import process_mood_checkin
from core.services.encryption import decrypt


@role_required("student")
def dashboard_view(request):
    """Student dashboard — greeting, mood widget, upcoming, history."""
    profile = request.profile

    # Upcoming appointments (pending/confirmed, future)
    upcoming = Appointment.objects.filter(
        student=profile,
        status__in=["pending", "confirmed"],
        scheduled_at__gte=timezone.now(),
    ).select_related("counselor").order_by("scheduled_at")[:5]

    # Recent history
    history = Appointment.objects.filter(
        student=profile,
    ).exclude(
        status__in=["pending", "confirmed"],
    ).select_related("counselor").order_by("-scheduled_at")[:10]

    # Non-confidential case notes for student
    case_notes = CaseNote.objects.filter(
        appointment__student=profile,
        is_confidential=False,
    ).select_related("appointment", "counselor").order_by("-created_at")[:5]

    # Decrypt note previews (truncated)
    notes_data = []
    for note in case_notes:
        try:
            plain = decrypt(note.content)
            notes_data.append({
                "note": note,
                "preview": plain[:200] + "..." if len(plain) > 200 else plain,
            })
        except Exception:
            notes_data.append({"note": note, "preview": "[Unable to decrypt]"})

    return render(request, "student/dashboard.html", {
        "profile": profile,
        "upcoming": upcoming,
        "history": history,
        "case_notes": notes_data,
    })


@role_required("student")
def appointments_view(request):
    """Appointments page — booking form + tables."""
    profile = request.profile

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "book":
            counselor_id = request.POST.get("counselor_id")
            date_str = request.POST.get("scheduled_date")
            time_str = request.POST.get("scheduled_time")
            concern = request.POST.get("concern_type", "other")
            notes = request.POST.get("notes", "")

            try:
                scheduled_dt = timezone.make_aware(
                    datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"),
                    timezone.get_current_timezone(),
                )
            except (ValueError, TypeError):
                messages.error(request, "Invalid date or time format.")
                return redirect("/appointments/")

            try:
                appt = book_appointment(
                    student=profile,
                    counselor=counselor_id,
                    scheduled_at=scheduled_dt,
                    concern_type=concern,
                    notes=notes,
                )
                messages.success(request, "Appointment booked successfully!")
            except Exception as e:
                msg = getattr(e, "message", str(e))
                messages.error(request, msg)
            return redirect("/appointments/")

        elif action == "cancel":
            appt_id = request.POST.get("appointment_id")
            try:
                cancel_appointment_student(appt_id, profile)
                messages.success(request, "Appointment cancelled.")
            except Exception as e:
                msg = getattr(e, "message", str(e))
                messages.error(request, msg)
            return redirect("/appointments/")

    # GET data
    counselors = Profile.objects.filter(role="counselor", is_active=True).order_by("full_name")

    upcoming = Appointment.objects.filter(
        student=profile,
        status__in=["pending", "confirmed"],
    ).select_related("counselor").order_by("scheduled_at")

    past = Appointment.objects.filter(
        student=profile,
    ).exclude(
        status__in=["pending", "confirmed"],
    ).select_related("counselor").order_by("-scheduled_at")

    return render(request, "student/appointments.html", {
        "profile": profile,
        "counselors": counselors,
        "upcoming": upcoming,
        "past": past,
    })


@role_required("student")
def get_slots_api(request):
    """AJAX endpoint: return available slots for a counselor on a date."""
    counselor_id = request.GET.get("counselor_id")
    date_str = request.GET.get("date")

    if not counselor_id or not date_str:
        return JsonResponse({"slots": []})

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"slots": []})

    slots = get_available_slots(counselor_id, date_obj)
    return JsonResponse({
        "slots": [
            {"value": s.strftime("%H:%M"), "label": s.strftime("%I:%M %p")}
            for s in slots
        ]
    })


@role_required("student")
def profile_view(request):
    """Student profile — read-only info + password change link."""
    return render(request, "student/profile.html", {
        "profile": request.profile,
    })


@role_required("student")
def front_desk_view(request):
    """Front desk info page — static info about in-person booking."""
    return render(request, "student/front_desk.html", {
        "profile": request.profile,
    })


@role_required("student")
def chatbot_page_view(request):
    """Chatbot page — info cards + embedded chat widget."""
    return render(request, "student/chatbot.html", {
        "profile": request.profile,
    })


@role_required("student")
def mood_checkin_view(request):
    """POST: process mood check-in."""
    if request.method != "POST":
        return redirect("/student/")

    mood = request.POST.get("mood", "").lower()
    note = request.POST.get("note", "")

    result = process_mood_checkin(request.profile, mood, note)

    if result.get("ok"):
        if result.get("notified"):
            messages.success(
                request,
                f"Your counselor {result.get('counselor_name', '')} has been notified."
            )
        else:
            messages.success(request, "Thank you for checking in!")
    else:
        messages.error(request, result.get("error", "Could not process check-in."))

    return redirect("/student/")


@role_required("student")
def cancel_appointment_view(request, appointment_id):
    """Direct POST action endpoint to cancel a student appointment."""
    if request.method == "POST":
        try:
            cancel_appointment_student(appointment_id, request.profile)
            messages.success(request, "Appointment cancelled.")
        except Exception as e:
            msg = getattr(e, "message", str(e))
            messages.error(request, msg)
    return redirect(request.META.get("HTTP_REFERER", "/appointments/"))

