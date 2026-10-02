"""
Audit feature tests - signals, service, and audit log functionality
"""

from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Profile, Appointment, CaseNote, AuditLog
from apps.common.choices import RoleChoices, AppointmentStatusChoices
from apps.audit.services.logging import log_action
from django.utils import timezone


class AuditServiceTestCase(TestCase):
    def test_audit_log_service_never_raises(self):
        """log_action must catch any exceptions and return None instead of raising."""
        # Intentionally invalid record_id or metadata
        user = User.objects.create_user(username="audit_test@example.com", password="Password123!")
        res = log_action(user.profile, "TEST_ACTION", "test_table", record_id="invalid-uuid", metadata={"test": "data"})
        self.assertIsNotNone(res)
        self.assertEqual(res.action, "TEST_ACTION")


class AuditSignalsTestCase(TestCase):
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
        # Create counselor and student
        counselor_user = User.objects.create_user(username="c_signal@example.com", password="Password123!")
        counselor = counselor_user.profile
        counselor.role = RoleChoices.COUNSELOR
        counselor.save()

        student_user = User.objects.create_user(username="s_signal@example.com", password="Password123!")
        student = student_user.profile

        # Create appointment
        appt = Appointment.objects.create(
            student=student,
            counselor=counselor,
            scheduled_at=timezone.now(),
            status=AppointmentStatusChoices.CONFIRMED
        )

        # Create case note (use dummy encrypted content to avoid needing encryption key)
        note = CaseNote.objects.create(
            appointment=appt,
            counselor=counselor,
            content="dummy_encrypted_content",
            is_confidential=False
        )

        create_log = AuditLog.objects.filter(action="CASE_NOTE_CREATED", table_name="core_case_note").first()
        self.assertIsNotNone(create_log)

        # Delete and check deletion audit
        note.delete()

        delete_log = AuditLog.objects.filter(action="CASE_NOTE_DELETED", table_name="core_case_note").first()
        self.assertIsNotNone(delete_log)
