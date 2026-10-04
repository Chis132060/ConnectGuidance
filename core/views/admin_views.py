"""
Admin views — overview dashboard, user management, audit logs, and analytics reports.
Handles administration, RBAC maintenance, system logs inspection, and data export.
"""
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from core.guards import role_required
from core.models import Profile, AuditLog
from core.choices import ROLE_CHOICES, STATUS_CHOICES, CONCERN_CHOICES
from core.services.metrics import get_kpis, get_weekly_series, get_concern_breakdown, get_recent_activity
from core.services.admin_users import create_user, change_role, toggle_active
from core.services.reports import generate_report, export_csv, export_pdf
from core.services.audit import log_action
import json


@role_required("admin")
def overview_view(request):
    """Admin dashboard — KPIs + charts."""
    kpis = get_kpis()
    weekly_series = get_weekly_series()
    concern_breakdown = get_concern_breakdown()
    recent_activity = get_recent_activity()

    return render(request, "admin_panel/overview.html", {
        "profile": request.profile,
        "kpis": kpis,
        "weekly_series_json": json.dumps(weekly_series),
        "concern_breakdown_json": json.dumps(concern_breakdown),
        "recent_activity": recent_activity,
    })


@role_required("admin")
def users_view(request):
    """User management — list, create, role change, toggle active."""
    profile = request.profile

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_user":
            full_name = request.POST.get("full_name", "").strip()
            email = request.POST.get("email", "").strip()
            password = request.POST.get("password", "")
            role = request.POST.get("role", "student")
            student_id = request.POST.get("student_id", "").strip() or None
            department = request.POST.get("department", "").strip() or None

            new_profile, error = create_user(full_name, email, password, role, student_id, department)
            if error:
                messages.error(request, error)
            else:
                messages.success(request, f"User {full_name} created as {role}.")

        elif action == "change_role":
            target_id = request.POST.get("target_id")
            new_role = request.POST.get("new_role")
            success, error = change_role(profile, target_id, new_role)
            if error:
                messages.error(request, error)
            else:
                messages.success(request, "Role updated.")

        elif action == "toggle_active":
            target_id = request.POST.get("target_id")
            new_status, error = toggle_active(profile, target_id)
            if error:
                messages.error(request, error)
            else:
                status_str = "activated" if new_status else "deactivated"
                messages.success(request, f"User {status_str}.")

        return redirect("/admin-panel/users/")

    # GET — list users
    search = request.GET.get("search", "")
    role_filter = request.GET.get("role", "")
    status_filter = request.GET.get("status", "")

    users_qs = Profile.objects.select_related("user").order_by("-created_at")
    if search:
        from django.db.models import Q
        users_qs = users_qs.filter(
            Q(full_name__icontains=search) |
            Q(student_id__icontains=search) |
            Q(user__email__icontains=search)
        )
    if role_filter:
        users_qs = users_qs.filter(role=role_filter)
    if status_filter:
        is_active = status_filter == "active"
        users_qs = users_qs.filter(is_active=is_active)

    paginator = Paginator(users_qs, 20)
    page = request.GET.get("page", 1)
    users_page = paginator.get_page(page)

    return render(request, "admin_panel/users.html", {
        "profile": profile,
        "users_page": users_page,
        "roles": ROLE_CHOICES,
        "search": search,
        "role_filter": role_filter,
        "status_filter": status_filter,
    })


@role_required("admin")
def audit_logs_view(request):
    """Audit log viewer with filters and pagination."""
    qs = AuditLog.objects.select_related("user").order_by("-created_at")

    # Filters
    user_filter = request.GET.get("user", "")
    action_filter = request.GET.get("action", "")
    table_filter = request.GET.get("table", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if user_filter:
        qs = qs.filter(user__full_name__icontains=user_filter)
    if action_filter:
        qs = qs.filter(action__icontains=action_filter)
    if table_filter:
        qs = qs.filter(table_name__icontains=table_filter)
    if date_from:
        try:
            qs = qs.filter(created_at__gte=datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(created_at__lte=datetime.strptime(date_to, "%Y-%m-%d"))
        except ValueError:
            pass

    # CSV export
    if request.GET.get("export") == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "User", "Action", "Table", "Record ID", "Metadata"])
        for log in qs[:1000]:
            writer.writerow([
                log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                log.user.full_name if log.user else "System",
                log.action,
                log.table_name,
                str(log.record_id) if log.record_id else "",
                json.dumps(log.metadata),
            ])
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=audit_logs.csv"
        return response

    paginator = Paginator(qs, 25)
    page = request.GET.get("page", 1)
    logs_page = paginator.get_page(page)

    return render(request, "admin_panel/audit_logs.html", {
        "profile": request.profile,
        "logs_page": logs_page,
        "user_filter": user_filter,
        "action_filter": action_filter,
        "table_filter": table_filter,
        "date_from": date_from,
        "date_to": date_to,
    })


@role_required("admin")
def reports_view(request):
    """Reports — filters, preview, CSV/PDF export."""
    profile = request.profile
    appointments = None
    summary = None

    filters = {
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
        "department": request.GET.get("department", ""),
        "concern_type": request.GET.get("concern_type", ""),
        "status": request.GET.get("status", ""),
        "counselor_id": request.GET.get("counselor_id", ""),
    }

    # Parse date strings
    parsed_filters = {}
    for k, v in filters.items():
        if v and k in ("date_from", "date_to"):
            try:
                parsed_filters[k] = datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                pass
        elif v:
            parsed_filters[k] = v

    if request.GET.get("generate"):
        appointments = generate_report(parsed_filters, profile)
        summary = {
            "total": appointments.count(),
            "pending": appointments.filter(status="pending").count(),
            "confirmed": appointments.filter(status="confirmed").count(),
            "completed": appointments.filter(status="completed").count(),
            "cancelled": appointments.filter(status="cancelled").count(),
        }

    # Export actions
    export_type = request.GET.get("export")
    if export_type and appointments is not None:
        if export_type == "csv":
            filename, content_type, content = export_csv(appointments)
            log_action(
                user=profile,
                action="REPORT_EXPORT",
                table_name="reports",
                metadata={"format": "csv", "count": appointments.count()},
            )
            response = HttpResponse(content, content_type=content_type)
            response["Content-Disposition"] = f"attachment; filename={filename}"
            return response
        elif export_type == "pdf":
            filename, content_type, content = export_pdf(appointments)
            if content:
                log_action(
                    user=profile,
                    action="REPORT_EXPORT",
                    table_name="reports",
                    metadata={"format": "pdf", "count": appointments.count()},
                )
                response = HttpResponse(content, content_type=content_type)
                response["Content-Disposition"] = f"attachment; filename={filename}"
                return response
            else:
                messages.error(request, "PDF export requires reportlab. Install it with: pip install reportlab")

    counselors = Profile.objects.filter(role="counselor").order_by("full_name")

    return render(request, "admin_panel/reports.html", {
        "profile": profile,
        "filters": filters,
        "appointments": appointments[:50] if appointments is not None else None,
        "summary": summary,
        "counselors": counselors,
        "concern_choices": CONCERN_CHOICES,
        "status_choices": STATUS_CHOICES,
    })


@role_required("admin")
def admin_profile_view(request):
    """Admin profile — account info + password change link."""
    return render(request, "admin_panel/profile.html", {
        "profile": request.profile,
    })
