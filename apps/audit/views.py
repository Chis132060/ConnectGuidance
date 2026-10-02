"""
apps/audit/views.py — Audit log viewer and export
"""

import csv
import json
from django.shortcuts import render
from django.http import HttpResponse
from django.core.paginator import Paginator
from apps.authentication.guards import require_admin
from core.models import AuditLog
from .services.logging import log_action


@require_admin
def admin_audit_logs_view(request):
    """
    INTERFACES #13 / FLOWS §20: Audit Log Trail and CSV export.
    """
    admin_profile = request.user.profile

    action_filter = request.GET.get('action', '').strip()
    table_filter = request.GET.get('table', '').strip()
    export_csv = request.GET.get('export', '')

    audit_qs = AuditLog.objects.select_related('user', 'user__user').all().order_by('-created_at')

    if action_filter:
        audit_qs = audit_qs.filter(action__icontains=action_filter)
    if table_filter:
        audit_qs = audit_qs.filter(table_name__icontains=table_filter)

    # Handle CSV Export
    if export_csv == 'true':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Timestamp', 'User', 'Action', 'Table', 'Record ID', 'Metadata'])
        for row in audit_qs[:500]:
            user_name = row.user.full_name if row.user else 'System'
            writer.writerow([
                row.id,
                row.created_at.isoformat(),
                user_name,
                row.action,
                row.table_name,
                row.record_id or '',
                json.dumps(row.metadata)
            ])
        log_action(admin_profile, "AUDIT_LOG_EXPORT_CSV", "core_audit_log")
        return response

    paginator = Paginator(audit_qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'profile': admin_profile,
        'page_obj': page_obj,
        'action_filter': action_filter,
        'table_filter': table_filter,
    }
    return render(request, 'audit/logs.html', context)
