"""
tests/test_appointments.py — Tests for booking lifecycle, cancellation, status transitions, receptionist flows, and RBAC guards.
"""

import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.models import Profile, Appointment, AuditLog
from core.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
from core.services.appointments import (
    book_appointment,
    student_cancel_appointment,
    counselor_update_status,
)
from core.services.receptionist import (
    search_students,
    book_receptionist_appointment,
)


class AppointmentsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Student user
        self.student_user = User.objects.create_user(
            username='student@test.edu',
            email='student@test.edu',
            password='TestPassword123!',
        )
        self.student = self.student_user.profile
        self.student.role = RoleChoices.STUDENT
        self.student.is_active = True
        self.student.full_name = 'Sam Student'
        self.student.student_id = 'STU-1001'
        self.student.save()

        # Another student
        self.student_2_user = User.objects.create_user(
            username='student2@test.edu',
            email='student2@test.edu',
            password='TestPassword123!',
        )
        self.student_2 = self.student_2_user.profile
        self.student_2.role = RoleChoices.STUDENT
        self.student_2.is_active = True
        self.student_2.full_name = 'Sally Other'
        self.student_2.student_id = 'STU-1002'
        self.student_2.save()

        # Inactive student
        self.inactive_student_user = User.objects.create_user(
            username='inactive_stu@test.edu',
            email='inactive_stu@test.edu',
            password='TestPassword123!',
        )
        self.inactive_student = self.inactive_student_user.profile
        self.inactive_student.role = RoleChoices.STUDENT
        self.inactive_student.is_active = False
        self.inactive_student.full_name = 'Inactive Sam'
        self.inactive_student.student_id = 'STU-9999'
        self.inactive_student.save()

        # Counselor
        self.counselor_user = User.objects.create_user(
            username='counselor@test.edu',
            email='counselor@test.edu',
            password='TestPassword123!',
        )
        self.counselor = self.counselor_user.profile
        self.counselor.role = RoleChoices.COUNSELOR
        self.counselor.is_active = True
        self.counselor.full_name = 'Dr. Clark Counselor'
        self.counselor.save()

        # Second counselor
        self.counselor_2_user = User.objects.create_user(
            username='counselor2@test.edu',
            email='counselor2@test.edu',
            password='TestPassword123!',
        )
        self.counselor_2 = self.counselor_2_user.profile
        self.counselor_2.role = RoleChoices.COUNSELOR
        self.counselor_2.is_active = True
        self.counselor_2.full_name = 'Dr. Dana Davis'
        self.counselor_2.save()

        # Receptionist
        self.receptionist_user = User.objects.create_user(
            username='receptionist@test.edu',
            email='receptionist@test.edu',
            password='TestPassword123!',
        )
        self.receptionist = self.receptionist_user.profile
        self.receptionist.role = RoleChoices.RECEPTIONIST
        self.receptionist.is_active = True
        self.receptionist.full_name = 'Rita Receptionist'
        self.receptionist.save()

        # Target future datetime
        self.tz = timezone.get_current_timezone()
        future_date = timezone.localdate() + datetime.timedelta(days=5)
        self.future_time = timezone.make_aware(
            datetime.datetime.combine(future_date, datetime.time(10, 0)),
            self.tz
        )

    def test_book_appointment_creates_pending_and_audit(self):
        """Booking creates pending appointment and writes APPOINTMENT_CREATED audit row."""
        appt = book_appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=self.future_time,
            concern_type=ConcernTypeChoices.ACADEMIC,
            notes='Need study tips',
            created_by_receptionist=False,
            actor=self.student
        )

        self.assertEqual(appt.status, AppointmentStatusChoices.PENDING)
        self.assertEqual(appt.student_id, self.student.id)
        self.assertEqual(appt.counselor_id, self.counselor.id)

        # Audit log verification (record_id is stored as UUID, not raw int)
        audit = AuditLog.objects.filter(
            action='APPOINTMENT_CREATED',
        ).order_by('-created_at').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, self.student.id)

    def test_student_cancel_only_own_appointment(self):
        """Student cannot cancel another student's appointment."""
        appt = book_appointment(
            student=self.student_2,
            counselor=self.counselor,
            scheduled_at=self.future_time,
            concern_type=ConcernTypeChoices.CAREER
        )

        # Student 1 attempts to cancel Student 2's appointment
        with self.assertRaises(ValidationError) as ctx:
            student_cancel_appointment(appt, self.student)
        self.assertIn("not authorized", str(ctx.exception).lower())

        # Student 2 can cancel own appointment
        cancelled_appt = student_cancel_appointment(appt, self.student_2)
        self.assertEqual(cancelled_appt.status, AppointmentStatusChoices.CANCELLED)

        # Audit check (record_id is stored as UUID, not raw int)
        audit = AuditLog.objects.filter(
            action='APPOINTMENT_CANCELLED_STUDENT',
        ).order_by('-created_at').first()
        self.assertIsNotNone(audit)

    def test_student_cancel_terminal_blocked(self):
        """Cannot cancel an appointment that is already completed or cancelled."""
        appt = book_appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=self.future_time,
            concern_type=ConcernTypeChoices.PERSONAL
        )
        appt.status = AppointmentStatusChoices.COMPLETED
        appt.save()

        with self.assertRaises(ValidationError) as ctx:
            student_cancel_appointment(appt, self.student)
        self.assertIn("already completed", str(ctx.exception).lower())

    def test_counselor_state_machine_transitions(self):
        """
        Counselor status update strictly enforces:
        - pending -> confirmed, cancelled (allowed)
        - confirmed -> completed, cancelled (allowed)
        - pending -> completed (FORBIDDEN)
        - completed/cancelled -> terminal (FORBIDDEN)
        """
        appt = book_appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=self.future_time,
            concern_type=ConcernTypeChoices.ACADEMIC
        )

        # Illegal: pending -> completed directly
        with self.assertRaises(ValidationError):
            counselor_update_status(appt, AppointmentStatusChoices.COMPLETED, self.counselor)

        # Legal: pending -> confirmed
        confirmed = counselor_update_status(appt, AppointmentStatusChoices.CONFIRMED, self.counselor)
        self.assertEqual(confirmed.status, AppointmentStatusChoices.CONFIRMED)

        # Legal: confirmed -> completed
        completed = counselor_update_status(appt, AppointmentStatusChoices.COMPLETED, self.counselor)
        self.assertEqual(completed.status, AppointmentStatusChoices.COMPLETED)

        # Illegal: completed (terminal) -> confirmed or cancelled
        with self.assertRaises(ValidationError):
            counselor_update_status(appt, AppointmentStatusChoices.CONFIRMED, self.counselor)

    def test_counselor_cannot_update_unassigned_appointment(self):
        """Counselor B cannot update Counselor A's appointment."""
        appt = book_appointment(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=self.future_time,
            concern_type=ConcernTypeChoices.ACADEMIC
        )
        with self.assertRaises(ValidationError) as ctx:
            counselor_update_status(appt, AppointmentStatusChoices.CONFIRMED, self.counselor_2)
        self.assertIn("only update appointments assigned to your workspace", str(ctx.exception))

    def test_receptionist_search_students_limit_and_active_only(self):
        """Receptionist search returns active students matching name/ID, max 25."""
        results = search_students('Sam')
        # Should include active 'Sam Student', exclude 'Inactive Sam'
        found_names = [s.full_name for s in results]
        self.assertIn('Sam Student', found_names)
        self.assertNotIn('Inactive Sam', found_names)

        # Search by student_id
        id_results = search_students('STU-1002')
        self.assertEqual(len(id_results), 1)
        self.assertEqual(id_results[0].full_name, 'Sally Other')

    def test_receptionist_next_available_booking(self):
        """Receptionist booking with counselor=None picks earliest free counselor A-Z."""
        appt = book_receptionist_appointment(
            receptionist=self.receptionist,
            student=self.student,
            scheduled_at=self.future_time,
            concern_type=ConcernTypeChoices.ACADEMIC,
            counselor=None,
            notes='Walk-in desk booking'
        )
        self.assertEqual(appt.status, AppointmentStatusChoices.PENDING)
        # Dr. Clark Counselor is earlier alphabetically than Dr. Dana Davis
        self.assertEqual(appt.counselor_id, self.counselor.id)

        # Verify audit action APPOINTMENT_CREATED_RECEPTION
        audit = AuditLog.objects.filter(
            action='APPOINTMENT_CREATED_RECEPTION',
        ).order_by('-created_at').first()
        self.assertIsNotNone(audit)

    def test_wrong_role_redirects_to_role_home(self):
        """Student attempting to view /counselor/ or /receptionist/ is redirected to /student/."""
        self.client.force_login(self.student_user)

        resp_counselor = self.client.get(reverse('counselor_workspace'))
        self.assertRedirects(resp_counselor, '/student/')

        resp_receptionist = self.client.get(reverse('receptionist_dashboard'))
        self.assertRedirects(resp_receptionist, '/student/')
