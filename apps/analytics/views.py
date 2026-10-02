"""
apps/analytics/views.py — Analytics and reporting views for GuidanceConnect.

Implements FLOWS §20-21, §24:
- /admin-panel/ — Executive dashboard overview with KPIs & analytics
- /admin-panel/reports/ — Appointment reports filter, live preview, PDF & CSV export
"""

import json
from django.shortcuts import render
from django.http import HttpResponse

from apps.authentication.guards import require_admin
from core.models import Profile, AuditLog
from apps.common.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
from apps.analytics.services.metrics import get_admin_metrics
from apps.analytics.services.reports import (
    filter_appointments,
    export_appointments_csv,
    export_appointments_pdf,
)


@require_admin
def admin_overview_view(request):
    """
    INTERFACES #11 / FLOWS §24: Admin Executive Overview.
    Displays 4 KPI cards, 8-week appointment series, concern distribution, and recent audit activity.
    """
    metrics = get_admin_metrics()
    recent_activity = AuditLog.objects.select_related('user', 'user__user').order_by('-created_at')[:10]

    context = {
        'profile': request.user.profile,
        'metrics': metrics,
        'recent_activity': recent_activity,
        'kpis': {
            'total_students': metrics.get('total_students', 0),
            'total_counselors': metrics.get('total_counselors', 0),
            'monthly_appointments': metrics.get('monthly_appointments', 0),
            'completion_rate': metrics.get('completion_rate', 0),
        },
        'weekly_labels': json.dumps([w['label'] for w in metrics.get('weekly_series', [])]),
        'weekly_data': json.dumps([w['count'] for w in metrics.get('weekly_series', [])]),
        'concern_labels': json.dumps([c['label'] for c in metrics.get('concern_breakdown', [])]),
        'concern_data': json.dumps([c['count'] for c in metrics.get('concern_breakdown', [])]),
    }
    return render(request, 'analytics/overview.html', context)


@require_admin
def admin_reports_view(request):
    """
    INTERFACES #14 / FLOWS §21: Appointment Reports & Data Exports (PDF & CSV).
    """
    admin_profile = request.user.profile

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    department = request.GET.get('department')
    concern_type = request.GET.get('concern_type')
    status = request.GET.get('status')
    counselor_id = request.GET.get('counselor_id')
    export_format = request.GET.get('export')

    filtered_appts = filter_appointments(
        start_date=start_date,
        end_date=end_date,
        department=department,
        concern_type=concern_type,
        status=status,
        counselor_id=int(counselor_id) if counselor_id and counselor_id.isdigit() else None
    )

    if export_format == 'csv':
        return export_appointments_csv(filtered_appts, exported_by=admin_profile)
    elif export_format == 'pdf':
        return export_appointments_pdf(filtered_appts, exported_by=admin_profile)

    preview_appts = filtered_appts[:50]
    counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).order_by('full_name')

    context = {
        'profile': admin_profile,
        'counselors': counselors,
        'concern_choices': ConcernTypeChoices.choices,
        'status_choices': AppointmentStatusChoices.choices,
        'total_count': filtered_appts.count(),
        'preview_appts': preview_appts,
        'filters': {
            'start_date': start_date or '',
            'end_date': end_date or '',
            'department': department or '',
            'concern_type': concern_type or '',
            'status': status or '',
            'counselor_id': counselor_id or '',
        }
    }
    return render(request, 'analytics/reports.html', context)
