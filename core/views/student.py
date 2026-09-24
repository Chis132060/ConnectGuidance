"""
core/views/student.py — Student views for GuidanceConnect Django replica.

Implements FLOWS §7-9, §13, §22:
- Dashboard shell (/student/)
- Available slots retrieval (/appointments/slots/)
- Appointment booking (/appointments/book/)
- Appointment listing (/appointments/)
- Appointment cancellation (/appointments/<int:pk>/cancel/)
- Mood check-in (/student/mood/)
- Student profile with password change (/student/profile/)
- Front desk information (/student/front-desk/)
"""

import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from core.guards import require_student
from core.models import Profile, Appointment, CaseNote
from core.choices import RoleChoices, AppointmentStatusChoices
from core.forms import AppointmentBookingForm, MoodCheckInForm
from core.services.slots import get_available_slots_for_counselor
from core.services.appointments import book_appointment, student_cancel_appointment
from core.services.mood import process_mood_checkin
from core.services.case_notes import get_decrypted_case_note


@require_student
def student_dashboard_view(request):
    """
    FLOWS §22: Student dashboard overview.
    Displays greeting, mood check-in widget, upcoming appointments, and non-confidential case history.
    """
    student = request.user.profile
    now = timezone.now()

    upcoming_appointments = Appointment.objects.filter(
        student=student,
        scheduled_at__gte=now,
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED]
    ).select_related('counselor', 'counselor__user').order_by('scheduled_at')

    past_appointments = Appointment.objects.filter(
        student=student
    ).filter(
        scheduled_at__lt=now
    ).exclude(
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED]
    ).select_related('counselor').order_by('-scheduled_at')[:5]

    next_appointment = upcoming_appointments.first()

    # Retrieve non-confidential case notes for this student's past sessions
    case_notes_raw = CaseNote.objects.filter(
        appointment__student=student,
        is_confidential=False
    ).select_related('counselor', 'appointment').order_by('-created_at')[:5]

    case_notes_history = []
    for cn in case_notes_raw:
        data = get_decrypted_case_note(cn, student)
        if data:
            case_notes_history.append(data)

    context = {
        'profile': student,
        'next_appointment': next_appointment,
        'upcoming_appointments': upcoming_appointments,
        'upcoming_count': upcoming_appointments.count(),
        'past_count': past_appointments.count(),
        'case_notes_history': case_notes_history,
        'mood_form': MoodCheckInForm(),
    }
    return render(request, 'student/dashboard.html', context)


@require_student
def student_appointments_list_view(request):
    """
    FLOWS §8/9: List student appointments categorized into upcoming and past/history.
    """
    student = request.user.profile
    now = timezone.now()

    upcoming_appointments = Appointment.objects.filter(
        student=student,
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED]
    ).select_related('counselor', 'counselor__user').order_by('scheduled_at')

    past_appointments = Appointment.objects.filter(
        student=student
    ).exclude(
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED]
    ).select_related('counselor', 'counselor__user').order_by('-scheduled_at')

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
    FLOWS §7: Get available hourly slots for a chosen counselor on a target date.
    Params:
      counselor_id (int)
      date (YYYY-MM-DD)
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
    """
    FLOWS §8: Student books an appointment.
    """
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
    """
    FLOWS §9: Student cancels their own appointment.
    """
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
    """
    FLOWS §13: Student submits wellness mood check-in.
    """
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
    """
    INTERFACES #7: Student profile with read-only account details and embedded password change form.
    """
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
    """
    INTERFACES #8: Student front desk static information and contact protocols.
    """
    return render(request, 'student/front_desk.html', {
        'profile': request.user.profile
    })
