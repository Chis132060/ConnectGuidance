import io
import csv
import datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db.models import Count, Q
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from core.models import Appointment, Profile, AuditLog
from core.choices import AppointmentStatusChoices, RoleChoices, ConcernTypeChoices
from .audit import log_action


def get_admin_metrics() -> Dict[str, Any]:
    """Computes executive KPI summary and historical metrics."""
    now = timezone.now()
    eight_weeks_ago = now - datetime.timedelta(weeks=8)

    total_appointments = Appointment.objects.count()
    status_counts = Appointment.objects.values('status').annotate(total=Count('id'))
    status_map = {item['status']: item['total'] for item in status_counts}

    total_students = Profile.objects.filter(role=RoleChoices.STUDENT, is_active=True).count()
    total_counselors = Profile.objects.filter(role=RoleChoices.COUNSELOR, is_active=True).count()

    concern_counts = Appointment.objects.values('concern_type').annotate(count=Count('id')).order_by('-count')

    # Weekly series for 8 weeks
    weekly_series = []
    for week_idx in range(7, -1, -1):
        w_start = (now - datetime.timedelta(weeks=week_idx + 1)).replace(hour=0, minute=0, second=0)
        w_end = (now - datetime.timedelta(weeks=week_idx)).replace(hour=23, minute=59, second=59)
        c = Appointment.objects.filter(scheduled_at__gte=w_start, scheduled_at__lte=w_end).count()
        weekly_series.append({
            'label': w_start.strftime('Wk %W (%b %d)'),
            'count': c
        })

    return {
        'total_appointments': total_appointments,
        'pending_count': status_map.get(AppointmentStatusChoices.PENDING, 0),
        'confirmed_count': status_map.get(AppointmentStatusChoices.CONFIRMED, 0),
        'completed_count': status_map.get(AppointmentStatusChoices.COMPLETED, 0),
        'cancelled_count': status_map.get(AppointmentStatusChoices.CANCELLED, 0),
        'total_students': total_students,
        'total_counselors': total_counselors,
        'concern_breakdown': list(concern_counts),
        'weekly_series': weekly_series,
    }


def filter_appointments(
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    department: Optional[str] = None,
    concern_type: Optional[str] = None,
    status: Optional[str] = None
):
    """Filter appointment queryset based on report criteria."""
    qs = Appointment.objects.select_related('student', 'counselor').all()
    if start_date:
        qs = qs.filter(scheduled_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(scheduled_at__date__lte=end_date)
    if department:
        qs = qs.filter(student__department__iexact=department)
    if concern_type:
        qs = qs.filter(concern_type=concern_type)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by('-scheduled_at')


def export_appointments_csv(appointments, exported_by: Profile) -> str:
    """Generate RFC-4180 CSV string of filtered appointments."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Scheduled At", "Status", "Concern Type",
        "Student Name", "Student ID", "Department",
        "Counselor Name", "Created At"
    ])

    for appt in appointments:
        writer.writerow([
            appt.id,
            appt.scheduled_at.strftime("%Y-%m-%d %H:%M"),
            appt.status,
            appt.get_concern_type_display(),
            appt.student.full_name,
            appt.student.student_id or "",
            appt.student.department or "",
            appt.counselor.full_name,
            appt.created_at.strftime("%Y-%m-%d %H:%M")
        ])

    log_action(
        user=exported_by,
        action="REPORT_EXPORT",
        table_name="core_appointment",
        metadata={"format": "csv", "count": appointments.count()}
    )

    return output.getvalue()


def export_appointments_pdf(appointments, exported_by: Profile) -> bytes:
    """Generate PDF document using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=12
    )
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=18
    )

    elements = [
        Paragraph("GuidanceConnect — Appointments Report", title_style),
        Paragraph(f"Exported by {exported_by.full_name} on {timezone.now():%B %d, %Y at %I:%M %p} | Total Records: {appointments.count()}", meta_style),
        Spacer(1, 10)
    ]

    table_data = [
        ["ID", "Scheduled Date", "Student", "Counselor", "Concern", "Status"]
    ]

    for appt in appointments[:200]:  # Cap PDF at 200 items for clean rendering
        table_data.append([
            str(appt.id),
            appt.scheduled_at.strftime("%Y-%m-%d %H:%M"),
            appt.student.full_name[:20],
            appt.counselor.full_name[:20],
            appt.get_concern_type_display()[:15],
            appt.status.upper()
        ])

    table = Table(table_data, colWidths=[35, 110, 115, 115, 95, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))

    elements.append(table)
    doc.build(elements)

    log_action(
        user=exported_by,
        action="REPORT_EXPORT",
        table_name="core_appointment",
        metadata={"format": "pdf", "count": appointments.count()}
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
