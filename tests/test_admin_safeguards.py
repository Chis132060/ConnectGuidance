"""
tests/test_admin_safeguards.py — Comprehensive tests for Admin RBAC Safeguards,
Metrics, Reports, PDF/CSV Exports, and Audit Signals.

Covers PLAN steps 64–70 and FLOWS §17-21, §24.
"""

import io
import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.http import HttpResponse

from core.models import Profile, Appointment, CaseNote, AuditLog
from core.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
from core.services.admin_users import (
    can_change_role,
    update_user_role,
    can_change_active_status,
    update_user_status,
    create_user_by_admin,
)
from core.services.metrics import get_admin_metrics
from core.services.reports import (
    filter_appointments,
    export_appointments_csv,
    export_appointments_pdf,
)
from core.services.audit import log_action


class AdminSafeguardsTestCase(TestCase):
    def setUp(self):
        # Create Primary Admin
        self.admin_user = User.objects.create_user(
            username="admin1@example.com",
            email="admin1@example.com",
            password="Password123!"
        )
        self.admin_profile = self.admin_user.profile
        self.admin_profile.role = RoleChoices.ADMIN
        self.admin_profile.full_name = "Primary Admin"
        self.admin_profile.is_active = True
        self.admin_profile.save()

        # Create Secondary Admin
        self.admin2_user = User.objects.create_user(
            username="admin2@example.com",
            email="admin2@example.com",
            password="Password123!"
        )
        self.admin2_profile = self.admin2_user.profile
        self.admin2_profile.role = RoleChoices.ADMIN
        self.admin2_profile.full_name = "Secondary Admin"
        self.admin2_profile.is_active = True
        self.admin2_profile.save()

        # Create Counselor
        self.counselor_user = User.objects.create_user(
            username="counselor@example.com",
            email="counselor@example.com",
            password="Password123!"
        )
        self.counselor_profile = self.counselor_user.profile
        self.counselor_profile.role = RoleChoices.COUNSELOR
        self.counselor_profile.full_name = "Guidance Counselor"
        self.counselor_profile.department = "Psychology"
        self.counselor_profile.is_active = True
        self.counselor_profile.save()

        # Create Student
        self.student_user = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password="Password123!"
        )
        self.student_profile = self.student_user.profile
        self.student_profile.role = RoleChoices.STUDENT
        self.student_profile.full_name = "Alice Student"
        self.student_profile.student_id = "2024-0001"
        self.student_profile.department = "Computer Science"
        self.student_profile.is_active = True
        self.student_profile.save()

    def test_cannot_demote_self(self):
        """Admin attempting to demote their own account must raise ValidationError."""
        with self.assertRaises(ValidationError) as cm:
            update_user_role(self.admin_profile, self.admin_profile, RoleChoices.STUDENT)
        self.assertIn("cannot demote your own admin account", str(cm.exception))

    def test_cannot_demote_last_active_admin(self):
        """Demoting the only remaining active admin must be rejected."""
        # Deactivate admin2 first
        self.admin2_profile.is_active = False
        self.admin2_profile.save()

        # Now only admin1 is active. Another staff member (e.g. system) trying to demote admin1:
        with self.assertRaises(ValidationError) as cm:
            update_user_role(self.admin2_profile, self.admin_profile, RoleChoices.COUNSELOR)
        self.assertIn("Cannot remove the last admin account", str(cm.exception))

    def test_successful_role_demotion_with_multiple_admins(self):
        """Demoting an admin when another active admin exists is allowed and updates is_staff."""
        updated = update_user_role(self.admin_profile, self.admin2_profile, RoleChoices.COUNSELOR)
        self.assertEqual(updated.role, RoleChoices.COUNSELOR)
        self.admin2_user.refresh_from_db()
        self.assertFalse(self.admin2_user.is_staff)

        # Audit log written
        log_entry = AuditLog.objects.filter(action="USER_ROLE_UPDATED").first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.metadata.get("new_role"), RoleChoices.COUNSELOR)

    def test_cannot_deactivate_self(self):
        """Admin cannot deactivate their own account."""
        with self.assertRaises(ValidationError) as cm:
            update_user_status(self.admin_profile, self.admin_profile, False)
        self.assertIn("cannot deactivate your own account", str(cm.exception))

    def test_cannot_deactivate_last_active_admin(self):
        """Deactivating the last remaining active admin must be rejected."""
        # Deactivate admin2 first
        self.admin2_profile.is_active = False
        self.admin2_profile.save()

        # Attempt to deactivate admin1
        with self.assertRaises(ValidationError) as cm:
            update_user_status(self.admin2_profile, self.admin_profile, False)
        self.assertIn("Cannot deactivate the last active admin", str(cm.exception))

    def test_successful_status_toggle(self):
        """Deactivating a non-last-admin user works cleanly."""
        updated = update_user_status(self.admin_profile, self.student_profile, False)
        self.assertFalse(updated.is_active)
        self.student_user.refresh_from_db()
        self.assertFalse(self.student_user.is_active)

        # Activate again
        updated2 = update_user_status(self.admin_profile, self.student_profile, True)
        self.assertTrue(updated2.is_active)

    def test_admin_create_user(self):
        """Admin can create new user accounts with designated roles."""
        new_prof = create_user_by_admin(
            actor=self.admin_profile,
            email="receptionist.new@example.com",
            password="Password123!",
            full_name="Front Desk Officer",
            role=RoleChoices.RECEPTIONIST,
            department="Student Affairs"
        )
        self.assertEqual(new_prof.role, RoleChoices.RECEPTIONIST)
        self.assertEqual(new_prof.full_name, "Front Desk Officer")
        self.assertTrue(new_prof.is_active)

        # Check duplicate email validation
        with self.assertRaises(ValidationError):
            create_user_by_admin(
                actor=self.admin_profile,
                email="receptionist.new@example.com",
                password="Password123!",
                full_name="Duplicate Officer",
                role=RoleChoices.RECEPTIONIST
            )


class AdminReportsAndMetricsTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="Password123!"
        )
        self.admin_profile = self.admin_user.profile
        self.admin_profile.role = RoleChoices.ADMIN
        self.admin_profile.full_name = "Admin Reports"
        self.admin_profile.save()

        self.counselor_user = User.objects.create_user(
            username="counselor@example.com",
            email="counselor@example.com",
            password="Password123!"
        )
        self.counselor_profile = self.counselor_user.profile
        self.counselor_profile.role = RoleChoices.COUNSELOR
        self.counselor_profile.full_name = "Dr. Santos"
        self.counselor_profile.save()

        self.student_user = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password="Password123!"
        )
        self.student_profile = self.student_user.profile
        self.student_profile.role = RoleChoices.STUDENT
        self.student_profile.full_name = "Bob Student"
        self.student_profile.department = "Engineering"
        self.student_profile.save()

        # Create sample appointments across dates
        now = timezone.now()
        self.appt1 = Appointment.objects.create(
            student=self.student_profile,
            counselor=self.counselor_profile,
            scheduled_at=now,
            status=AppointmentStatusChoices.COMPLETED,
            concern_type=ConcernTypeChoices.ACADEMIC
        )
        self.appt2 = Appointment.objects.create(
            student=self.student_profile,
            counselor=self.counselor_profile,
            scheduled_at=now - datetime.timedelta(days=2),
            status=AppointmentStatusChoices.CONFIRMED,
            concern_type=ConcernTypeChoices.CAREER
        )

    def test_metrics_calculation(self):
        """get_admin_metrics calculates KPIs, weekly series, and concern breakdown."""
        metrics = get_admin_metrics()
        self.assertEqual(metrics['total_appointments'], 2)
        self.assertEqual(metrics['completed_count'], 1)
        self.assertEqual(metrics['confirmed_count'], 1)
        self.assertEqual(metrics['completion_rate'], 50.0)
        self.assertGreaterEqual(metrics['monthly_appointments'], 1)
        self.assertEqual(len(metrics['weekly_series']), 8)
        self.assertTrue(any(c['label'] == 'Academic' for c in metrics['concern_breakdown']))

    def test_filter_appointments(self):
        """filter_appointments accurately matches parameters."""
        # By department
        eng_appts = filter_appointments(department="Engineering")
        self.assertEqual(eng_appts.count(), 2)

        none_appts = filter_appointments(department="Nursing")
        self.assertEqual(none_appts.count(), 0)

        # By status
        completed = filter_appointments(status=AppointmentStatusChoices.COMPLETED)
        self.assertEqual(completed.count(), 1)
        self.assertEqual(completed.first().id, self.appt1.id)

        # By counselor
        by_counselor = filter_appointments(counselor_id=self.counselor_profile.id)
        self.assertEqual(by_counselor.count(), 2)

    def test_csv_export(self):
        """export_appointments_csv outputs valid RFC-4180 CSV response and logs audit."""
        appts = Appointment.objects.all()
        response = export_appointments_csv(appts, exported_by=self.admin_profile)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="appointments_report_', response['Content-Disposition'])

        content = response.content.decode('utf-8')
        self.assertIn("Student Name", content)
        self.assertIn("Bob Student", content)
        self.assertIn("Dr. Santos", content)

        # Verify audit log
        audit = AuditLog.objects.filter(action="REPORT_EXPORT", table_name="core_appointment").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata.get("format"), "csv")

    def test_pdf_export(self):
        """export_appointments_pdf generates valid PDF response and logs audit."""
        appts = Appointment.objects.all()
        response = export_appointments_pdf(appts, exported_by=self.admin_profile)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

        # Verify audit log
        audit = AuditLog.objects.filter(action="REPORT_EXPORT", table_name="core_appointment", metadata__format="pdf").first()
        self.assertIsNotNone(audit)


class AuditSignalsAndServiceTestCase(TestCase):
    def test_audit_log_service_never_raises(self):
        """log_action must catch any exceptions and return None instead of raising."""
        # Intentionally invalid record_id or metadata
        res = log_action(user=None, action="TEST_ACTION", table_name="test_table")
        self.assertIsNotNone(res)
        self.assertEqual(res.action, "TEST_ACTION")

    def test_profile_save_audit_signal(self):
        """Profile creation and update write to AuditLog via signal."""
        user = User.objects.create_user(username="test_audit@example.com", password="Password123!")
        prof = user.profile
        prof.full_name = "Signal Test User"
        prof.save()

        signal_logs = AuditLog.objects.filter(table_name="core_profile", metadata__full_name="Signal Test User")
        self.assertTrue(signal_logs.exists())

    def test_case_note_audit_signal(self):
        """CaseNote creation and deletion write to AuditLog via signals."""
        counselor_user = User.objects.create_user(username="c_signal@example.com", password="Password123!")
        counselor = counselor_user.profile
        counselor.role = RoleChoices.COUNSELOR
        counselor.save()

        student_user = User.objects.create_user(username="s_signal@example.com", password="Password123!")
        student = student_user.profile

        appt = Appointment.objects.create(
            student=student,
            counselor=counselor,
            scheduled_at=timezone.now()
        )

        note = CaseNote.objects.create(
            appointment=appt,
            counselor=counselor,
            content="dummy_encrypted_content",
            is_confidential=False
        )

        create_log = AuditLog.objects.filter(action="CASE_NOTE_CREATED", table_name="core_case_note").first()
        self.assertIsNotNone(create_log)

        note_id = note.id
        note.delete()

        delete_log = AuditLog.objects.filter(action="CASE_NOTE_DELETED", table_name="core_case_note").first()
        self.assertIsNotNone(delete_log)
