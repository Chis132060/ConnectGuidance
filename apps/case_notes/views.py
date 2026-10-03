"""
apps/case_notes/views.py — Case Notes views for GuidanceConnect.

Implements FLOWS §11 & §12:
- Case note editor (/case-notes/<int:appointment_id>/) with AES-256 encryption and confidentiality controls
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, Http404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError, PermissionDenied

from apps.authentication.guards import require_counselor
from core.models import Appointment, CaseNote
from apps.case_notes.forms import CaseNoteForm
from apps.case_notes.services.case_notes import save_case_note, get_decrypted_case_note


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
    return render(request, 'case_notes/editor.html', context)
