"""
core/views/receptionist.py — Receptionist views for GuidanceConnect Django replica.

Implements Standardized Receptionist Features:
1. Dashboard (Desk metrics and daily arrivals summary)
2. Appointments / Walk-ins (4-step walk-in intake engine)
3. Front Desk (Live arrivals queue & counselor duty roster)
4. Profile (Staff credentials & password security management)
"""

import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.decorators import require_receptionist
from accounts.models import Profile
from accounts.choices import RoleChoices
from core.models import Appointment
from core.choices import ConcernTypeChoices, AppointmentStatusChoices
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
    RECEPTIONIST #1: Dashboard.
    Front desk daily KPIs, arrivals overview, and provider availability summary.
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

    today_total = today_appointments.count()
    today_confirmed = today_appointments.filter(status=AppointmentStatusChoices.CONFIRMED).count()
    today_pending = today_appointments.filter(status=AppointmentStatusChoices.PENDING).count()
    today_completed = today_appointments.filter(status=AppointmentStatusChoices.COMPLETED).count()

    context = {
        'profile': receptionist,
        'counselors': counselors,
        'today_appointments': today_appointments,
        'stats': {
            'today_total': today_total,
            'today_confirmed': today_confirmed,
            'today_pending': today_pending,
            'today_completed': today_completed,
            'active_counselors': len(counselors),
        }
    }
    return render(request, 'receptionist/dashboard.html', context)


@require_receptionist
def receptionist_walk_ins_view(request):
    """
    RECEPTIONIST #2: Appointments / Walk-ins.
    4-step walk-in appointment booking wizard.
    """
    receptionist = request.user.profile
    counselors = list_reception_counselors()

    context = {
        'profile': receptionist,
        'counselors': counselors,
        'concern_choices': ConcernTypeChoices.choices,
    }
    return render(request, 'receptionist/booking.html', context)


@require_receptionist
def receptionist_front_desk_view(request):
    """
    RECEPTIONIST #3: Front Desk.
    Live queue tracker, student arrival verification, and real-time station triage.
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

    today_appointments = Appointment.objects.filter(
        scheduled_at__range=(day_start, day_end)
    ).select_related('student', 'counselor', 'student__user', 'counselor__user').order_by('scheduled_at')

    counselors = list_reception_counselors()

    context = {
        'profile': receptionist,
        'today_appointments': today_appointments,
        'counselors': counselors,
        'today_date': today,
    }
    return render(request, 'receptionist/front_desk.html', context)


@require_receptionist
@require_http_methods(["GET", "POST"])
def receptionist_profile_view(request):
    """
    RECEPTIONIST #4: Profile.
    Staff credentials and password security settings.
    """
    receptionist = request.user.profile

    if request.method == 'POST':
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, "Your receptionist password has been successfully updated.")
            return redirect('receptionist_profile')
        else:
            messages.error(request, "Please correct the password errors below.")
    else:
        password_form = PasswordChangeForm(user=request.user)

    context = {
        'profile': receptionist,
        'user': request.user,
        'password_form': password_form,
    }
    return render(request, 'receptionist/profile.html', context)


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
    Handles specific counselor or 'next available' (counselor_id is 0 or empty).
    """
    receptionist = request.user.profile

    student_id = request.POST.get('student_id')
    counselor_id = request.POST.get('counselor_id')
    scheduled_at_str = request.POST.get('scheduled_at')
    concern_type = request.POST.get('concern_type')
    notes = request.POST.get('notes', '')

    if not student_id or not scheduled_at_str or not concern_type:
        messages.error(request, "Please fill in all required booking fields.")
        return redirect('receptionist_walk_ins')

    try:
        student = Profile.objects.get(id=student_id, role=RoleChoices.STUDENT, is_active=True)
    except Profile.DoesNotExist:
        messages.error(request, "Selected student is not active or does not exist.")
        return redirect('receptionist_walk_ins')

    # Parse scheduled_at
    from django.utils.dateparse import parse_datetime
    scheduled_at = parse_datetime(scheduled_at_str)
    if not scheduled_at:
        try:
            scheduled_at = datetime.datetime.strptime(scheduled_at_str, '%Y-%m-%d %H:%M')
            scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())
        except (ValueError, TypeError):
            messages.error(request, "Invalid appointment date/time format.")
            return redirect('receptionist_walk_ins')

    counselor = None
    if counselor_id and str(counselor_id) != '0' and str(counselor_id) != '':
        try:
            counselor = Profile.objects.get(id=counselor_id, role=RoleChoices.COUNSELOR, is_active=True)
        except Profile.DoesNotExist:
            messages.error(request, "Selected counselor is not available.")
            return redirect('receptionist_walk_ins')

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

    return redirect('receptionist_walk_ins')
