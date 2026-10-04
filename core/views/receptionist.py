"""
Receptionist views — walk-in appointment booking workflow, dashboard, front desk, and profile.
Handles student lookup, counselor availability scheduling, and appointment creation.
"""
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from core.guards import role_required
from core.models import Profile, Appointment
from core.services.receptionist import (
    search_students,
    list_counselors,
    find_next_available,
    book_for_student,
)
from core.services.slots import get_available_slots
from core.services.appointments import book_appointment


@role_required("receptionist")
def dashboard_view(request):
    """Receptionist dashboard overview."""
    profile = request.profile
    today = timezone.now().date()

    today_appts = Appointment.objects.filter(
        scheduled_at__date=today
    ).select_related("student", "counselor").order_by("scheduled_at")

    counselors = Profile.objects.filter(role="counselor", is_active=True).order_by("full_name")

    stats = {
        "today_total": today_appts.count(),
        "today_pending": today_appts.filter(status="pending").count(),
        "today_confirmed": today_appts.filter(status="confirmed").count(),
        "today_completed": today_appts.filter(status="completed").count(),
    }

    return render(request, "receptionist/dashboard.html", {
        "profile": profile,
        "today_appointments": today_appts,
        "counselors": counselors,
        "stats": stats,
    })


@role_required("receptionist")
def booking_view(request):
    """4-step receptionist walk-in booking workflow."""
    profile = request.profile

    if request.method == "POST":
        student_id = request.POST.get("student_id")
        counselor_id = request.POST.get("counselor_id")
        date_str = request.POST.get("scheduled_date")
        time_str = request.POST.get("scheduled_time")
        concern = request.POST.get("concern_type", "other")
        notes = request.POST.get("notes", "")

        try:
            student_profile = Profile.objects.get(pk=student_id, role="student", is_active=True)
        except Profile.DoesNotExist:
            messages.error(request, "Student not found or inactive.")
            return redirect("/receptionist/")

        try:
            scheduled_dt = timezone.make_aware(
                datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"),
                timezone.get_current_timezone(),
            )
        except (ValueError, TypeError):
            messages.error(request, "Invalid date or time.")
            return redirect("/receptionist/")

        try:
            appt = book_for_student(
                receptionist=profile,
                student=student_profile,
                scheduled_at=scheduled_dt,
                concern_type=concern,
                counselor=counselor_id,
                notes=notes,
            )
            messages.success(
                request,
                f"Appointment booked for {student_profile.full_name} with {appt.counselor.full_name}. Status: Pending."
            )
        except Exception as e:
            msg = getattr(e, "message", str(e))
            messages.error(request, msg)
        return redirect("/receptionist/")

    # GET
    search_query = request.GET.get("search", "")
    students = []
    if search_query:
        students = search_students(search_query)

    counselors = list_counselors()

    return render(request, "receptionist/booking.html", {
        "profile": profile,
        "students": students,
        "counselors": counselors,
        "search_query": search_query,
    })


@role_required("receptionist")
def front_desk_view(request):
    """Receptionist front desk information and office guidelines."""
    return render(request, "receptionist/front_desk.html", {
        "profile": request.profile,
    })


@role_required("receptionist")
def profile_view(request):
    """Receptionist staff profile."""
    return render(request, "receptionist/profile.html", {
        "profile": request.profile,
    })


@role_required("receptionist")
def receptionist_slots_api(request):
    """AJAX: get available slots for a counselor on a date."""
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
