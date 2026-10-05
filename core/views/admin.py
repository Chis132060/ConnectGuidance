"""
core/views/admin.py — Administrator Portal for ConnectGuidance.

Standardized Admin Views:
1. admin_overview_view      → /admin-panel/ (Executive KPIs, weekly trends, concern breakdown, audit)
2. admin_reports_view       → /admin-panel/reports/ (Reports, CSV & PDF export)
3. admin_users_view         → /admin-panel/users/ (User management, roles, activation)
4. admin_audit_logs_view    → /admin-panel/audit/ (Compliance audit logs, CSV export)
5. admin_appointments_view  → /admin-panel/appointments/ (System-wide appointments)
6. admin_profile_view       → /admin-panel/profile/ (Admin profile & credentials)
"""

import io
import csv
import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count, Q, Max
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.decorators import require_admin
from accounts.models import Profile
from accounts.choices import RoleChoices
from core.models import Appointment, CaseNote, AuditLog
from core.choices import AppointmentStatusChoices, ConcernTypeChoices
from core.services.metrics import get_admin_metrics
from core.services.reports import filter_appointments, export_appointments_csv, export_appointments_pdf
from core.services.audit import log_action
from core.services.management import (
    can_change_role,
    update_user_role,
    can_change_active_status,
    update_user_status,
    create_user_by_admin,
)


# 1. Executive Dashboard / Overview
@require_admin
def admin_overview_view(request):
    """System Executive Overview: KPIs, appointment volume, and recent audit activity."""
    admin_profile = request.user.profile
    metrics = get_admin_metrics()
    recent_activity = AuditLog.objects.select_related('user').order_by('-created_at')[:10]

    context = {
        'profile': admin_profile,
        'kpis': {
            'total_students': metrics['total_students'],
            'total_counselors': metrics['total_counselors'],
            'monthly_appointments': metrics['monthly_appointments'],
            'completion_rate': metrics['completion_rate'],
        },
        'status_counts': {
            'pending': metrics['pending_count'],
            'confirmed': metrics['confirmed_count'],
            'completed': metrics['completed_count'],
            'cancelled': metrics['cancelled_count'],
        },
        'weekly_series_json': json.dumps(metrics['weekly_series']),
        'concern_breakdown_json': json.dumps(metrics['concern_breakdown']),
        'recent_activity': recent_activity,
    }
    return render(request, 'analytics/overview.html', context)


# 2. Reports & Data Export
@require_admin
def admin_reports_view(request):
    """Appointment reports generator with CSV and ReportLab PDF export."""
    admin_profile = request.user.profile

    start_date = request.GET.get('date_from', '').strip()
    end_date = request.GET.get('date_to', '').strip()
    department = request.GET.get('department', '').strip()
    concern_type = request.GET.get('concern_type', '').strip()
    status = request.GET.get('status', '').strip()
    counselor_id = request.GET.get('counselor_id', '').strip()

    has_filters = bool(start_date or end_date or department or concern_type or status or counselor_id or request.GET.get('generate'))

    if has_filters:
        appointments = filter_appointments(
            start_date=start_date,
            end_date=end_date,
            department=department,
            concern_type=concern_type,
            status=status,
            counselor_id=int(counselor_id) if counselor_id.isdigit() else None
        )
    else:
        appointments = Appointment.objects.select_related('student', 'counselor').all().order_by('-scheduled_at')

    # Handle Exports
    export_format = request.GET.get('export', '').strip().lower()
    if export_format == 'csv':
        return export_appointments_csv(appointments, exported_by=admin_profile)
    elif export_format == 'pdf':
        return export_appointments_pdf(appointments, exported_by=admin_profile)

    paginator = Paginator(appointments, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).order_by('full_name')

    summary = {
        'total': appointments.count(),
        'pending': appointments.filter(status=AppointmentStatusChoices.PENDING).count(),
        'confirmed': appointments.filter(status=AppointmentStatusChoices.CONFIRMED).count(),
        'completed': appointments.filter(status=AppointmentStatusChoices.COMPLETED).count(),
        'cancelled': appointments.filter(status=AppointmentStatusChoices.CANCELLED).count(),
    }

    context = {
        'profile': admin_profile,
        'appointments': page_obj,
        'page_obj': page_obj,
        'summary': summary,
        'counselors': counselors,
        'concern_choices': ConcernTypeChoices.choices,
        'status_choices': AppointmentStatusChoices.choices,
        'filters': {
            'date_from': start_date,
            'date_to': end_date,
            'department': department,
            'concern_type': concern_type,
            'status': status,
            'counselor_id': counselor_id,
        },
    }
    return render(request, 'analytics/reports.html', context)


# 3. User Management
@require_admin
@require_http_methods(["GET", "POST"])
def admin_users_view(request):
    """User Management: directory, role assignments, activation, manual creation."""
    admin_profile = request.user.profile

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_user':
            email = request.POST.get('email', '').strip().lower()
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
                    student_id=student_id or None,
                    department=department or None
                )
                messages.success(request, f"User account for {full_name} ({email}) created successfully.")
            except Exception as e:
                messages.error(request, str(e))

        elif action == 'change_role':
            target_id = request.POST.get('target_id')
            new_role = request.POST.get('new_role')
            target = get_object_or_404(Profile, id=target_id)
            try:
                update_user_role(admin_profile, target, new_role)
                messages.success(request, f"Role for {target.full_name} updated to {new_role}.")
            except Exception as e:
                messages.error(request, str(e))

        elif action == 'toggle_status':
            target_id = request.POST.get('target_id')
            new_status_str = request.POST.get('new_is_active', 'false').lower()
            new_is_active = (new_status_str == 'true')
            target = get_object_or_404(Profile, id=target_id)
            try:
                update_user_status(admin_profile, target, new_is_active)
                st = "activated" if new_is_active else "deactivated"
                messages.success(request, f"User {target.full_name} has been {st}.")
            except Exception as e:
                messages.error(request, str(e))

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

    paginator = Paginator(profiles_qs, 25)
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
    return render(request, 'users/users.html', context)


# 4. System Audit Logs
@require_admin
def admin_audit_logs_view(request):
    """System Audit Trail: immutable activity logs with filtering and CSV export."""
    admin_profile = request.user.profile

    action_filter = request.GET.get('action', '').strip()
    table_filter = request.GET.get('table', '').strip()
    user_search = request.GET.get('user', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    logs_qs = AuditLog.objects.select_related('user').all().order_by('-created_at')

    if action_filter:
        logs_qs = logs_qs.filter(action=action_filter)
    if table_filter:
        logs_qs = logs_qs.filter(table_name=table_filter)
    if user_search:
        logs_qs = logs_qs.filter(
            Q(user__full_name__icontains=user_search) |
            Q(user__user__email__icontains=user_search)
        )
    if date_from:
        d = parse_date(date_from)
        if d:
            logs_qs = logs_qs.filter(created_at__date__gte=d)
    if date_to:
        d = parse_date(date_to)
        if d:
            logs_qs = logs_qs.filter(created_at__date__lte=d)

    # CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        response['Content-Disposition'] = f'attachment; filename="audit_logs_{timestamp}.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Timestamp", "User", "Role", "Action", "Table Name", "Record ID", "Metadata"])

        for l in logs_qs[:5000]:
            user_str = l.user.full_name if l.user else "System / Anonymous"
            role_str = l.user.role if l.user else "—"
            writer.writerow([
                l.id,
                l.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                user_str,
                role_str,
                l.action,
                l.table_name,
                str(l.record_id or ''),
                json.dumps(l.metadata or {})
            ])
        return response

    paginator = Paginator(logs_qs, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    actions = AuditLog.objects.values_list('action', flat=True).distinct()
    tables = AuditLog.objects.values_list('table_name', flat=True).distinct()

    context = {
        'profile': admin_profile,
        'page_obj': page_obj,
        'action_filter': action_filter,
        'table_filter': table_filter,
        'user_search': user_search,
        'date_from': date_from,
        'date_to': date_to,
        'actions': actions,
        'tables': tables,
    }
    return render(request, 'audit/logs.html', context)


# 5. All-Appointments Registry
@require_admin
def admin_appointments_view(request):
    """Full system-wide appointment registry with search and status tabs."""
    admin_profile = request.user.profile

    status_filter = request.GET.get('status', 'all').strip().lower()
    search_query = request.GET.get('q', '').strip()
    counselor_id = request.GET.get('counselor_id', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    appointments = Appointment.objects.select_related(
        'student', 'counselor', 'student__user', 'counselor__user'
    ).order_by('-scheduled_at')

    if status_filter and status_filter != 'all':
        appointments = appointments.filter(status=status_filter)

    if search_query:
        appointments = appointments.filter(
            Q(student__full_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query) |
            Q(counselor__full_name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    if counselor_id and counselor_id.isdigit():
        appointments = appointments.filter(counselor_id=int(counselor_id))

    if date_from:
        d = parse_date(date_from)
        if d:
            appointments = appointments.filter(scheduled_at__date__gte=d)

    if date_to:
        d = parse_date(date_to)
        if d:
            appointments = appointments.filter(scheduled_at__date__lte=d)

    all_appointments = Appointment.objects.all()
    counts = {
        'all': all_appointments.count(),
        'pending': all_appointments.filter(status=AppointmentStatusChoices.PENDING).count(),
        'confirmed': all_appointments.filter(status=AppointmentStatusChoices.CONFIRMED).count(),
        'completed': all_appointments.filter(status=AppointmentStatusChoices.COMPLETED).count(),
        'cancelled': all_appointments.filter(status=AppointmentStatusChoices.CANCELLED).count(),
    }

    counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).order_by('full_name')

    context = {
        'profile': admin_profile,
        'appointments': appointments[:200],
        'counts': counts,
        'active_filter': status_filter,
        'search_query': search_query,
        'counselors': counselors,
        'selected_counselor_id': counselor_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'admin/appointments.html', context)


# 6. Admin Profile & Security
@require_admin
@require_http_methods(["GET", "POST"])
def admin_profile_view(request):
    """Administrator credentials and security settings."""
    admin_profile = request.user.profile

    if request.method == 'POST':
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, "Your administrator password has been updated.")
            return redirect('admin_profile')
        else:
            messages.error(request, "Please correct the password errors below.")
    else:
        password_form = PasswordChangeForm(user=request.user)

    total_users = Profile.objects.count()
    active_students = Profile.objects.filter(role=RoleChoices.STUDENT, is_active=True).count()
    active_counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).count()

    context = {
        'profile': admin_profile,
        'user': request.user,
        'password_form': password_form,
        'stats': {
            'total_users': total_users,
            'active_students': active_students,
            'active_counselors': active_counselors,
        }
    }
    return render(request, 'users/profile.html', context)
