"""
core/views/admin_views.py — Administrator views for GuidanceConnect Django replica.

Implements FLOWS §17-21, §24:
- /admin-panel/ — Executive dashboard overview with KPIs & analytics
- /admin-panel/users/ — User management, role transitions, status toggling, and user creation
- /admin-panel/audit/ — Audit trail viewer and CSV export
- /admin-panel/reports/ — Appointment reports filter, live preview, PDF & CSV export
- /admin-panel/profile/ — Administrator profile and password modification
"""

import csv
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from core.guards import require_admin
from core.models import Profile, Appointment, AuditLog
from core.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
from core.services.metrics import get_admin_metrics
from core.services.reports import (
    filter_appointments,
    export_appointments_csv,
    export_appointments_pdf,
)
from core.services.admin_users import (
    update_user_role,
    update_user_status,
    create_user_by_admin,
)
from core.services.audit import log_action


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
    return render(request, 'admin/overview.html', context)


@require_admin
@require_http_methods(["GET", "POST"])
def admin_users_view(request):
    """
    INTERFACES #12 / FLOWS §17-18: User Management.
    Supports user search, role/status filtering, inline role modifications,
    account activation/deactivation, and manual staff account creation.
    """
    admin_profile = request.user.profile

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_user':
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '')
            full_name = request.POST.get('full_name', '').strip()
            role = request.POST.get('role', RoleChoices.STUDENT)
            student_id = request.POST.get('student_id', '').strip()
            department = request.POST.get('department', '').strip()

            try:
                create_user_by_admin(
                    actor=admin_profile,
                    email=email,
                    password=password,
                    full_name=full_name,
                    role=role,
                    student_id=student_id,
                    department=department
                )
                messages.success(request, f"User account for {full_name} ({email}) created successfully.")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))
            except Exception as e:
                messages.error(request, f"Error creating user: {e}")

        elif action == 'change_role':
            target_id = request.POST.get('target_id')
            new_role = request.POST.get('new_role')
            target = get_object_or_404(Profile, id=target_id)
            try:
                update_user_role(admin_profile, target, new_role)
                messages.success(request, f"Role for {target.full_name} updated to {new_role}.")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))

        elif action == 'toggle_status':
            target_id = request.POST.get('target_id')
            new_status_str = request.POST.get('new_is_active', 'false').lower()
            new_is_active = (new_status_str == 'true')
            target = get_object_or_404(Profile, id=target_id)
            try:
                update_user_status(admin_profile, target, new_is_active)
                status_text = "activated" if new_is_active else "deactivated"
                messages.success(request, f"User {target.full_name} has been {status_text}.")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))

        return redirect('admin_users')

    # GET Filter & Search
    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    profiles_qs = Profile.objects.select_related('user').all().order_by('-user_no', 'full_name')

    if q:
        profiles_qs = profiles_qs.filter(
            Q(full_name__icontains=q) |
            Q(student_id__icontains=q) |
            Q(user__email__icontains=q)
        )
    if role_filter:
        profiles_qs = profiles_qs.filter(role=role_filter)
    if status_filter == 'active':
        profiles_qs = profiles_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        profiles_qs = profiles_qs.filter(is_active=False)

    paginator = Paginator(profiles_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile': admin_profile,
        'page_obj': page_obj,
        'q': q,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': RoleChoices.choices,
    }
    return render(request, 'admin/users.html', context)


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
    return render(request, 'admin/audit_logs.html', context)


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
    return render(request, 'admin/reports.html', context)


@require_admin
@require_http_methods(["GET", "POST"])
def admin_profile_view(request):
    """
    INTERFACES #15: Admin profile and password modification.
    """
    admin_profile = request.user.profile

    if request.method == 'POST':
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect('admin_profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        password_form = PasswordChangeForm(user=request.user)

    context = {
        'profile': admin_profile,
        'user': request.user,
        'password_form': password_form,
    }
    return render(request, 'admin/profile.html', context)
