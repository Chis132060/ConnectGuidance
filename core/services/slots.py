"""
Counseling Appointment Slot Generator.
Calculates hourly availability (09:00 - 16:00),
filtering out already booked (pending or confirmed) appointments.
"""
import datetime
from django.utils import timezone
from core.models import Appointment, Profile
from core.choices import AppointmentStatusChoices, RoleChoices


SLOT_START_HOUR = 9
SLOT_END_HOUR = 16   # 09:00 to 16:00 inclusive (8 hourly slots: 9, 10, 11, 12, 13, 14, 15, 16)


def get_hourly_slots_for_date(date_obj):
    """
    Generate all 8 hourly slots (09:00 to 16:00) for a given date.
    Returns list of aware datetime objects.
    """
    tz = timezone.get_current_timezone()
    slots = []
    for hour in range(SLOT_START_HOUR, SLOT_END_HOUR + 1):
        slot_dt = timezone.make_aware(
            datetime.datetime.combine(date_obj, datetime.time(hour, 0)),
            tz,
        )
        slots.append(slot_dt)
    return slots


generate_day_slots = get_hourly_slots_for_date


def is_counselor_slot_free(counselor_or_id, scheduled_at):
    """
    Check if a counselor has an opening at scheduled_at.
    Returns False if scheduled_at is in the past, or if there is any pending/confirmed
    appointment within a 50-minute conflict window.
    """
    if scheduled_at < timezone.now():
        return False

    counselor_id = getattr(counselor_or_id, "id", counselor_or_id)

    # 50-minute clash window before and after
    start_window = scheduled_at - datetime.timedelta(minutes=50)
    end_window = scheduled_at + datetime.timedelta(minutes=50)

    has_conflict = Appointment.objects.filter(
        counselor_id=counselor_id,
        scheduled_at__gt=start_window,
        scheduled_at__lt=end_window,
        status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED],
    ).exists()

    return not has_conflict


def has_clash(counselor_id, scheduled_at):
    """Return True if there is a conflict at scheduled_at."""
    return not is_counselor_slot_free(counselor_id, scheduled_at)


def get_booked_slots(counselor_id, date_obj):
    """Get set of datetime objects already booked on given date."""
    tz = timezone.get_current_timezone()
    day_start = timezone.make_aware(
        datetime.datetime.combine(date_obj, datetime.time(0, 0)),
        tz,
    )
    day_end = day_start + datetime.timedelta(days=1)

    return set(
        Appointment.objects.filter(
            counselor_id=getattr(counselor_id, "id", counselor_id),
            scheduled_at__gte=day_start,
            scheduled_at__lt=day_end,
            status__in=[AppointmentStatusChoices.PENDING, AppointmentStatusChoices.CONFIRMED],
        ).values_list("scheduled_at", flat=True)
    )


def get_available_slots_for_counselor(counselor_or_id, date_obj):
    """
    Return list of dicts: [{'datetime': dt, 'is_available': bool}, ...]
    for all hourly slots of date_obj.
    """
    counselor_id = getattr(counselor_or_id, "id", counselor_or_id)
    all_slots = get_hourly_slots_for_date(date_obj)

    results = []
    for slot_dt in all_slots:
        free = is_counselor_slot_free(counselor_id, slot_dt)
        results.append({
            "datetime": slot_dt,
            "is_available": free,
        })
    return results


def get_available_slots(counselor_id, date_obj):
    """
    Return list of available datetime slots (where slot is free).
    Used by booking views and forms.
    """
    slot_dicts = get_available_slots_for_counselor(counselor_id, date_obj)
    return [s["datetime"] for s in slot_dicts if s["is_available"]]


def get_first_available_counselor_slot(date_obj):
    """
    Find the earliest free slot on date_obj, picking counselors alphabetically.
    Returns {'counselor': Profile, 'slot': datetime} or None.
    """
    counselors = list(
        Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).order_by("full_name", "user__username")
    )
    if not counselors:
        return None

    all_slots = get_hourly_slots_for_date(date_obj)
    for slot in all_slots:
        for counselor in counselors:
            if is_counselor_slot_free(counselor, slot):
                return {
                    "counselor": counselor,
                    "slot": slot,
                }
    return None


find_first_available_slot = get_first_available_counselor_slot
