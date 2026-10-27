from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import Profile
from core.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
from core.models import Appointment, CaseNote
from core.services.encryption import decrypt_text, encrypt_text


class CaseNotesWorkflowTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = self.create_profile('student', RoleChoices.STUDENT, 'Student User')
        self.counselor = self.create_profile('counselor', RoleChoices.COUNSELOR, 'Counselor User')
        self.admin = self.create_profile('admin', RoleChoices.ADMIN, 'Admin User')
        self.receptionist = self.create_profile('receptionist', RoleChoices.RECEPTIONIST, 'Receptionist User')
        self.appointment = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=timezone.now(),
            status=AppointmentStatusChoices.COMPLETED,
            concern_type=ConcernTypeChoices.ACADEMIC,
        )

    def create_profile(self, username, role, full_name):
        user = User.objects.create_user(username=username, password='Password123!')
        profile = user.profile
        profile.role = role
        profile.full_name = full_name
        profile.save()
        return profile

    def test_counselor_can_create_and_edit_case_note(self):
        self.client.force_login(self.counselor.user)
        response = self.client.post(
            f'/counselor/case-notes/{self.appointment.id}/',
            {'content': 'Initial assessment', 'is_confidential': ''},
        )
        self.assertRedirects(response, f'/counselor/case-notes/{self.appointment.id}/')

        note = CaseNote.objects.get(appointment=self.appointment)
        self.assertEqual(decrypt_text(note.content), 'Initial assessment')
        self.client.post(
            f'/counselor/case-notes/{self.appointment.id}/',
            {'content': 'Updated assessment', 'is_confidential': 'on'},
        )
        note.refresh_from_db()
        self.assertEqual(decrypt_text(note.content), 'Updated assessment')
        self.assertTrue(note.is_confidential)

    def test_student_sees_shared_note_but_not_confidential_note(self):
        CaseNote.objects.create(
            appointment=self.appointment,
            counselor=self.counselor,
            content=encrypt_text('Shared recommendation'),
            is_confidential=False,
        )
        self.client.force_login(self.student.user)
        response = self.client.get('/student/')
        self.assertContains(response, 'Shared recommendation')

        CaseNote.objects.filter(appointment=self.appointment).update(is_confidential=True)
        response = self.client.get('/student/')
        self.assertNotContains(response, 'Shared recommendation')

    def test_student_only_sees_shared_notes_for_completed_appointments(self):
        self.appointment.status = AppointmentStatusChoices.PENDING
        self.appointment.save(update_fields=['status'])
        CaseNote.objects.create(
            appointment=self.appointment,
            counselor=self.counselor,
            content=encrypt_text('Pending session note'),
            is_confidential=False,
        )

        self.client.force_login(self.student.user)
        response = self.client.get('/student/')
        self.assertNotContains(response, 'Pending session note')

        self.appointment.status = AppointmentStatusChoices.COMPLETED
        self.appointment.save(update_fields=['status'])
        response = self.client.get('/student/')
        self.assertContains(response, 'Pending session note')

    def test_student_can_view_shared_note_from_appointment_history(self):
        CaseNote.objects.create(
            appointment=self.appointment,
            counselor=self.counselor,
            content=encrypt_text('Read-only appointment note'),
            is_confidential=False,
        )

        self.client.force_login(self.student.user)
        response = self.client.get('/appointments/')

        self.assertContains(response, 'View Case Note')
        self.assertContains(response, 'Read-only appointment note')
        self.assertContains(response, 'student-case-note-modal')

        CaseNote.objects.filter(appointment=self.appointment).update(is_confidential=True)
        response = self.client.get('/appointments/')
        self.assertContains(response, 'View Case Note')
        self.assertNotContains(response, 'Read-only appointment note')

    def test_student_cannot_see_another_students_shared_note(self):
        other_student = self.create_profile('other_student', RoleChoices.STUDENT, 'Other Student')
        other_appointment = Appointment.objects.create(
            student=other_student,
            counselor=self.counselor,
            scheduled_at=timezone.now(),
            status=AppointmentStatusChoices.COMPLETED,
            concern_type=ConcernTypeChoices.CAREER,
        )
        CaseNote.objects.create(
            appointment=other_appointment,
            counselor=self.counselor,
            content=encrypt_text('Private other-student note'),
            is_confidential=False,
        )

        self.client.force_login(self.student.user)
        response = self.client.get('/student/')
        self.assertNotContains(response, 'Private other-student note')

    def test_counselor_cannot_open_another_counselors_case_note(self):
        other_counselor = self.create_profile('other_counselor', RoleChoices.COUNSELOR, 'Other Counselor')
        self.client.force_login(other_counselor.user)

        response = self.client.get(f'/counselor/case-notes/{self.appointment.id}/')
        self.assertEqual(response.status_code, 403)

        response = self.client.get('/counselor/case-notes/')
        self.assertNotContains(response, self.student.full_name)

    def test_admin_can_review_shared_notes_only(self):
        CaseNote.objects.create(
            appointment=self.appointment,
            counselor=self.counselor,
            content=encrypt_text('Admin-visible recommendation'),
            is_confidential=False,
        )
        self.client.force_login(self.admin.user)
        response = self.client.get('/admin-panel/case-notes/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin-visible recommendation')

        CaseNote.objects.filter(appointment=self.appointment).update(is_confidential=True)
        response = self.client.get('/admin-panel/case-notes/')
        self.assertNotContains(response, 'Admin-visible recommendation')

    def test_non_authorized_roles_cannot_open_case_note_editor(self):
        for profile in (self.student, self.admin, self.receptionist):
            self.client.force_login(profile.user)
            response = self.client.get(f'/counselor/case-notes/{self.appointment.id}/')
            self.assertRedirects(response, {
                RoleChoices.STUDENT: '/student/',
                RoleChoices.ADMIN: '/admin-panel/',
                RoleChoices.RECEPTIONIST: '/receptionist/',
            }[profile.role])
