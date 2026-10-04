"""
Admin Metrics and Analytics Service.
Calculates KPI counts (total students, counselors, monthly sessions, completion rate),
weekly trend data, and concern type distributions.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from core.models import Profile, Appointment, AuditLog
from core.choices import AppointmentStatusChoices, RoleChoices, ConcernTypeChoices


def get_kpis():
    """Return KPI card data."""
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_students = Profile.objects.filter(role=RoleChoices.STUDENT).count()
    total_counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR).count()

    monthly_appointments = Appointment.objects.filter(
        created_at__gte=month_start
    ).count()

    total_appts = Appointment.objects.count()
    completed_appts = Appointment.objects.filter(status=AppointmentStatusChoices.COMPLETED).count()
    confirmed_appts = Appointment.objects.filter(status=AppointmentStatusChoices.CONFIRMED).count()
    completion_rate = round((completed_appts / total_appts * 100) if total_appts > 0 else 0, 1)

    return {
        "total_students": total_students,
        "total_counselors": total_counselors,
        "monthly_appointments": monthly_appointments,
        "completion_rate": completion_rate,
        "total_appointments": total_appts,
        "completed_count": completed_appts,
        "confirmed_count": confirmed_appts,
        "completed_appointments": completed_appts,
    }


def get_weekly_series(weeks=8):
    """
    Return 8-week series data (Monday-start).
    Each entry: {"week_label": "Oct 1", "count": N}
    """
    now = timezone.now()
    current_monday = now - timedelta(days=now.weekday())
    current_monday = current_monday.replace(hour=0, minute=0, second=0, microsecond=0)

    series = []
    for i in range(weeks - 1, -1, -1):
        week_start = current_monday - timedelta(weeks=i)
        week_end = week_start + timedelta(weeks=1)

        count = Appointment.objects.filter(
            created_at__gte=week_start,
            created_at__lt=week_end,
        ).count()

        series.append({
            "week_label": week_start.strftime("%b %d"),
            "count": count,
        })

    return series


def get_concern_breakdown():
    """
    Return top concern types with counts, max 8 + "Other" bucket.
    """
    breakdown = (
        Appointment.objects.values("concern_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    choices_dict = dict(ConcernTypeChoices.choices)

    result = []
    other_count = 0
    for i, item in enumerate(breakdown):
        label = choices_dict.get(item["concern_type"], item["concern_type"])
        if i < 8:
            result.append({
                "label": label,
                "value": item["concern_type"],
                "count": item["count"],
            })
        else:
            other_count += item["count"]

    if other_count > 0:
        result.append({"label": "Other", "value": "other_bucket", "count": other_count})

    return result


def get_admin_metrics():
    """Combined dashboard metrics calculation."""
    kpis = get_kpis()
    kpis["weekly_series"] = get_weekly_series(weeks=8)
    kpis["concern_breakdown"] = get_concern_breakdown()
    return kpis


def get_recent_activity(limit=10):
    """Return recent audit log entries."""
    return AuditLog.objects.select_related("user").order_by("-created_at")[:limit]
