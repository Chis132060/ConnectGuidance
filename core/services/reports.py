"""
core/services/reports.py — Reporting and data export service for GuidanceConnect.

Implements FLOWS §20 and PLAN steps 67–68:
- Dynamic appointment filtering (dates, department, concern_type, status, counselor)
- RFC-4180 CSV export
- ReportLab PDF export with styled table and metadata summary
- Audit log integration for REPORT_EXPORT
"""

import io
import csv
import datetime
from typing import Optional, Union, Any
from django.utils import timezone
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from core.models import Appointment, Profile
from core.choices import RoleChoices, ConcernTypeChoices
from core.services.metrics import get_admin_metrics
from core.services.audit import log_action


def filter_appointments(
    start_date: Optional[Union[str, datetime.date]] = None,
    end_date: Optional[Union[str, datetime.date]] = None,
    department: Optional[str] = None,
    concern_type: Optional[str] = None,
    status: Optional[str] = None,
    counselor_id: Optional[int] = None,
):
    """
    Filter appointment queryset based on report criteria.
    Accepts string or date objects for start_date / end_date.
    """
    qs = Appointment.objects.select_related('student', 'counselor').all()

    # Parse start_date if string
    if start_date:
        if isinstance(start_date, str) and start_date.strip():
            try:
                parsed_start = datetime.datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
                qs = qs.filter(scheduled_at__date__gte=parsed_start)
            except ValueError:
                pass
        elif isinstance(start_date, (datetime.date, datetime.datetime)):
            qs = qs.filter(scheduled_at__date__gte=start_date)

    # Parse end_date if string
    if end_date:
        if isinstance(end_date, str) and end_date.strip():
            try:
                parsed_end = datetime.datetime.strptime(end_date.strip(), "%Y-%m-%d").date()
                qs = qs.filter(scheduled_at__date__lte=parsed_end)
            except ValueError:
                pass
        elif isinstance(end_date, (datetime.date, datetime.datetime)):
            qs = qs.filter(scheduled_at__date__lte=end_date)

    if department and department.strip():
        qs = qs.filter(student__department__icontains=department.strip())

    if concern_type and concern_type.strip():
        qs = qs.filter(concern_type=concern_type.strip())

    if status and status.strip():
        qs = qs.filter(status=status.strip())

    if counselor_id:
        qs = qs.filter(counselor_id=counselor_id)

    return qs.order_by('-scheduled_at')


def export_appointments_csv(appointments, exported_by: Optional[Profile] = None) -> HttpResponse:
    """Generate RFC-4180 CSV HttpResponse of filtered appointments."""
    response = HttpResponse(content_type='text/csv')
    timestamp_str = timezone.now().strftime("%Y%m%d_%H%M")
    response['Content-Disposition'] = f'attachment; filename="appointments_report_{timestamp_str}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID", "Scheduled At", "Status", "Concern Type",
        "Student Name", "Student ID", "Department",
        "Counselor Name", "Created At"
    ])

    count = 0
    for appt in appointments:
        count += 1
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

    if exported_by:
        log_action(
            user=exported_by,
            action="REPORT_EXPORT",
            table_name="core_appointment",
            metadata={"format": "csv", "count": count}
        )

    return response


def export_appointments_pdf(appointments, exported_by: Optional[Profile] = None) -> HttpResponse:
    """Generate PDF document using ReportLab and return as HttpResponse."""
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

    exporter_name = exported_by.full_name if exported_by else "Administrator"
    total_count = appointments.count() if hasattr(appointments, 'count') else len(appointments)

    elements = [
        Paragraph("GuidanceConnect — Appointments Report", title_style),
        Paragraph(
            f"Exported by {exporter_name} on {timezone.now():%B %d, %Y at %I:%M %p} | Total Records: {total_count}",
            meta_style
        ),
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

    if exported_by:
        log_action(
            user=exported_by,
            action="REPORT_EXPORT",
            table_name="core_appointment",
            metadata={"format": "pdf", "count": total_count}
        )

    pdf_bytes = buffer.getvalue()
    buffer.close()

    timestamp_str = timezone.now().strftime("%Y%m%d_%H%M")
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="appointments_report_{timestamp_str}.pdf"'
    return response
