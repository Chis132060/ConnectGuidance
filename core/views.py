"""
core/views.py — ConnectGuidance Central Domain View Layer

Implements all role-based view endpoints for GuidanceConnect:
1. Student Portal (Dashboard, slots, booking, cancellation, mood check-ins, profile)
2. Counselor Portal (Workspace, clinical queue, encrypted case notes, wellness, status transitions)
3. Receptionist Desk (Front desk dashboard, triage arrivals queue, 4-step walk-in intake, search)
4. Administrator Portal (Executive KPI overview, filtered reports, user management, audit logs, appointments registry)
5. AI Guidance Chatbot (Session hydration, SSE streaming, rate limiting, and crisis safety protocol)
"""

import io
import csv
import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import (
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
    HttpResponseForbidden,
    HttpResponseBadRequest,
    Http404,
)
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count, Q, Max
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

# Role-Based Access Control Guards & Accounts
from accounts.decorators import (
    require_student,
    require_counselor,
    require_receptionist,
    require_admin,
)
from accounts.models import Profile
from accounts.choices import RoleChoices
from accounts.constants import FSUU_PROGRAM_CHOICES

# Core Models, Choices, and Forms
from core.models import (
    Appointment,
    CaseNote,
    AuditLog,
    ChatbotSession,
    StudentMoodAlert,
)
from core.choices import (
    AppointmentStatusChoices,
    ConcernTypeChoices,
)
from core.forms import (
    AppointmentBookingForm,
    ReceptionistBookingForm,
    MoodCheckInForm,
    CaseNoteForm,
)

# Core Domain Services
from core.services.slots import (
    get_available_slots_for_counselor,
    get_first_available_counselor_slot,
)
from core.services.appointments import (
    book_appointment,
    student_cancel_appointment,
    counselor_update_status,
)
from core.services.mood import process_mood_checkin
from core.services.case_notes import (
    save_case_note,
    get_decrypted_case_note,
    get_student_shared_case_notes,
)
from core.services.encryption import encrypt, decrypt
from core.services.receptionist import (
    search_students,
    list_reception_counselors,
    book_receptionist_appointment,
    ensure_timezone_aware,
)
from core.services.metrics import get_admin_metrics
from core.services.reports import (
    filter_appointments,
    export_appointments_csv,
    export_appointments_pdf,
)
from core.services.audit import log_action
from core.services.management import (
    can_change_active_status,
    update_user_status,
    create_user_by_admin,
)
from core.services.chat import (
    check_chat_rate_limit,
    check_session_get_rate_limit,
    get_chat_retry_after,
    has_llm_api_key,
    stream_chat_response,
    save_or_update_session,
    should_trigger_booking_cta,
    is_crisis_text,
)


# ==============================================================================
# 1. STUDENT PORTAL VIEWS
# ==============================================================================

@require_student
def student_dashboard_view(request):
    """
    Student dashboard overview: greeting, mood widget, upcoming appointments,
    and non-confidential case note history.
    """
    student = request.user.profile
    now = timezone.now()

    upcoming_appointments = Appointment.objects.filter(
        student=student,
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED]
    ).select_related('counselor', 'counselor__user').order_by('scheduled_at')

    completed_appointments = Appointment.objects.filter(
        student=student,
        status=AppointmentStatusChoices.COMPLETED
    ).select_related('counselor', 'counselor__user').order_by('-scheduled_at')

    past_appointments = Appointment.objects.filter(
        student=student,
        status__in=[AppointmentStatusChoices.COMPLETED, AppointmentStatusChoices.CANCELLED]
    ).select_related('counselor', 'counselor__user').order_by('-scheduled_at')[:5]

    next_appointment = upcoming_appointments.filter(scheduled_at__gte=now).first()
    if not next_appointment:
        next_appointment = upcoming_appointments.first()

    completed_count = completed_appointments.count()

    case_notes_history = list(get_student_shared_case_notes(student).values())[:5]

    context = {
        'profile': student,
        'next_appointment': next_appointment,
        'upcoming_appointments': upcoming_appointments,
        'upcoming_count': upcoming_appointments.count(),
        'past_count': completed_count,
        'completed_count': completed_count,
        'past_appointments': past_appointments,
        'case_notes_history': case_notes_history,
        'mood_form': MoodCheckInForm(),
    }
    return render(request, 'student/dashboard.html', context)


@require_student
def student_appointments_list_view(request):
    """List student appointments categorized into upcoming and past/history."""
    student = request.user.profile

    upcoming_appointments = list(Appointment.objects.filter(
        student=student,
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED]
    ).select_related('counselor', 'counselor__user').order_by('scheduled_at'))

    past_appointments = list(Appointment.objects.filter(
        student=student
    ).exclude(
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED]
    ).select_related('counselor', 'counselor__user').order_by('-scheduled_at'))

    student_case_notes = get_student_shared_case_notes(student)
    for appointment in upcoming_appointments + past_appointments:
        appointment.student_case_note = student_case_notes.get(appointment.id)

    counselors = Profile.objects.filter(
        role=RoleChoices.COUNSELOR,
        is_active=True
    ).order_by('full_name')

    form = AppointmentBookingForm()

    context = {
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'counselors': counselors,
        'form': form,
    }
    return render(request, 'student/appointments.html', context)


@require_student
@require_http_methods(["GET"])
def student_slots_view(request):
    """
    Get available hourly slots for a chosen counselor on a target date.
    Params: counselor_id (int), date (YYYY-MM-DD).
    """
    counselor_id = request.GET.get('counselor_id')
    date_str = request.GET.get('date')

    if not counselor_id or not date_str:
        return JsonResponse({'error': 'counselor_id and date are required.'}, status=400)

    try:
        counselor = Profile.objects.get(
            id=counselor_id,
            role=RoleChoices.COUNSELOR,
            is_active=True
        )
    except Profile.DoesNotExist:
        return JsonResponse({'error': 'That counselor is not available.'}, status=404)

    target_date = parse_date(date_str)
    if not target_date:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

    slots = get_available_slots_for_counselor(counselor, target_date)
    return JsonResponse({
        'counselor_id': counselor.id,
        'counselor_name': counselor.full_name,
        'date': date_str,
        'slots': slots
    })


@require_student
@require_http_methods(["GET", "POST"])
def student_book_appointment_view(request):
    """Student books an appointment with selected counselor, concern type, and time slot."""
    student = request.user.profile
    counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).order_by('full_name')

    if request.method == 'POST':
        form = AppointmentBookingForm(request.POST)
        if form.is_valid():
            counselor_id = form.cleaned_data['counselor_id']
            scheduled_at = form.cleaned_data['scheduled_at']
            concern_type = form.cleaned_data['concern_type']
            notes = form.cleaned_data.get('notes', '')

            if scheduled_at <= timezone.now():
                messages.error(request, "Choose future date and time.")
                return render(request, 'student/book_appointment.html', {'form': form, 'counselors': counselors})

            try:
                counselor = Profile.objects.get(
                    id=counselor_id,
                    role=RoleChoices.COUNSELOR,
                    is_active=True
                )
            except Profile.DoesNotExist:
                messages.error(request, "That counselor is not available.")
                return render(request, 'student/book_appointment.html', {'form': form, 'counselors': counselors})

            try:
                book_appointment(
                    student=student,
                    counselor=counselor,
                    scheduled_at=scheduled_at,
                    concern_type=concern_type,
                    notes=notes,
                    created_by_receptionist=False,
                    actor=student
                )
                messages.success(request, f"Your appointment with {counselor.full_name} has been requested.")
                return redirect('student_appointments')
            except ValidationError as e:
                err_msg = str(e.message) if hasattr(e, 'message') else str(e)
                if 'no longer available' in err_msg.lower() or 'clash' in err_msg.lower():
                    messages.error(request, "That time was just taken. Please choose another slot.")
                else:
                    messages.error(request, err_msg)
            except Exception:
                messages.error(request, "Could not save appointment. Please try again.")
        else:
            messages.error(request, "Invalid booking details. Please check all fields.")
    else:
        form = AppointmentBookingForm()

    return render(request, 'student/book_appointment.html', {
        'form': form,
        'counselors': counselors,
    })


@require_student
@require_http_methods(["POST"])
def student_cancel_appointment_view(request, pk: int):
    """Student cancels their own appointment."""
    student = request.user.profile

    try:
        appointment = Appointment.objects.get(id=pk, student=student)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found.")

    if appointment.status in [AppointmentStatusChoices.COMPLETED, AppointmentStatusChoices.CANCELLED]:
        messages.error(request, "Can no longer be cancelled.")
        return redirect('student_appointments')

    try:
        student_cancel_appointment(appointment, student)
        messages.success(request, "Your appointment has been cancelled.")
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect('student_appointments')


@require_student
@require_http_methods(["POST"])
def student_mood_checkin_view(request):
    """Student submits wellness mood check-in with safety alert dispatch."""
    student = request.user.profile
    form = MoodCheckInForm(request.POST)

    if form.is_valid():
        mood = form.cleaned_data['mood']
        note = form.cleaned_data.get('note', '')
        try:
            result = process_mood_checkin(student, mood, note)
            if result.get('status') == 'alert_dispatched':
                messages.info(request, result['message'])
            elif result.get('status') == 'warning':
                messages.warning(request, result['message'])
            else:
                messages.success(request, result['message'])
        except ValidationError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, "Please select a valid mood option.")

    return redirect('student_dashboard')


@require_student
@require_http_methods(["GET", "POST"])
def student_profile_view(request):
    """Student profile with read-only account details and embedded password change form."""
    student = request.user.profile

    if request.method == 'POST':
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, "Your password has been successfully updated.")
            return redirect('student_profile')
        else:
            messages.error(request, "Please correct the password errors below.")
    else:
        password_form = PasswordChangeForm(user=request.user)

    context = {
        'profile': student,
        'user': request.user,
        'password_form': password_form,
    }
    return render(request, 'student/profile.html', context)


@require_student
def student_front_desk_view(request):
    """Student front desk information and contact protocols."""
    return render(request, 'student/front_desk.html', {
        'profile': request.user.profile
    })


# ==============================================================================
# 2. COUNSELOR PORTAL VIEWS
# ==============================================================================

@require_counselor
def counselor_workspace_view(request):
    """Counselor workspace overview: today's sessions, pending requests, and wellness alerts."""
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
    """Clinical appointments list with status filters, student search, and state transitions."""
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
    """Case Notes Repository: lists clinical sessions with encrypted note authoring status."""
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
    """Assigned students list, recent mood check-ins, alerts, and wellness histories."""
    counselor = request.user.profile

    alerts = StudentMoodAlert.objects.filter(
        counselor=counselor
    ).select_related('student', 'student__user').order_by('-created_at')

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
    """Counselor clinical credentials and password security settings."""
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
    """Counselor updates appointment status strictly enforcing state transitions."""
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


@require_counselor
@require_http_methods(["GET", "POST"])
def counselor_case_note_view(request, appointment_id: int):
    """Case note editor: encrypts content with AES-256 before persisting to database."""
    counselor = request.user.profile

    try:
        appointment = Appointment.objects.select_related('student', 'student__user').get(id=appointment_id)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found.")

    if appointment.counselor_id != counselor.id:
        return HttpResponseForbidden("You are not assigned to this appointment.")

    existing_note = CaseNote.objects.filter(appointment=appointment, counselor=counselor).first()
    decrypted_content = ""

    if existing_note:
        try:
            decrypted_content = decrypt(existing_note.content)
        except Exception:
            messages.error(request, "Unable to decrypt existing note.")

    form = CaseNoteForm(
        request.POST or None,
        initial={
            'content': decrypted_content,
            'is_confidential': existing_note.is_confidential if existing_note else False,
        }
    )

    if request.method == 'POST' and form.is_valid():
        try:
            save_case_note(
                appointment=appointment,
                counselor=counselor,
                raw_content=form.cleaned_data['content'],
                is_confidential=form.cleaned_data['is_confidential']
            )
            messages.success(request, "Case note saved securely.")
            return redirect('counselor_case_note', appointment_id=appointment.id)
        except (PermissionDenied, ValidationError) as e:
            form.add_error(None, str(e))

    context = {
        'appointment': appointment,
        'existing_note': existing_note,
        'decrypted_content': decrypted_content,
        'form': form,
        'profile': counselor,
    }
    return render(request, 'case_notes/editor.html', context)


# ==============================================================================
# 3. RECEPTIONIST FRONT DESK VIEWS
# ==============================================================================

@require_receptionist
def receptionist_dashboard_view(request):
    """Front desk daily KPIs, arrivals overview, and provider availability summary."""
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
    """4-step walk-in appointment booking intake wizard."""
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
    """Live queue tracker, student arrival verification, and real-time station triage."""
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
    """Staff credentials and password security settings."""
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
    """Search active students by name or student ID (max 25 results)."""
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
    """Book appointment for student via walk-in intake."""
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

    scheduled_at = parse_datetime(scheduled_at_str)
    if not scheduled_at:
        try:
            scheduled_at = datetime.datetime.strptime(scheduled_at_str, '%Y-%m-%d %H:%M')
            scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())
        except (ValueError, TypeError):
            messages.error(request, "Invalid appointment date/time format.")
            return redirect('receptionist_walk_ins')
    scheduled_at = ensure_timezone_aware(scheduled_at)

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


# ==============================================================================
# 4. ADMINISTRATOR PORTAL & ANALYTICS VIEWS
# ==============================================================================

@require_admin
def admin_case_notes_view(request):
    """Review shared case notes while excluding counselor-only confidential notes."""
    admin_profile = request.user.profile
    notes = CaseNote.objects.filter(
        is_confidential=False
    ).select_related('appointment', 'appointment__student', 'counselor')

    search_query = request.GET.get('q', '').strip()
    if search_query:
        notes = notes.filter(
            Q(appointment__student__full_name__icontains=search_query) |
            Q(counselor__full_name__icontains=search_query)
        )

    note_items = []
    for note in notes:
        note_data = get_decrypted_case_note(note, admin_profile)
        if note_data:
            note_items.append({'note': note, 'content': note_data['content']})

    return render(request, 'admin/case_notes.html', {
        'profile': admin_profile,
        'note_items': note_items,
        'search_query': search_query,
    })


@require_admin
def admin_overview_view(request):
    """Executive Overview: KPIs, monthly trends, concern breakdown, and recent audit activity."""
    admin_profile = request.user.profile
    metrics = get_admin_metrics()
    recent_activity = AuditLog.objects.select_related('user').order_by('-created_at')[:10]

    weekly_series = metrics.get('weekly_series', [])
    concern_breakdown = metrics.get('concern_breakdown', [])

    weekly_labels = [item['label'] for item in weekly_series]
    weekly_data = [item['count'] for item in weekly_series]
    concern_labels = [item['label'] for item in concern_breakdown]
    concern_data = [item['count'] for item in concern_breakdown]

    context = {
        'profile': admin_profile,
        'kpis': {
            'total_students': metrics['total_students'],
            'total_counselors': metrics['total_counselors'],
            'monthly_appointments': metrics['monthly_appointments'],
            'completion_rate': metrics['completion_rate'],
            'total_appointments': metrics.get('total_appointments', sum(weekly_data)),
        },
        'status_counts': {
            'pending': metrics['pending_count'],
            'confirmed': metrics['confirmed_count'],
            'completed': metrics['completed_count'],
            'cancelled': metrics['cancelled_count'],
        },
        'weekly_labels': weekly_labels,
        'weekly_data': weekly_data,
        'concern_labels': concern_labels,
        'concern_data': concern_data,
        'weekly_labels_json': json.dumps(weekly_labels),
        'weekly_data_json': json.dumps(weekly_data),
        'concern_labels_json': json.dumps(concern_labels),
        'concern_data_json': json.dumps(concern_data),
        'weekly_series': weekly_series,
        'concern_breakdown': concern_breakdown,
        'weekly_series_json': json.dumps(weekly_series),
        'concern_breakdown_json': json.dumps(concern_breakdown),
        'recent_activity': recent_activity,
    }
    return render(request, 'analytics/overview.html', context)


@require_admin
def admin_reports_view(request):
    """Appointment reports generator with CSV and PDF export."""
    admin_profile = request.user.profile

    start_date = request.GET.get('date_from', '').strip()
    end_date = request.GET.get('date_to', '').strip()
    department = request.GET.get('department', '').strip()
    concern_type = request.GET.get('concern_type', '').strip()
    status = request.GET.get('status', '').strip()
    counselor_id = request.GET.get('counselor_id', '').strip()

    has_filters = bool(start_date or end_date or department or concern_type or status or counselor_id or request.GET.get('generate'))

    if has_filters:
        appointments = filter_appointments(
            start_date=start_date,
            end_date=end_date,
            department=department,
            concern_type=concern_type,
            status=status,
            counselor_id=int(counselor_id) if counselor_id.isdigit() else None
        )
    else:
        appointments = Appointment.objects.select_related('student', 'counselor').all().order_by('-scheduled_at')

    # Exports
    export_format = request.GET.get('export', '').strip().lower()
    if export_format == 'csv':
        return export_appointments_csv(appointments, exported_by=admin_profile)
    elif export_format == 'pdf':
        return export_appointments_pdf(appointments, exported_by=admin_profile)

    paginator = Paginator(appointments, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).order_by('full_name')

    summary = {
        'total': appointments.count(),
        'pending': appointments.filter(status=AppointmentStatusChoices.PENDING).count(),
        'confirmed': appointments.filter(status=AppointmentStatusChoices.CONFIRMED).count(),
        'completed': appointments.filter(status=AppointmentStatusChoices.COMPLETED).count(),
        'cancelled': appointments.filter(status=AppointmentStatusChoices.CANCELLED).count(),
    }

    context = {
        'profile': admin_profile,
        'appointments': page_obj,
        'page_obj': page_obj,
        'summary': summary,
        'counselors': counselors,
        'concern_choices': ConcernTypeChoices.choices,
        'status_choices': AppointmentStatusChoices.choices,
        'filters': {
            'date_from': start_date,
            'date_to': end_date,
            'department': department,
            'concern_type': concern_type,
            'status': status,
            'counselor_id': counselor_id,
        },
    }
    return render(request, 'analytics/reports.html', context)


@require_admin
@require_http_methods(["GET", "POST"])
def admin_users_view(request):
    """User Management: directory, role assignments, activation, manual creation."""
    admin_profile = request.user.profile

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_user':
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password', '')
            full_name = request.POST.get('full_name', '').strip()
            role = request.POST.get('role', RoleChoices.STUDENT)
            student_id = request.POST.get('student_id', '').strip()
            department = request.POST.get('department', '').strip()

            try:
                create_user_by_admin(
                    actor=admin_profile,
                    email=email,
                    password=password,
                    full_name=full_name,
                    role=role,
                    student_id=student_id or None,
                    department=department or None
                )
                messages.success(request, f"User account for {full_name} ({email}) created successfully.")
            except Exception as e:
                messages.error(request, str(e))

        elif action == 'toggle_status':
            target_id = request.POST.get('target_id')
            new_status_str = request.POST.get('new_is_active', 'false').lower()
            new_is_active = (new_status_str == 'true')
            target = get_object_or_404(Profile, id=target_id)
            try:
                update_user_status(admin_profile, target, new_is_active)
                st = "activated" if new_is_active else "deactivated"
                messages.success(request, f"User {target.full_name} has been {st}.")
            except Exception as e:
                messages.error(request, str(e))

        return redirect('admin_users')

    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    profiles_qs = Profile.objects.select_related('user').all().order_by('-user_no', 'full_name')

    if q:
        profiles_qs = profiles_qs.filter(
            Q(full_name__icontains=q) |
            Q(student_id__icontains=q) |
            Q(user__email__icontains=q)
        )

    if role_filter:
        profiles_qs = profiles_qs.filter(role=role_filter)

    if status_filter == 'active':
        profiles_qs = profiles_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        profiles_qs = profiles_qs.filter(is_active=False)

    paginator = Paginator(profiles_qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile': admin_profile,
        'page_obj': page_obj,
        'q': q,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': RoleChoices.choices,
        'programs': FSUU_PROGRAM_CHOICES,
    }
    return render(request, 'users/users.html', context)


@require_admin
def admin_audit_logs_view(request):
    """System Audit Trail: immutable activity logs with filtering and CSV export."""
    admin_profile = request.user.profile

    action_filter = request.GET.get('action', '').strip()
    table_filter = request.GET.get('table', '').strip()
    user_search = request.GET.get('user', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    logs_qs = AuditLog.objects.select_related('user').all().order_by('-created_at')

    if action_filter:
        logs_qs = logs_qs.filter(action=action_filter)
    if table_filter:
        logs_qs = logs_qs.filter(table_name=table_filter)
    if user_search:
        logs_qs = logs_qs.filter(
            Q(user__full_name__icontains=user_search) |
            Q(user__user__email__icontains=user_search)
        )
    if date_from:
        d = parse_date(date_from)
        if d:
            logs_qs = logs_qs.filter(created_at__date__gte=d)
    if date_to:
        d = parse_date(date_to)
        if d:
            logs_qs = logs_qs.filter(created_at__date__lte=d)

    # CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        response['Content-Disposition'] = f'attachment; filename="audit_logs_{timestamp}.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Timestamp", "User", "Role", "Action", "Table Name", "Record ID", "Metadata"])

        for l in logs_qs[:5000]:
            user_str = l.user.full_name if l.user else "System / Anonymous"
            role_str = l.user.role if l.user else "—"
            writer.writerow([
                l.id,
                l.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                user_str,
                role_str,
                l.action,
                l.table_name,
                str(l.record_id or ''),
                json.dumps(l.metadata or {})
            ])
        return response

    paginator = Paginator(logs_qs, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    actions = AuditLog.objects.values_list('action', flat=True).distinct()
    tables = AuditLog.objects.values_list('table_name', flat=True).distinct()

    context = {
        'profile': admin_profile,
        'page_obj': page_obj,
        'action_filter': action_filter,
        'table_filter': table_filter,
        'user_search': user_search,
        'date_from': date_from,
        'date_to': date_to,
        'actions': actions,
        'tables': tables,
    }
    return render(request, 'audit/logs.html', context)


@require_admin
def admin_appointments_view(request):
    """Full system-wide appointment registry with search, status filtering, and counselor lookup."""
    admin_profile = request.user.profile

    status_filter = request.GET.get('status', 'all').strip().lower()
    search_query = request.GET.get('q', '').strip()
    counselor_id = request.GET.get('counselor_id', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    appointments = Appointment.objects.select_related(
        'student', 'counselor', 'student__user', 'counselor__user'
    ).order_by('-scheduled_at')

    if status_filter and status_filter != 'all':
        appointments = appointments.filter(status=status_filter)

    if search_query:
        appointments = appointments.filter(
            Q(student__full_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query) |
            Q(counselor__full_name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    if counselor_id and counselor_id.isdigit():
        appointments = appointments.filter(counselor_id=int(counselor_id))

    if date_from:
        d = parse_date(date_from)
        if d:
            appointments = appointments.filter(scheduled_at__date__gte=d)

    if date_to:
        d = parse_date(date_to)
        if d:
            appointments = appointments.filter(scheduled_at__date__lte=d)

    all_appointments = Appointment.objects.all()
    counts = {
        'all': all_appointments.count(),
        'pending': all_appointments.filter(status=AppointmentStatusChoices.PENDING).count(),
        'confirmed': all_appointments.filter(status=AppointmentStatusChoices.CONFIRMED).count(),
        'completed': all_appointments.filter(status=AppointmentStatusChoices.COMPLETED).count(),
        'cancelled': all_appointments.filter(status=AppointmentStatusChoices.CANCELLED).count(),
    }

    counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).order_by('full_name')

    context = {
        'profile': admin_profile,
        'appointments': appointments[:200],
        'counts': counts,
        'active_filter': status_filter,
        'search_query': search_query,
        'counselors': counselors,
        'selected_counselor_id': counselor_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'admin/appointments.html', context)


@require_admin
@require_http_methods(["GET", "POST"])
def admin_profile_view(request):
    """Administrator credentials and password security settings."""
    admin_profile = request.user.profile

    if request.method == 'POST':
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, "Your administrator password has been updated.")
            return redirect('admin_profile')
        else:
            messages.error(request, "Please correct the password errors below.")
    else:
        password_form = PasswordChangeForm(user=request.user)

    total_users = Profile.objects.count()
    active_students = Profile.objects.filter(role=RoleChoices.STUDENT, is_active=True).count()
    active_counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).count()

    context = {
        'profile': admin_profile,
        'user': request.user,
        'password_form': password_form,
        'stats': {
            'total_users': total_users,
            'active_students': active_students,
            'active_counselors': active_counselors,
        }
    }
    return render(request, 'users/profile.html', context)


# ==============================================================================
# 5. AI CHATBOT & WELLNESS STREAMING VIEWS
# ==============================================================================

@require_student
def student_chatbot_page_view(request):
    """Render interactive student AI wellness chatbot screen."""
    return render(request, 'student/chatbot.html', {
        'profile': request.user.profile
    })


@require_student
@require_http_methods(["GET"])
def chat_session_get_view(request):
    """
    Restore or hydrate latest chatbot session for authenticated student.
    Rate limited to 60 GET requests per 15 minutes.
    """
    student = request.user.profile

    if not check_session_get_rate_limit(student.id):
        resp = JsonResponse({'error': 'Rate limit exceeded.'}, status=429)
        resp['Retry-After'] = str(get_chat_retry_after(student.id, is_post=False))
        return resp

    session = ChatbotSession.objects.filter(student=student).first()

    if session:
        return JsonResponse({
            'sessionId': session.id,
            'messages': session.messages
        })

    return JsonResponse({
        'sessionId': None,
        'messages': []
    })


@require_student
@require_http_methods(["POST"])
def chat_stream_post_view(request):
    """
    Streaming chat endpoint via Server-Sent Events (SSE).
    Enforces LLM config check, rate limiting (24/15min), 36-msg history cap,
    24,000 char cap, crisis protocol, and session persistence.
    """
    student = request.user.profile

    if not has_llm_api_key():
        return JsonResponse({'error': 'AI Chat service is not configured.'}, status=503)

    if not check_chat_rate_limit(student.id):
        resp = JsonResponse({'error': 'Rate limit exceeded. Please wait before sending more messages.'}, status=429)
        resp['Retry-After'] = str(get_chat_retry_after(student.id, is_post=True))
        return resp

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Malformed JSON body.'}, status=400)

    messages_list = body.get('messages', [])
    if not isinstance(messages_list, list) or not messages_list:
        return JsonResponse({'error': 'Messages list is required and cannot be empty.'}, status=400)

    last_msg = messages_list[-1]
    if not isinstance(last_msg, dict) or last_msg.get('role') != 'user' or not last_msg.get('content', '').strip():
        return JsonResponse({'error': 'Last message must have role "user" and non-empty content.'}, status=400)

    total_chars = sum(len(str(m.get('content', ''))) for m in messages_list)
    if total_chars > 24000:
        return JsonResponse({'error': 'Total message content exceeds the 24,000 character limit.'}, status=400)

    if len(messages_list) > 36:
        messages_list = messages_list[-36:]

    session_id = body.get('sessionId')
    if session_id:
        existing_session = ChatbotSession.objects.filter(id=session_id).first()
        if existing_session and existing_session.student_id != student.id:
            return HttpResponseForbidden("You do not own this chat session.")

    def event_stream():
        accumulated_chunks = []
        try:
            for delta in stream_chat_response(messages_list):
                accumulated_chunks.append(delta)
                event_data = json.dumps({'type': 'delta', 'chunk': delta})
                yield f"data: {event_data}\n\n"

            full_assistant_reply = "".join(accumulated_chunks)
            persisted_messages = messages_list + [{'role': 'assistant', 'content': full_assistant_reply}]
            saved_session = save_or_update_session(student, persisted_messages)

            should_suggest = (
                should_trigger_booking_cta(full_assistant_reply) or
                is_crisis_text(last_msg.get('content', ''))
            )

            done_event = json.dumps({
                'type': 'done',
                'sessionId': saved_session.id,
                'should_suggest': should_suggest,
                'is_crisis': is_crisis_text(last_msg.get('content', ''))
            })
            yield f"data: {done_event}\n\n"

        except Exception as e:
            err_event = json.dumps({'type': 'error', 'error': str(e)})
            yield f"data: {err_event}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
