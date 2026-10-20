"""
Test suite for ConnectGuidance core models.
Tests model creation, validation, constraints, and business logic.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from accounts.models import Profile
from accounts.choices import RoleChoices
from core.models import Appointment, CaseNote, AuditLog, StudentMoodAlert, ChatbotSession
from core.choices import AppointmentStatusChoices, ConcernTypeChoices
from core.services.encryption import encrypt_text


class AppointmentModelTest(TestCase):
    """Test Appointment model validation and behavior."""

    def setUp(self):
        """Create test users and profiles."""
        self.student_user = User.objects.create_user(username='student_test', password='pass')
        self.student = Profile.objects.create(
            user=self.student_user,
            role=RoleChoices.STUDENT,
            full_name='Test Student',
            user_no=1,
            is_active=True
        )
        
        self.counselor_user = User.objects.create_user(username='counselor_test', password='pass')
        self.counselor = Profile.objects.create(
            user=self.counselor_user,
            role=RoleChoices.COUNSELOR,
            full_name='Test Counselor',
            user_no=2,
            is_active=True
        )

    def test_appointment_creation(self):
        """Test creating a basic appointment."""
        scheduled_time = timezone.now() + timedelta(days=1)
        appointment = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            status=AppointmentStatusChoices.PENDING,
            concern_type=ConcernTypeChoices.ACADEMIC,
            notes='First session'
        )
        
        self.assertEqual(appointment.student, self.student)
        self.assertEqual(appointment.counselor, self.counselor)
        self.assertEqual(appointment.status, AppointmentStatusChoices.PENDING)
        self.assertEqual(appointment.concern_type, ConcernTypeChoices.ACADEMIC)
        self.assertIsNotNone(appointment.created_at)

    def test_appointment_str_representation(self):
        """Test __str__ method returns expected format."""
        scheduled_time = timezone.now() + timedelta(days=1)
        appointment = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            status=AppointmentStatusChoices.CONFIRMED,
            concern_type=ConcernTypeChoices.MENTAL_HEALTH
        )
        
        str_repr = str(appointment)
        self.assertIn(self.student.full_name, str_repr)
        self.assertIn(self.counselor.full_name, str_repr)
        self.assertIn('confirmed', str_repr.lower())

    def test_appointment_notes_max_length_validation(self):
        """Test that notes exceeding 2000 characters are rejected."""
        scheduled_time = timezone.now() + timedelta(days=1)
        long_notes = 'x' * 2001  # 2001 characters
        
        appointment = Appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            status=AppointmentStatusChoices.PENDING,
            concern_type=ConcernTypeChoices.CAREER,
            notes=long_notes
        )
        
        with self.assertRaises(ValidationError) as context:
            appointment.clean()
        
        self.assertIn('notes', str(context.exception).lower())

    def test_appointment_notes_within_limit(self):
        """Test that notes of exactly 2000 characters are accepted."""
        scheduled_time = timezone.now() + timedelta(days=1)
        notes = 'x' * 2000
        
        appointment = Appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=scheduled_time,
            status=AppointmentStatusChoices.PENDING,
            concern_type=ConcernTypeChoices.PERSONAL,
            notes=notes
        )
        
        # Should not raise
        appointment.clean()
        appointment.save()
        self.assertEqual(len(appointment.notes), 2000)

    def test_appointment_ordering(self):
        """Test appointments are ordered by scheduled_at descending."""
        now = timezone.now()
        appt1 = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=now + timedelta(days=1),
            status=AppointmentStatusChoices.PENDING,
            concern_type=ConcernTypeChoices.ACADEMIC
        )
        appt2 = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=now + timedelta(days=3),
            status=AppointmentStatusChoices.PENDING,
            concern_type=ConcernTypeChoices.ACADEMIC
        )
        appt3 = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=now + timedelta(days=2),
            status=AppointmentStatusChoices.PENDING,
            concern_type=ConcernTypeChoices.ACADEMIC
        )
        
        appointments = list(Appointment.objects.all())
        # Ordered by -scheduled_at, so newest first
        self.assertEqual(appointments[0], appt2)
        self.assertEqual(appointments[1], appt3)
        self.assertEqual(appointments[2], appt1)


class CaseNoteModelTest(TestCase):
    """Test CaseNote model validation and constraints."""

    def setUp(self):
        """Create test users and appointments."""
        self.student_user = User.objects.create_user(username='student_cn', password='pass')
        self.student = Profile.objects.create(
            user=self.student_user,
            role=RoleChoices.STUDENT,
            full_name='Student CaseNote',
            user_no=10,
            is_active=True
        )
        
        self.counselor_user = User.objects.create_user(username='counselor_cn', password='pass')
        self.counselor = Profile.objects.create(
            user=self.counselor_user,
            role=RoleChoices.COUNSELOR,
            full_name='Counselor CaseNote',
            user_no=11,
            is_active=True
        )
        
        self.other_counselor_user = User.objects.create_user(username='counselor_other', password='pass')
        self.other_counselor = Profile.objects.create(
            user=self.other_counselor_user,
            role=RoleChoices.COUNSELOR,
            full_name='Other Counselor',
            user_no=12,
            is_active=True
        )
        
        self.appointment = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=timezone.now() + timedelta(days=1),
            status=AppointmentStatusChoices.COMPLETED,
            concern_type=ConcernTypeChoices.ACADEMIC
        )

    def test_case_note_creation(self):
        """Test creating a case note with encrypted content."""
        encrypted_content = encrypt_text("Confidential session notes")
        case_note = CaseNote.objects.create(
            appointment=self.appointment,
            counselor=self.counselor,
            content=encrypted_content,
            is_confidential=True
        )
        
        self.assertEqual(case_note.appointment, self.appointment)
        self.assertEqual(case_note.counselor, self.counselor)
        self.assertTrue(case_note.is_confidential)
        self.assertIsNotNone(case_note.created_at)
        self.assertIsNotNone(case_note.updated_at)

    def test_case_note_counselor_must_match_appointment(self):
        """Test that counselor must match the appointment's counselor."""
        encrypted_content = encrypt_text("Test notes")
        case_note = CaseNote(
            appointment=self.appointment,
            counselor=self.other_counselor,  # Different counselor
            content=encrypted_content,
            is_confidential=False
        )
        
        with self.assertRaises(ValidationError) as context:
            case_note.clean()
        
        self.assertIn('counselor', str(context.exception).lower())

    def test_case_note_unique_constraint(self):
        """Test that only one case note per appointment-counselor pair is allowed."""
        encrypted_content = encrypt_text("First note")
        CaseNote.objects.create(
            appointment=self.appointment,
            counselor=self.counselor,
            content=encrypted_content,
            is_confidential=False
        )
        
        # Try to create another note for same appointment-counselor pair
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CaseNote.objects.create(
                appointment=self.appointment,
                counselor=self.counselor,
                content=encrypt_text("Second note"),
                is_confidential=False
            )

    def test_case_note_str_representation(self):
        """Test __str__ method."""
        encrypted_content = encrypt_text("Test")
        case_note = CaseNote.objects.create(
            appointment=self.appointment,
            counselor=self.counselor,
            content=encrypted_content
        )
        
        str_repr = str(case_note)
        self.assertIn(str(self.appointment.id), str_repr)
        self.assertIn(self.counselor.full_name, str_repr)


class AuditLogModelTest(TestCase):
    """Test AuditLog model behavior."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(username='audit_user', password='pass')
        self.profile = Profile.objects.create(
            user=self.user,
            role=RoleChoices.ADMIN,
            full_name='Audit Admin',
            user_no=20,
            is_active=True
        )

    def test_audit_log_creation(self):
        """Test creating an audit log entry."""
        log = AuditLog.objects.create(
            user=self.profile,
            action='TEST_ACTION',
            table_name='test_table',
            metadata={'key': 'value'}
        )
        
        self.assertEqual(log.user, self.profile)
        self.assertEqual(log.action, 'TEST_ACTION')
        self.assertEqual(log.table_name, 'test_table')
        self.assertEqual(log.metadata['key'], 'value')
        self.assertIsNotNone(log.created_at)

    def test_audit_log_nullable_user(self):
        """Test audit log can be created without a user (system action)."""
        log = AuditLog.objects.create(
            user=None,
            action='SYSTEM_ACTION',
            table_name='system_table',
            metadata={}
        )
        
        self.assertIsNone(log.user)
        self.assertEqual(log.action, 'SYSTEM_ACTION')

    def test_audit_log_str_representation(self):
        """Test __str__ method shows actor, action, and table."""
        log = AuditLog.objects.create(
            user=self.profile,
            action='USER_LOGIN',
            table_name='auth_user'
        )
        
        str_repr = str(log)
        self.assertIn(self.profile.full_name, str_repr)
        self.assertIn('USER_LOGIN', str_repr)
        self.assertIn('auth_user', str_repr)

    def test_audit_log_system_str_representation(self):
        """Test __str__ method for system actions."""
        log = AuditLog.objects.create(
            user=None,
            action='SCHEDULED_TASK',
            table_name='jobs'
        )
        
        str_repr = str(log)
        self.assertIn('System', str_repr)

    def test_audit_log_ordering(self):
        """Test audit logs are ordered by created_at descending."""
        log1 = AuditLog.objects.create(action='ACTION_1', table_name='test')
        log2 = AuditLog.objects.create(action='ACTION_2', table_name='test')
        log3 = AuditLog.objects.create(action='ACTION_3', table_name='test')
        
        logs = list(AuditLog.objects.all())
        # Most recent first
        self.assertEqual(logs[0], log3)
        self.assertEqual(logs[1], log2)
        self.assertEqual(logs[2], log1)


class StudentMoodAlertModelTest(TestCase):
    """Test StudentMoodAlert model."""

    def setUp(self):
        """Create test student and counselor."""
        self.student_user = User.objects.create_user(username='mood_student', password='pass')
        self.student = Profile.objects.create(
            user=self.student_user,
            role=RoleChoices.STUDENT,
            full_name='Mood Student',
            user_no=30,
            is_active=True
        )
        
        self.counselor_user = User.objects.create_user(username='mood_counselor', password='pass')
        self.counselor = Profile.objects.create(
            user=self.counselor_user,
            role=RoleChoices.COUNSELOR,
            full_name='Mood Counselor',
            user_no=31,
            is_active=True
        )

    def test_mood_alert_creation(self):
        """Test creating a mood alert."""
        alert = StudentMoodAlert.objects.create(
            student=self.student,
            counselor=self.counselor,
            note='Student feeling overwhelmed'
        )
        
        self.assertEqual(alert.student, self.student)
        self.assertEqual(alert.counselor, self.counselor)
        self.assertEqual(alert.note, 'Student feeling overwhelmed')
        self.assertIsNotNone(alert.created_at)

    def test_mood_alert_note_max_length_validation(self):
        """Test that note exceeding 500 characters is rejected."""
        long_note = 'x' * 501
        alert = StudentMoodAlert(
            student=self.student,
            counselor=self.counselor,
            note=long_note
        )
        
        with self.assertRaises(ValidationError) as context:
            alert.clean()
        
        self.assertIn('note', str(context.exception).lower())

    def test_mood_alert_note_within_limit(self):
        """Test that note of exactly 500 characters is accepted."""
        note = 'x' * 500
        alert = StudentMoodAlert(
            student=self.student,
            counselor=self.counselor,
            note=note
        )
        
        alert.clean()  # Should not raise
        alert.save()
        self.assertEqual(len(alert.note), 500)

    def test_mood_alert_str_representation(self):
        """Test __str__ method."""
        alert = StudentMoodAlert.objects.create(
            student=self.student,
            counselor=self.counselor,
            note='Test'
        )
        
        str_repr = str(alert)
        self.assertIn(self.student.full_name, str_repr)
        self.assertIn(self.counselor.full_name, str_repr)


class ProfileModelTest(TestCase):
    """Test Profile model is_active flag behavior."""

    def test_profile_is_active_default(self):
        """Test that is_active defaults to True."""
        user = User.objects.create_user(username='test_active', password='pass')
        profile = Profile.objects.create(
            user=user,
            role=RoleChoices.STUDENT,
            full_name='Active User',
            user_no=40
        )
        
        self.assertTrue(profile.is_active)

    def test_profile_can_be_deactivated(self):
        """Test that profile can be set to inactive."""
        user = User.objects.create_user(username='test_inactive', password='pass')
        profile = Profile.objects.create(
            user=user,
            role=RoleChoices.COUNSELOR,
            full_name='Inactive User',
            user_no=41,
            is_active=False
        )
        
        self.assertFalse(profile.is_active)

    def test_profile_str_representation(self):
        """Test __str__ method shows full_name and role."""
        user = User.objects.create_user(username='test_str', password='pass')
        profile = Profile.objects.create(
            user=user,
            role=RoleChoices.RECEPTIONIST,
            full_name='Test Receptionist',
            user_no=42
        )
        
        str_repr = str(profile)
        self.assertIn('Test Receptionist', str_repr)
        self.assertIn('Receptionist', str_repr)


class ChatbotSessionModelTest(TestCase):
    """Test ChatbotSession model."""

    def setUp(self):
        """Create test student."""
        self.student_user = User.objects.create_user(username='chat_student', password='pass')
        self.student = Profile.objects.create(
            user=self.student_user,
            role=RoleChoices.STUDENT,
            full_name='Chat Student',
            user_no=50,
            is_active=True
        )

    def test_chatbot_session_creation(self):
        """Test creating a chatbot session."""
        session = ChatbotSession.objects.create(
            student=self.student,
            messages=[
                {'role': 'user', 'content': 'Hello'},
                {'role': 'assistant', 'content': 'Hi there!'}
            ]
        )
        
        self.assertEqual(session.student, self.student)
        self.assertEqual(len(session.messages), 2)
        self.assertIsNotNone(session.created_at)

    def test_chatbot_session_str_representation(self):
        """Test __str__ method."""
        session = ChatbotSession.objects.create(
            student=self.student,
            messages=[{'role': 'user', 'content': 'Test'}]
        )
        
        str_repr = str(session)
        self.assertIn(self.student.full_name, str_repr)
        self.assertIn('1 msgs', str_repr)
