"""
core/services/metrics.py — Executive KPIs and analytics for GuidanceConnect.
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

    # 5. 8-week appointment series with Monday start
    today = now.date()
    current_monday = today - datetime.timedelta(days=today.weekday())
    weekly_series: List[Dict[str, Any]] = []

    for i in range(7, -1, -1):
        week_start_date = current_monday - datetime.timedelta(weeks=i)
        week_end_date = week_start_date + datetime.timedelta(days=7)
        
        start_dt = timezone.make_aware(datetime.datetime.combine(week_start_date, datetime.time.min))
        end_dt = timezone.make_aware(datetime.datetime.combine(week_end_date, datetime.time.min))
        
        count = Appointment.objects.filter(
            scheduled_at__gte=start_dt,
            scheduled_at__lt=end_dt
        ).count()
        
        label = week_start_date.strftime("%b %d")
        weekly_series.append({
            'label': label,
            'count': count
        })

    # 6. Concern breakdown: top 8 + Other
    concern_counts = (
        Appointment.objects.values('concern_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    concern_breakdown: List[Dict[str, Any]] = []
    top_concerns = list(concern_counts[:8])
    other_concerns = list(concern_counts[8:])

    for item in top_concerns:
        ctype = item['concern_type']
        label = dict(ConcernTypeChoices.choices).get(ctype, ctype.replace('_', ' ').title())
        concern_breakdown.append({
            'label': label,
            'count': item['count']
        })

    if other_concerns:
        other_total = sum(item['count'] for item in other_concerns)
        concern_breakdown.append({
            'label': 'Other',
            'count': other_total
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
        'concern_breakdown': concern_breakdown,
    }
