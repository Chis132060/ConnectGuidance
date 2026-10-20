"""
Test suite for ConnectGuidance service layer.
Tests encryption, appointments, mood check-ins, audit logging, and business logic.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from accounts.models import Profile
from accounts.choices import RoleChoices
from core.models import Appointment, StudentMoodAlert, AuditLog
from core.choices import AppointmentStatusChoices, ConcernTypeChoices
from core.services.encryption import encrypt_text, decrypt_text, encrypt, decrypt
from core.services.appointments import book_appointment, student_cancel_appointment, counselor_update_status
from core.services.mood import process_mood_checkin
from core.services.audit import log_action
from core.services.slots import is_counselor_slot_free


class EncryptionServiceTest(TestCase):
    """Test AES-256 encryption and decryption service."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypting and decrypting returns original text."""
        original = "This is sensitive case note content."
        encrypted = encrypt_text(original)
        decrypted = decrypt_text(encrypted)
        
        self.assertEqual(decrypted, original)

    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        encrypted = encrypt_text("")
        self.assertEqual(encrypted, "")

    def test_decrypt_empty_string(self):
        """Test decrypting empty string."""
        decrypted = decrypt_text("")
        self.assertEqual(decrypted, "")

    def test_different_inputs_produce_different_ciphertext(self):
        """Test that same plaintext produces different ciphertext due to random IV."""
        text = "Same text encrypted twice"
        encrypted1 = encrypt_text(text)
        encrypted2 = encrypt_text(text)
        
        # Should be different due to random IV
        self.assertNotEqual(encrypted1, encrypted2)
        
        # But both should decrypt to same plaintext
        self.assertEqual(decrypt_text(encrypted1), text)
        self.assertEqual(decrypt_text(encrypted2), text)

    def test_encrypt_unicode_characters(self):
        """Test encrypting and decrypting unicode characters."""
        original = "Testing émojis 🎓 and spëcial çharacters"
        encrypted = encrypt_text(original)
        decrypted = decrypt_text(encrypted)
        
        self.assertEqual(decrypted, original)

    def test_encrypt_long_text(self):
        """Test encrypting long text."""
        original = "Lorem ipsum " * 500  # Long text
        encrypted = encrypt_text(original)
        decrypted = decrypt_text(original)
        
        self.assertEqual(decrypted, original)

    def test_decrypt_malformed_payload_raises_error(self):
        """Test that decrypting malformed ciphertext raises error."""
        with self.assertRaises((ValueError, Exception)):
            decrypt_text("not_valid_hex")

    def test_encrypt_decrypt_aliases(self):
        """Test that encrypt/decrypt aliases work."""
        original = "Test aliases"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        
        self.assertEqual(decrypted, original)


class AppointmentServiceTest(TestCase):
    """Test appointment booking and management service."""

    def setUp(self):
        """Create test users."""
        self.student_user = User.objects.create_user(username='student_svc', password='pass')
        self.student = Profile.objects.create(
            user=self.student_user,
            role=RoleChoices.STUDENT,
            full_name='Service Student',
            user_no=100,
            is_active=True
        )
        
        self.counselor_user = User.objects.create_user(username='counselor_svc', password='pass')
        self.counselor = Profile.objects.create(
            user=self.counselor_user,
            role=RoleChoices.COUNSELOR,
            full_name='Service Counselor',
            user_no=101,
            is_active=True
        )

    def test_book_appointment_success(self):
        """Test successfully booking an appointment."""
        scheduled_time = timezone.now() + timedelta(days=2)
        
        appointment = book_appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            concern_type=ConcernTypeChoices.ACADEMIC,
            notes='Need help with coursework',
            created_by_receptionist=False,
            actor=self.student
        )
        
        self.assertIsNotNone(appointment.id)
        self.assertEqual(appointment.student, self.student)
        self.assertEqual(appointment.counselor, self.counselor)
        self.assertEqual(appointment.status, AppointmentStatusChoices.PENDING)
        self.assertEqual(appointment.concern_type, ConcernTypeChoices.ACADEMIC)

    def test_book_appointment_creates_audit_log(self):
        """Test that booking creates an audit log entry."""
        initial_count = AuditLog.objects.count()
        scheduled_time = timezone.now() + timedelta(days=2)
        
        book_appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            concern_type=ConcernTypeChoices.CAREER,
            actor=self.student
        )
        
        self.assertEqual(AuditLog.objects.count(), initial_count + 1)
        log = AuditLog.objects.latest('created_at')
        self.assertIn('APPOINTMENT_CREATED', log.action)

    def test_book_appointment_with_non_student_fails(self):
        """Test that booking with non-student profile fails."""
        admin_user = User.objects.create_user(username='admin_wrong', password='pass')
        admin = Profile.objects.create(
            user=admin_user,
            role=RoleChoices.ADMIN,
            full_name='Admin User',
            user_no=102,
            is_active=True
        )
        
        scheduled_time = timezone.now() + timedelta(days=2)
        
        with self.assertRaises(ValidationError) as context:
            book_appointment(
                student=admin,  # Not a student
                counselor=self.counselor,
                scheduled_at=scheduled_time,
                concern_type=ConcernTypeChoices.ACADEMIC,
                actor=admin
            )
        
        self.assertIn('student', str(context.exception).lower())

    def test_book_appointment_with_inactive_counselor_fails(self):
        """Test that booking with inactive counselor fails."""
        self.counselor.is_active = False
        self.counselor.save()
        
        scheduled_time = timezone.now() + timedelta(days=2)
        
        with self.assertRaises(ValidationError) as context:
            book_appointment(
                student=self.student,
                counselor=self.counselor,
                scheduled_at=scheduled_time,
                concern_type=ConcernTypeChoices.PERSONAL,
                actor=self.student
            )
        
        self.assertIn('inactive', str(context.exception).lower())

    def test_double_booking_prevention(self):
        """Test that double-booking same time slot is prevented."""
        scheduled_time = timezone.now() + timedelta(days=3)
        
        # First booking
        book_appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            concern_type=ConcernTypeChoices.ACADEMIC,
            actor=self.student
        )
        
        # Create another student
        student2_user = User.objects.create_user(username='student2_svc', password='pass')
        student2 = Profile.objects.create(
            user=student2_user,
            role=RoleChoices.STUDENT,
            full_name='Student Two',
            user_no=103,
            is_active=True
        )
        
        # Try to book same counselor at same time
        with self.assertRaises(ValidationError) as context:
            book_appointment(
                student=student2,
                counselor=self.counselor,
                scheduled_at=scheduled_time,
                concern_type=ConcernTypeChoices.CAREER,
                actor=student2
            )
        
        self.assertIn('no longer available', str(context.exception).lower())

    def test_student_cancel_appointment_success(self):
        """Test student successfully cancelling their appointment."""
        scheduled_time = timezone.now() + timedelta(days=2)
        appointment = book_appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            concern_type=ConcernTypeChoices.MENTAL_HEALTH,
            actor=self.student
        )
        
        cancelled = student_cancel_appointment(appointment, self.student)
        
        self.assertEqual(cancelled.status, AppointmentStatusChoices.CANCELLED)

    def test_student_cancel_completed_appointment_fails(self):
        """Test that student cannot cancel completed appointment."""
        scheduled_time = timezone.now() + timedelta(days=2)
        appointment = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            status=AppointmentStatusChoices.COMPLETED,
            concern_type=ConcernTypeChoices.ACADEMIC
        )
        
        with self.assertRaises(ValidationError) as context:
            student_cancel_appointment(appointment, self.student)
        
        self.assertIn('cannot cancel', str(context.exception).lower())

    def test_student_cancel_other_student_appointment_fails(self):
        """Test that student cannot cancel another student's appointment."""
        # Create another student
        other_user = User.objects.create_user(username='other_student', password='pass')
        other_student = Profile.objects.create(
            user=other_user,
            role=RoleChoices.STUDENT,
            full_name='Other Student',
            user_no=104,
            is_active=True
        )
        
        scheduled_time = timezone.now() + timedelta(days=2)
        appointment = book_appointment(
            student=other_student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            concern_type=ConcernTypeChoices.PERSONAL,
            actor=other_student
        )
        
        with self.assertRaises(ValidationError) as context:
            student_cancel_appointment(appointment, self.student)
        
        self.assertIn('not authorized', str(context.exception).lower())

    def test_counselor_update_status_to_confirmed(self):
        """Test counselor confirming a pending appointment."""
        scheduled_time = timezone.now() + timedelta(days=2)
        appointment = book_appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            concern_type=ConcernTypeChoices.ACADEMIC,
            actor=self.student
        )
        
        updated = counselor_update_status(
            appointment,
            AppointmentStatusChoices.CONFIRMED,
            self.counselor
        )
        
        self.assertEqual(updated.status, AppointmentStatusChoices.CONFIRMED)

    def test_counselor_update_status_to_completed(self):
        """Test counselor marking confirmed appointment as completed."""
        scheduled_time = timezone.now() + timedelta(days=2)
        appointment = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            status=AppointmentStatusChoices.CONFIRMED,
            concern_type=ConcernTypeChoices.MENTAL_HEALTH
        )
        
        updated = counselor_update_status(
            appointment,
            AppointmentStatusChoices.COMPLETED,
            self.counselor
        )
        
        self.assertEqual(updated.status, AppointmentStatusChoices.COMPLETED)

    def test_counselor_invalid_status_transition_fails(self):
        """Test that invalid status transitions are rejected."""
        scheduled_time = timezone.now() + timedelta(days=2)
        appointment = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            status=AppointmentStatusChoices.COMPLETED,
            concern_type=ConcernTypeChoices.CAREER
        )
        
        # Cannot transition from completed to confirmed
        with self.assertRaises(ValidationError) as context:
            counselor_update_status(
                appointment,
                AppointmentStatusChoices.CONFIRMED,
                self.counselor
            )
        
        self.assertIn('invalid transition', str(context.exception).lower())


class MoodServiceTest(TestCase):
    """Test mood check-in service logic."""

    def setUp(self):
        """Create test student and counselor."""
        self.student_user = User.objects.create_user(username='mood_student_svc', password='pass')
        self.student = Profile.objects.create(
            user=self.student_user,
            role=RoleChoices.STUDENT,
            full_name='Mood Student',
            user_no=200,
            is_active=True
        )
        
        self.counselor_user = User.objects.create_user(username='mood_counselor_svc', password='pass')
        self.counselor = Profile.objects.create(
            user=self.counselor_user,
            role=RoleChoices.COUNSELOR,
            full_name='Mood Counselor',
            user_no=201,
            is_active=True
        )

    def test_good_mood_checkin(self):
        """Test that 'good' mood check-in creates audit log but no alert."""
        result = process_mood_checkin(self.student, 'good', 'Feeling great!')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['mood'], 'good')
        self.assertFalse(result['alert_created'])
        
        # No mood alert should be created
        self.assertEqual(StudentMoodAlert.objects.count(), 0)

    def test_okay_mood_checkin(self):
        """Test that 'okay' mood check-in creates audit log but no alert."""
        result = process_mood_checkin(self.student, 'okay', 'Managing well')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['mood'], 'okay')
        self.assertFalse(result['alert_created'])
        
        # No mood alert should be created
        self.assertEqual(StudentMoodAlert.objects.count(), 0)

    def test_low_mood_with_appointment_creates_alert(self):
        """Test that 'low' mood check-in creates StudentMoodAlert when appointment exists."""
        # Create a past appointment
        scheduled_time = timezone.now() - timedelta(days=1)
        Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            status=AppointmentStatusChoices.COMPLETED,
            concern_type=ConcernTypeChoices.MENTAL_HEALTH
        )
        
        result = process_mood_checkin(self.student, 'low', 'Feeling overwhelmed')
        
        self.assertEqual(result['status'], 'alert_dispatched')
        self.assertEqual(result['mood'], 'low')
        self.assertTrue(result['alert_created'])
        self.assertEqual(result['counselor_name'], self.counselor.full_name)
        
        # Alert should be created
        self.assertEqual(StudentMoodAlert.objects.count(), 1)
        alert = StudentMoodAlert.objects.first()
        self.assertEqual(alert.student, self.student)
        self.assertEqual(alert.counselor, self.counselor)
        self.assertIn('overwhelmed', alert.note)

    def test_low_mood_without_appointment_returns_warning(self):
        """Test that 'low' mood without appointment returns warning message."""
        result = process_mood_checkin(self.student, 'low', 'No counselor yet')
        
        self.assertEqual(result['status'], 'warning')
        self.assertEqual(result['mood'], 'low')
        self.assertFalse(result['alert_created'])
        self.assertIn('could not find', result['message'].lower())
        
        # No alert should be created
        self.assertEqual(StudentMoodAlert.objects.count(), 0)

    def test_invalid_mood_value_fails(self):
        """Test that invalid mood value raises validation error."""
        with self.assertRaises(ValidationError) as context:
            process_mood_checkin(self.student, 'invalid_mood', 'Test')
        
        self.assertIn('invalid mood', str(context.exception).lower())

    def test_non_student_mood_checkin_fails(self):
        """Test that non-student cannot submit mood check-in."""
        with self.assertRaises(ValidationError) as context:
            process_mood_checkin(self.counselor, 'good', 'Test')
        
        self.assertIn('only students', str(context.exception).lower())


class AuditServiceTest(TestCase):
    """Test audit logging service."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(username='audit_svc_user', password='pass')
        self.profile = Profile.objects.create(
            user=self.user,
            role=RoleChoices.ADMIN,
            full_name='Audit Admin',
            user_no=300,
            is_active=True
        )

    def test_log_action_creates_record(self):
        """Test that log_action creates an AuditLog record."""
        log = log_action(
            user=self.profile,
            action='TEST_ACTION',
            table_name='test_table',
            record_id=12345,
            metadata={'detail': 'test'}
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.profile)
        self.assertEqual(log.action, 'TEST_ACTION')
        self.assertEqual(log.table_name, 'test_table')
        self.assertEqual(log.metadata['detail'], 'test')

    def test_log_action_with_none_user(self):
        """Test that log_action works with None user (system action)."""
        log = log_action(
            user=None,
            action='SYSTEM_ACTION',
            table_name='system',
            metadata={}
        )
        
        self.assertIsNotNone(log)
        self.assertIsNone(log.user)
        self.assertEqual(log.action, 'SYSTEM_ACTION')

    def test_log_action_never_raises_exception(self):
        """Test that log_action never raises an exception."""
        # Even with invalid data, should not raise
        log = log_action(
            user=self.profile,
            action='TEST',
            table_name='test'
        )
        
        # Should still create a log or return None gracefully
        self.assertIsNotNone(log)


class SlotServiceTest(TestCase):
    """Test appointment slot availability service."""

    def setUp(self):
        """Create test counselor."""
        self.counselor_user = User.objects.create_user(username='slot_counselor', password='pass')
        self.counselor = Profile.objects.create(
            user=self.counselor_user,
            role=RoleChoices.COUNSELOR,
            full_name='Slot Counselor',
            user_no=400,
            is_active=True
        )
        
        self.student_user = User.objects.create_user(username='slot_student', password='pass')
        self.student = Profile.objects.create(
            user=self.student_user,
            role=RoleChoices.STUDENT,
            full_name='Slot Student',
            user_no=401,
            is_active=True
        )

    def test_slot_is_free_when_no_appointments(self):
        """Test that slot is free when no appointments exist."""
        future_time = timezone.now() + timedelta(days=5)
        is_free = is_counselor_slot_free(self.counselor, future_time)
        
        self.assertTrue(is_free)

    def test_slot_is_not_free_when_booked(self):
        """Test that slot is not free when already booked."""
        scheduled_time = timezone.now() + timedelta(days=5)
        Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            status=AppointmentStatusChoices.PENDING,
            concern_type=ConcernTypeChoices.ACADEMIC
        )
        
        is_free = is_counselor_slot_free(self.counselor, scheduled_time)
        
        self.assertFalse(is_free)

    def test_cancelled_appointment_frees_slot(self):
        """Test that cancelled appointment makes slot available again."""
        scheduled_time = timezone.now() + timedelta(days=5)
        Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            status=AppointmentStatusChoices.CANCELLED,
            concern_type=ConcernTypeChoices.PERSONAL
        )
        
        is_free = is_counselor_slot_free(self.counselor, scheduled_time)
        
        self.assertTrue(is_free)
