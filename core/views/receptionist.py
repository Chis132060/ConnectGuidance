"""
core/views/receptionist.py — Receptionist views for GuidanceConnect Django replica.

Implements FLOWS §16:
- 4-step walk-in appointment booking (/receptionist/)
- Student search API endpoint (/receptionist/search-students/)
- Walk-in booking submission (/receptionist/book/)
"""

import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.guards import require_receptionist
from core.models import Profile, Appointment
from core.choices import RoleChoices, ConcernTypeChoices, AppointmentStatusChoices
from core.forms import ReceptionistBookingForm
from core.services.receptionist import (
    search_students,
    list_reception_counselors,
    book_receptionist_appointment,
)
from core.services.slots import get_available_slots_for_counselor, get_first_available_counselor_slot


@require_receptionist
def receptionist_dashboard_view(request):
    """
    FLOWS §16: Receptionist desk dashboard.
    Renders 4-step booking interface and lists today's booked appointments.
    """
    receptionist = request.user.profile
    today = timezone.localdate()

    day_start = timezone.make_aware(
        datetime.datetime.combine(today, datetime.time.min),
        timezone.get_current_timezone()
    )
    day_end = timezone.make_aware(
        datetime.datetime.combine(today, datetime.time.max),
        timezone.get_current_timezone()
    )

    counselors = list_reception_counselors()

    today_appointments = Appointment.objects.filter(
        scheduled_at__range=(day_start, day_end)
    ).select_related('student', 'counselor', 'student__user', 'counselor__user').order_by('scheduled_at')

    context = {
        'profile': receptionist,
        'counselors': counselors,
        'today_appointments': today_appointments,
        'concern_choices': ConcernTypeChoices.choices,
    }
    return render(request, 'receptionist/booking.html', context)


@require_receptionist
@require_http_methods(["GET"])
def receptionist_search_students_view(request):
    """
    FLOWS §16 Step 1: Search active students by name or student ID (max 25 results).
    """
    query = request.GET.get('q', '').strip()
    students = search_students(query, limit=25)

    data = [
        {
            'id': s.id,
            'full_name': s.full_name,
            'student_id': s.student_id or '—',
            'email': s.user.email,
            'department': s.department or '—',
        }
        for s in students
    ]
    return JsonResponse({'results': data, 'count': len(data)})


@require_receptionist
@require_http_methods(["POST"])
def receptionist_book_view(request):
    """
    FLOWS §16 Step 4: Book appointment for student.
    Handles specific counselor or "next available" (counselor_id is 0 or empty).
    """
    receptionist = request.user.profile

    student_id = request.POST.get('student_id')
    counselor_id = request.POST.get('counselor_id')
    scheduled_at_str = request.POST.get('scheduled_at')
    concern_type = request.POST.get('concern_type')
    notes = request.POST.get('notes', '')

    if not student_id or not scheduled_at_str or not concern_type:
        messages.error(request, "Please fill in all required booking fields.")
        return redirect('receptionist_dashboard')

    try:
        student = Profile.objects.get(id=student_id, role=RoleChoices.STUDENT, is_active=True)
    except Profile.DoesNotExist:
        messages.error(request, "Selected student is not active or does not exist.")
        return redirect('receptionist_dashboard')

    # Parse scheduled_at
    from django.utils.dateparse import parse_datetime
    scheduled_at = parse_datetime(scheduled_at_str)
    if not scheduled_at:
        try:
            scheduled_at = datetime.datetime.strptime(scheduled_at_str, '%Y-%m-%d %H:%M')
            scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())
        except (ValueError, TypeError):
            messages.error(request, "Invalid appointment date/time format.")
            return redirect('receptionist_dashboard')

    counselor = None
    if counselor_id and str(counselor_id) != '0' and str(counselor_id) != '':
        try:
            counselor = Profile.objects.get(id=counselor_id, role=RoleChoices.COUNSELOR, is_active=True)
        except Profile.DoesNotExist:
            messages.error(request, "Selected counselor is not available.")
            return redirect('receptionist_dashboard')

    try:
        appt = book_receptionist_appointment(
            receptionist=receptionist,
            student=student,
            scheduled_at=scheduled_at,
            concern_type=concern_type,
            counselor=counselor,
            notes=notes
        )
        messages.success(
            request,
            f"Walk-in appointment successfully booked for {student.full_name} with counselor {appt.counselor.full_name}."
        )
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, 'message') else e))
    except Exception as e:
        messages.error(request, f"Could not create appointment: {e}")

    return redirect('receptionist_dashboard')
