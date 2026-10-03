"""
core/views/admin.py — Administrator views for GuidanceConnect Django replica.

Implements ADMIN Standardized Features:
1. Dashboard          → handled by apps.analytics (admin_overview_view)
2. Analytics & Reports → handled by apps.analytics (admin_reports_view)
3. User Management    → handled by apps.users (admin_users_view)
4. Audit Logs         → handled by apps.audit (admin_audit_logs_view)
5. Appointments       → admin_appointments_view (this file)
6. Profile            → handled by apps.users (admin_profile_view)
"""

from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone

from apps.authentication.guards import require_admin
from core.models import Appointment, Profile
from apps.common.choices import AppointmentStatusChoices, RoleChoices


@require_admin
def admin_appointments_view(request):
    """
    ADMIN #5: All-Appointments Registry.
    Full system-wide appointment list with search, status filter, and date range filter.
    Allows admin oversight of all counseling sessions across all counselors and students.
    """
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
        from django.utils.dateparse import parse_date
        d = parse_date(date_from)
        if d:
            appointments = appointments.filter(scheduled_at__date__gte=d)

    if date_to:
        from django.utils.dateparse import parse_date
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

    counselors = Profile.objects.filter(
        role=RoleChoices.COUNSELOR, is_active=True
    ).order_by('full_name')

    context = {
        'profile': admin_profile,
        'appointments': appointments[:200],  # cap for performance
        'counts': counts,
        'active_filter': status_filter,
        'search_query': search_query,
        'counselors': counselors,
        'selected_counselor_id': counselor_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'admin/appointments.html', context)
