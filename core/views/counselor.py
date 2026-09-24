"""
core/views/counselor.py — Counselor views for GuidanceConnect Django replica.

Implements FLOWS §10-12:
- Counselor workspace (/counselor/) with stats for today, upcoming, and past sessions
- Status update action (/counselor/appointments/<int:pk>/status/) enforcing state machine transitions
- Case note editor (/counselor/case-notes/<int:appointment_id>/) with AES-256 encryption and confidentiality controls
"""

import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, Http404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone

from core.guards import require_counselor
from core.models import Appointment, StudentMoodAlert, CaseNote
from core.choices import AppointmentStatusChoices
from core.forms import CaseNoteForm
from core.services.appointments import counselor_update_status
from core.services.case_notes import save_case_note, get_decrypted_case_note


@require_counselor
def counselor_workspace_view(request):
    """
    FLOWS §10: Counselor workspace.
    Loads today's sessions, upcoming appointments, past completed records, and statistics.
    """
    counselor = request.user.profile
    now = timezone.now()
    today = timezone.localdate()

    # Day bounds
    day_start = timezone.make_aware(
        datetime.datetime.combine(today, datetime.time.min),
        timezone.get_current_timezone()
    )
    day_end = timezone.make_aware(
        datetime.datetime.combine(today, datetime.time.max),
        timezone.get_current_timezone()
    )

    # Scoped appointments for this counselor
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

    # Mood alerts for this counselor
    mood_alerts = StudentMoodAlert.objects.filter(
        counselor=counselor
    ).select_related('student', 'student__user').order_by('-created_at')[:10]

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
@require_http_methods(["POST"])
def counselor_status_update_view(request, pk: int):
    """
    FLOWS §10: Counselor updates appointment status.
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

    return redirect('counselor_workspace')


@require_counselor
@require_http_methods(["GET", "POST"])
def counselor_case_note_view(request, appointment_id: int):
    """
    FLOWS §11 & §12: Case note editor and viewer for assigned counselor.
    - Active counselor + appointment.counselor == me else 404/403
    - Wires CaseNoteForm -> save_case_note() (encrypt + upsert UNIQUE)
    - If ENCRYPTION_KEY missing or invalid -> surfaces "Encryption failed" without 500 error
    """
    counselor = request.user.profile

    try:
        appointment = Appointment.objects.select_related('student', 'student__user').get(id=appointment_id)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found.")

    if appointment.counselor_id != counselor.id:
        return HttpResponseForbidden("Not found or not yours: You are not assigned to this appointment.")

    existing_note = CaseNote.objects.filter(appointment=appointment, counselor=counselor).first()
    decrypted_content = ""

    if existing_note:
        try:
            note_data = get_decrypted_case_note(existing_note, counselor)
            if note_data:
                decrypted_content = note_data['content']
        except ValueError:
            messages.error(request, "Encryption failed: Unable to decrypt note with current key.")
        except Exception:
            messages.error(request, "Error retrieving case note.")

    if request.method == 'POST':
        form = CaseNoteForm(request.POST)
        if form.is_valid():
            content = form.cleaned_data['content']
            is_confidential = form.cleaned_data.get('is_confidential', False)
            try:
                save_case_note(
                    appointment=appointment,
                    counselor=counselor,
                    raw_content=content,
                    is_confidential=is_confidential
                )
                messages.success(request, "Case note saved securely.")
                return redirect('case_note', appointment_id=appointment.id)
            except ValueError:
                messages.error(request, "Encryption failed")
            except (ValidationError, PermissionDenied) as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))
            except Exception:
                messages.error(request, "Could not save case note.")
        else:
            messages.error(request, "Validation error. Note content cannot be empty.")
    else:
        initial = {}
        if existing_note:
            initial['content'] = decrypted_content
            initial['is_confidential'] = existing_note.is_confidential
        form = CaseNoteForm(initial=initial)

    context = {
        'appointment': appointment,
        'existing_note': existing_note,
        'form': form,
    }
    return render(request, 'counselor/case_note.html', context)
