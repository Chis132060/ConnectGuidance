"""
core/services/receptionist.py — Receptionist business logic for GuidanceConnect Django replica.

Handles student search, counselor roster retrieval, slot availability checks,
and 4-step walk-in appointment booking (FLOWS §16).
"""

import datetime
from typing import List, Optional, Dict, Any
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import Profile, Appointment
from core.choices import RoleChoices
from core.services.slots import (
    is_counselor_slot_free,
    get_available_slots_for_counselor,
    get_first_available_counselor_slot,
)
from core.services.appointments import book_appointment


def search_students(query: str, limit: int = 25) -> List[Profile]:
    """
    Search active students by full_name or student_id (case-insensitive).
    Limits result to at most `limit` records (default 25).
    """
    q_clean = (query or "").strip()
    if not q_clean:
        return []

    return list(
        Profile.objects.filter(
            role=RoleChoices.STUDENT,
            is_active=True
        ).filter(
            Q(full_name__icontains=q_clean) |
            Q(student_id__icontains=q_clean) |
            Q(user__email__icontains=q_clean)
        ).select_related('user').order_by('full_name')[:limit]
    )


def list_reception_counselors() -> List[Profile]:
    """
    Return all active counselors alphabetically by full_name.
    """
    return list(
        Profile.objects.filter(
            role=RoleChoices.COUNSELOR,
            is_active=True
        ).order_by('full_name')
    )


def book_receptionist_appointment(
    receptionist: Profile,
    student: Profile,
    scheduled_at: datetime.datetime,
    concern_type: str,
    counselor: Optional[Profile] = None,
    notes: Optional[str] = None
) -> Appointment:
    """
    FLOWS §16: Book an appointment from the receptionist desk.
    - If counselor is None: automatically selects earliest free counselor alphabetically at scheduled_at.
    - If specific counselor is provided: checks slot is free.
    - Enforces future datetime, active student, and active counselors exist.
    - Logs audit action: APPOINTMENT_CREATED_RECEPTION
    """
    now = timezone.now()
    if scheduled_at <= now:
        raise ValidationError("Appointment must be scheduled for a future date and time.")

    if not student.is_active or student.role != RoleChoices.STUDENT:
        raise ValidationError("Selected student is not active or not a student.")

    active_counselors = list_reception_counselors()
    if not active_counselors:
        raise ValidationError("No active counselors are currently available.")

    chosen_counselor = counselor

    if chosen_counselor is None:
        # Loop through active counselors alphabetically to find the first one free
        for c in active_counselors:
            if is_counselor_slot_free(c, scheduled_at):
                chosen_counselor = c
                break

        if chosen_counselor is None:
            raise ValidationError("No counselor is available at that time slot.")
    else:
        if not chosen_counselor.is_active or chosen_counselor.role != RoleChoices.COUNSELOR:
            raise ValidationError("Selected counselor is not active or invalid.")

        if not is_counselor_slot_free(chosen_counselor, scheduled_at):
            raise ValidationError("The selected counselor is not available at that time.")

    return book_appointment(
        student=student,
        counselor=chosen_counselor,
        scheduled_at=scheduled_at,
        concern_type=concern_type,
        notes=notes,
        created_by_receptionist=True,
        actor=receptionist
    )
