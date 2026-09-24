"""
core/services/metrics.py — Executive KPIs and analytics for GuidanceConnect.

Port of Next.js lib/admin-metrics.ts (FLOWS §19, PLAN step 69).
Computes:
- Total students, counselors, monthly appointments, completion rate
- Status distribution (pending, confirmed, completed, cancelled)
- 8-week appointment series with Monday start
- Top-8 concern breakdown + 'Other'
"""

import datetime
from typing import Dict, Any, List
from django.utils import timezone
from django.db.models import Count, Q

from core.models import Appointment, Profile
from core.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices


def get_admin_metrics() -> Dict[str, Any]:
    """
    Computes comprehensive executive KPI summary and historical analytics.
    Returns:
        dict: {
            'total_students': int,
            'total_counselors': int,
            'total_appointments': int,
            'monthly_appointments': int,
            'completion_rate': float,
            'pending_count': int,
            'confirmed_count': int,
            'completed_count': int,
            'cancelled_count': int,
            'weekly_series': list of {'label': str, 'count': int},
            'concern_breakdown': list of {'label': str, 'count': int},
        }
    """
    now = timezone.now()
    
    # 1. Total active students and counselors
    total_students = Profile.objects.filter(role=RoleChoices.STUDENT, is_active=True).count()
    total_counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).count()

    # 2. Total appointments & status distribution
    total_appointments = Appointment.objects.count()
    status_counts = Appointment.objects.values('status').annotate(total=Count('id'))
    status_map = {item['status']: item['total'] for item in status_counts}
    
    pending_count = status_map.get(AppointmentStatusChoices.PENDING, 0)
    confirmed_count = status_map.get(AppointmentStatusChoices.CONFIRMED, 0)
    completed_count = status_map.get(AppointmentStatusChoices.COMPLETED, 0)
    cancelled_count = status_map.get(AppointmentStatusChoices.CANCELLED, 0)

    # 3. Monthly appointments (current month)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_appointments = Appointment.objects.filter(scheduled_at__gte=first_of_month).count()

    # 4. Completion rate
    if total_appointments > 0:
        completion_rate = round((completed_count / total_appointments) * 100, 1)
    else:
        completion_rate = 0.0

    # 5. 8-week series (Monday start)
    # Determine the Monday of the current week
    current_weekday = now.weekday()  # Monday = 0, Sunday = 6
    current_week_monday = (now - datetime.timedelta(days=current_weekday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    weekly_series: List[Dict[str, Any]] = []
    for i in range(7, -1, -1):
        week_start = current_week_monday - datetime.timedelta(weeks=i)
        week_end = week_start + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
        count = Appointment.objects.filter(
            scheduled_at__gte=week_start,
            scheduled_at__lte=week_end
        ).count()
        label = week_start.strftime("%b %d")
        weekly_series.append({
            'label': label,
            'count': count
        })

    # 6. Concern breakdown: top 8 + other
    concern_choices_dict = dict(ConcernTypeChoices.choices)
    raw_concerns = (
        Appointment.objects.values('concern_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    top_concerns = []
    other_count = 0
    for idx, item in enumerate(raw_concerns):
        ctype = item['concern_type']
        count = item['count']
        display_label = concern_choices_dict.get(ctype, ctype or 'Unspecified')
        if idx < 8:
            top_concerns.append({
                'label': display_label,
                'count': count
            })
        else:
            other_count += count

    if other_count > 0:
        top_concerns.append({
            'label': 'Other Concerns',
            'count': other_count
        })

    return {
        'total_students': total_students,
        'total_counselors': total_counselors,
        'total_appointments': total_appointments,
        'monthly_appointments': monthly_appointments,
        'completion_rate': completion_rate,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'weekly_series': weekly_series,
        'concern_breakdown': top_concerns,
    }
