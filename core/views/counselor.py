"""
core/views/counselor.py — Counselor views for GuidanceConnect Django replica.

Implements Standardized Counselor Features:
1. Dashboard (Workspace & clinical overview)
2. Appointments (Full clinical schedule and state transitions)
3. Case Notes (Encrypted clinical case note repository)
4. Student/Wellness information (Student roster & mood alerts)
5. Profile (Provider credentials and security settings)
"""

import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, Http404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from django.db.models import Q

from apps.authentication.guards import require_counselor
from core.models import Appointment, StudentMoodAlert, CaseNote, Profile
from apps.common.choices import AppointmentStatusChoices, ConcernTypeChoices
from core.services.appointments import counselor_update_status


@require_counselor
def counselor_workspace_view(request):
    """
    COUNSELOR #1: Dashboard.
    Loads today's sessions, upcoming appointments, pending requests, and summary statistics.
    """
    counselor = request.user.profile
    today = timezone.localdate()

    day_start = timezone.make_aware(
        datetime.datetime.combine(today, datetime.time.min),
        timezone.get_current_timezone()
    )
    day_end = timezone.make_aware(
        datetime.datetime.combine(today, datetime.time.max),
        timezone.get_current_timezone()
    )

    my_appointments = Appointment.objects.filter(
        counselor=counselor
    ).select_related('student', 'student__user').order_by('scheduled_at')

    today_sessions = my_appointments.filter(
        scheduled_at__range=(day_start, day_end)
    ).exclude(status=AppointmentStatusChoices.CANCELLED)

    upcoming_sessions = my_appointments.filter(
        scheduled_at__gt=day_end,
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED]
    )

    pending_sessions = my_appointments.filter(
        status=AppointmentStatusChoices.PENDING
    )

    past_sessions = my_appointments.filter(
        status=AppointmentStatusChoices.COMPLETED
    ).order_by('-scheduled_at')[:10]

    mood_alerts = StudentMoodAlert.objects.filter(
        counselor=counselor
    ).select_related('student', 'student__user').order_by('-created_at')[:8]

    context = {
        'profile': counselor,
        'today_sessions': today_sessions,
        'upcoming_sessions': upcoming_sessions,
        'pending_sessions': pending_sessions,
        'past_sessions': past_sessions,
        'mood_alerts': mood_alerts,
        'stats': {
            'today_count': today_sessions.count(),
            'upcoming_count': upcoming_sessions.count(),
            'pending_count': pending_sessions.count(),
            'completed_count': my_appointments.filter(status=AppointmentStatusChoices.COMPLETED).count(),
        }
    }
    return render(request, 'counselor/workspace.html', context)


@require_counselor
def counselor_appointments_view(request):
    """
    COUNSELOR #2: Appointments.
    Dedicated clinical appointments list with status filters, student search, and state transitions.
    """
    counselor = request.user.profile
    status_filter = request.GET.get('status', 'all').strip().lower()
    search_query = request.GET.get('q', '').strip()

    appointments = Appointment.objects.filter(
        counselor=counselor
    ).select_related('student', 'student__user').order_by('-scheduled_at')

    if status_filter and status_filter != 'all':
        appointments = appointments.filter(status=status_filter)

    if search_query:
        appointments = appointments.filter(
            Q(student__full_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query) |
            Q(student__user__email__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    all_my_appointments = Appointment.objects.filter(counselor=counselor)

    counts = {
        'all': all_my_appointments.count(),
        'pending': all_my_appointments.filter(status=AppointmentStatusChoices.PENDING).count(),
        'confirmed': all_my_appointments.filter(status=AppointmentStatusChoices.CONFIRMED).count(),
        'completed': all_my_appointments.filter(status=AppointmentStatusChoices.COMPLETED).count(),
        'cancelled': all_my_appointments.filter(status=AppointmentStatusChoices.CANCELLED).count(),
    }

    context = {
        'profile': counselor,
        'appointments': appointments,
        'counts': counts,
        'active_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'counselor/appointments.html', context)


@require_counselor
def counselor_case_notes_list_view(request):
    """
    COUNSELOR #3: Case Notes Repository.
    Lists all clinical sessions with encrypted note authoring status and confidentiality badges.
    """
    counselor = request.user.profile
    search_query = request.GET.get('q', '').strip()

    appointments = Appointment.objects.filter(
        counselor=counselor
    ).select_related('student', 'student__user').prefetch_related('case_notes').order_by('-scheduled_at')

    if search_query:
        appointments = appointments.filter(
            Q(student__full_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query)
        )

    sessions_with_notes = []
    total_notes_count = 0
    confidential_count = 0

    for appt in appointments:
        note = next((n for n in appt.case_notes.all() if n.counselor_id == counselor.id), None)
        if note:
            total_notes_count += 1
            if note.is_confidential:
                confidential_count += 1
        sessions_with_notes.append({
            'appointment': appt,
            'note': note,
            'has_note': note is not None,
        })

    context = {
        'profile': counselor,
        'sessions_with_notes': sessions_with_notes,
        'search_query': search_query,
        'stats': {
            'total_sessions': appointments.count(),
            'notes_authored': total_notes_count,
            'confidential_notes': confidential_count,
        }
    }
    return render(request, 'counselor/case_notes_list.html', context)


@require_counselor
def counselor_wellness_view(request):
    """
    COUNSELOR #4: Student / Wellness Information.
    Lists assigned students, recent mood check-ins, alerts, and wellness histories.
    """
    counselor = request.user.profile

    alerts = StudentMoodAlert.objects.filter(
        counselor=counselor
    ).select_related('student', 'student__user').order_by('-created_at')

    # Distinct students assigned to this counselor
    student_ids = Appointment.objects.filter(
        counselor=counselor
    ).values_list('student_id', flat=True).distinct()

    students = Profile.objects.filter(
        id__in=student_ids
    ).select_related('user').order_by('full_name')

    students_with_history = []
    for s in students:
        recent_appt = Appointment.objects.filter(
            counselor=counselor, student=s
        ).order_by('-scheduled_at').first()
        student_alerts = alerts.filter(student=s).count()
        students_with_history.append({
            'student': s,
            'recent_appt': recent_appt,
            'alerts_count': student_alerts,
        })

    context = {
        'profile': counselor,
        'alerts': alerts,
        'students_with_history': students_with_history,
        'stats': {
            'active_students': len(students_with_history),
            'total_alerts': alerts.count(),
        }
    }
    return render(request, 'counselor/wellness.html', context)


@require_counselor
@require_http_methods(["GET", "POST"])
def counselor_profile_view(request):
    """
    COUNSELOR #5: Profile.
    Counselor clinical credentials and password security administration.
    """
    counselor = request.user.profile

    if request.method == 'POST':
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, "Your counselor password has been successfully updated.")
            return redirect('counselor_profile')
        else:
            messages.error(request, "Please correct the password errors below.")
    else:
        password_form = PasswordChangeForm(user=request.user)

    total_sessions = Appointment.objects.filter(counselor=counselor).count()
    completed_sessions = Appointment.objects.filter(
        counselor=counselor, status=AppointmentStatusChoices.COMPLETED
    ).count()

    context = {
        'profile': counselor,
        'user': request.user,
        'password_form': password_form,
        'stats': {
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
        }
    }
    return render(request, 'counselor/profile.html', context)


@require_counselor
@require_http_methods(["POST"])
def counselor_status_update_view(request, pk: int):
    """
    Counselor updates appointment status.
    Strictly enforces state machine:
    - pending → confirmed, cancelled
    - confirmed → completed, cancelled
    - completed / cancelled → terminal
    """
    counselor = request.user.profile

    try:
        appointment = Appointment.objects.get(id=pk)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found.")

    if appointment.counselor_id != counselor.id:
        return HttpResponseForbidden("Only counselors assigned to this appointment can update its status.")

    new_status = request.POST.get('status', '').strip().lower()

    try:
        counselor_update_status(appointment, new_status, counselor)
        messages.success(request, f"Appointment status updated to '{new_status}'.")
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, 'message') else e))

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'counselor_workspace'
    return redirect(next_url)
