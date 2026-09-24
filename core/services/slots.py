import datetime
from typing import List, Dict, Any, Optional
from django.utils import timezone
from core.models import Appointment, Profile
from core.choices import RoleChoices, AppointmentStatusChoices

HOURLY_START = 9
HOURLY_END = 16  # 16:00 is the last slot of the day


def get_hourly_slots_for_date(date: datetime.date) -> List[datetime.datetime]:
    """Generate localized datetime objects for 09:00 through 16:00 on the given date."""
    current_tz = timezone.get_current_timezone()
    slots = []
    for hour in range(HOURLY_START, HOURLY_END + 1):
        dt = datetime.datetime(date.year, date.month, date.day, hour, 0, 0)
        aware_dt = timezone.make_aware(dt, current_tz)
        slots.append(aware_dt)
    return slots


def get_available_slots_for_counselor(counselor: Profile, target_date: datetime.date) -> List[Dict[str, Any]]:
    """
    Returns all 09:00-16:00 slots for the counselor on target_date,
    annotated with whether each slot is currently free.
    """
    all_slots = get_hourly_slots_for_date(target_date)
    now = timezone.now()

    # Query busy slots for this counselor on target date (pending or confirmed)
    day_start = timezone.make_aware(
        datetime.datetime.combine(target_date, datetime.time.min),
        timezone.get_current_timezone()
    )
    day_end = timezone.make_aware(
        datetime.datetime.combine(target_date, datetime.time.max),
        timezone.get_current_timezone()
    )

    busy_appts = Appointment.objects.filter(
        counselor=counselor,
        scheduled_at__range=(day_start, day_end),
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED]
    ).values_list('scheduled_at', flat=True)

    busy_times = {dt.replace(second=0, microsecond=0) for dt in busy_appts}

    result = []
    for slot in all_slots:
        is_future = slot > now
        is_taken = slot.replace(second=0, microsecond=0) in busy_times
        is_available = is_future and not is_taken

        result.append({
            'datetime': slot,
            'iso': slot.isoformat(),
            'formatted_time': slot.strftime('%I:%M %p'),
            'formatted_date': slot.strftime('%b %d, %Y'),
            'is_available': is_available,
            'is_future': is_future,
            'is_taken': is_taken
        })
    return result


def is_counselor_slot_free(
    counselor: Profile,
    scheduled_at: datetime.datetime,
    exclude_appointment_id: Optional[int] = None
) -> bool:
    """
    Verify that the slot is in the future, falls between 09:00-16:00,
    and has no overlapping pending/confirmed appointments.
    """
    now = timezone.now()
    if scheduled_at <= now:
        return False

    # Check 1-hour conflict window (+/- 50 minutes to prevent overlaps)
    window_start = scheduled_at - datetime.timedelta(minutes=50)
    window_end = scheduled_at + datetime.timedelta(minutes=50)

    conflict_query = Appointment.objects.filter(
        counselor=counselor,
        scheduled_at__gt=window_start,
        scheduled_at__lt=window_end,
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED]
    )

    if exclude_appointment_id:
        conflict_query = conflict_query.exclude(id=exclude_appointment_id)

    return not conflict_query.exists()


def get_first_available_counselor_slot(
    target_date: datetime.date,
    exclude_student_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Used by receptionist next-available algorithm:
    Iterates through active counselors alphabetically by full_name,
    finding the earliest available slot.
    """
    counselors = Profile.objects.filter(
        role=RoleChoices.COUNSELOR,
        is_active=True
    ).order_by('full_name')

    slots_to_check = get_hourly_slots_for_date(target_date)
    now = timezone.now()

    for slot in slots_to_check:
        if slot <= now:
            continue
        for counselor in counselors:
            if is_counselor_slot_free(counselor, slot):
                return {
                    'counselor': counselor,
                    'slot': slot,
                    'formatted_time': slot.strftime('%I:%M %p'),
                    'formatted_date': slot.strftime('%b %d, %Y')
                }
    return None
