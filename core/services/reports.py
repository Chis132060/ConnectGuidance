"""
core/services/reports.py — Reporting and data export service for GuidanceConnect.
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
        qs = qs.filter(student__department__iexact=department.strip())

    if concern_type and concern_type.strip():
        qs = qs.filter(concern_type=concern_type.strip())

    if status and status.strip():
        qs = qs.filter(status=status.strip())

    if counselor_id:
        try:
            qs = qs.filter(counselor_id=int(counselor_id))
        except (ValueError, TypeError):
            pass

    return qs.order_by('-scheduled_at')


def export_appointments_csv(
    queryset,
    exported_by: Optional[Profile] = None,
    actor: Optional[Profile] = None,
    metadata: Optional[dict] = None
) -> HttpResponse:
    """
    Export queryset to RFC-4180 compliant CSV stream and log audit trail.
    """
    effective_actor = exported_by or actor
    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    response['Content-Disposition'] = f'attachment; filename="appointments_report_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Appointment ID",
        "Student ID",
        "Student Name",
        "Department",
        "Counselor Name",
        "Scheduled At",
        "Status",
        "Concern Type",
        "Created At"
    ])

    count = 0
    for appt in queryset:
        count += 1
        scheduled_str = appt.scheduled_at.strftime("%Y-%m-%d %H:%M") if appt.scheduled_at else ""
        created_str = appt.created_at.strftime("%Y-%m-%d %H:%M") if appt.created_at else ""
        student_id_str = appt.student.student_id or ""
        dept_str = appt.student.department or ""
        
        writer.writerow([
            appt.id,
            student_id_str,
            appt.student.full_name,
            dept_str,
            appt.counselor.full_name,
            scheduled_str,
            appt.get_status_display(),
            appt.get_concern_type_display(),
            created_str
        ])

    log_action(
        user=effective_actor,
        action="REPORT_EXPORT",
        table_name="core_appointment",
        metadata={
            "format": "csv",
            "record_count": count,
            "filter_params": metadata or {}
        }
    )

    return response


def export_appointments_pdf(
    queryset,
    exported_by: Optional[Profile] = None,
    actor: Optional[Profile] = None,
    metadata: Optional[dict] = None
) -> HttpResponse:
    """
    Export queryset to a clean ReportLab PDF document and log audit trail.
    """
    effective_actor = exported_by or actor
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    elements = []
    styles = getSampleStyleSheet()

    # Title & Metadata
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=6
    )
    elements.append(Paragraph("GuidanceConnect — Executive Appointment Report", title_style))

    meta_text = f"Generated by: {actor.full_name if actor else 'System'} | Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Total Records: {queryset.count()}"
    elements.append(Paragraph(meta_text, styles['Normal']))
    elements.append(Spacer(1, 16))

    # Table data
    data = [
        ["Date / Time", "Student", "Dept", "Counselor", "Status", "Concern"]
    ]

    for appt in queryset[:500]:
        scheduled_str = appt.scheduled_at.strftime("%b %d, %H:%M") if appt.scheduled_at else ""
        student_name = appt.student.full_name[:18]
        dept = (appt.student.department or "—")[:12]
        counselor_name = appt.counselor.full_name[:18]
        status = appt.get_status_display()
        concern = appt.get_concern_type_display()[:15]

        data.append([scheduled_str, student_name, dept, counselor_name, status, concern])

    t = Table(data, colWidths=[90, 100, 75, 100, 75, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0284c7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))

    elements.append(t)
    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    response['Content-Disposition'] = f'attachment; filename="appointments_report_{timestamp}.pdf"'

    log_action(
        user=effective_actor,
        action="REPORT_EXPORT",
        table_name="core_appointment",
        metadata={
            "format": "pdf",
            "record_count": queryset.count(),
            "filter_params": metadata or {}
        }
    )

    return response
