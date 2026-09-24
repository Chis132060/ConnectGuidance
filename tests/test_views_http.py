"""
tests/test_views_http.py — HTTP Route & Template Verification Suite.

Verifies that all 16 designated screens (plus the widget include) respond with HTTP 200
and render their exact corresponding template files as required by INTERFACES.md and PLAN step 63.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Profile, Appointment, CaseNote
from core.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices


class ViewsHttpTemplateTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Student
        self.student_user = User.objects.create_user(
            username='student@test.edu',
            email='student@test.edu',
            password='Password123!',
        )
        self.student = self.student_user.profile
        self.student.role = RoleChoices.STUDENT
        self.student.is_active = True
        self.student.full_name = 'Test Student'
        self.student.save()

        # Counselor
        self.counselor_user = User.objects.create_user(
            username='counselor@test.edu',
            email='counselor@test.edu',
            password='Password123!',
        )
        self.counselor = self.counselor_user.profile
        self.counselor.role = RoleChoices.COUNSELOR
        self.counselor.is_active = True
        self.counselor.full_name = 'Dr. Test Counselor'
        self.counselor.save()

        # Admin
        self.admin_user = User.objects.create_user(
            username='admin@test.edu',
            email='admin@test.edu',
            password='Password123!',
            is_staff=True,
        )
        self.admin = self.admin_user.profile
        self.admin.role = RoleChoices.ADMIN
        self.admin.is_active = True
        self.admin.full_name = 'System Admin'
        self.admin.save()

        # Receptionist
        self.receptionist_user = User.objects.create_user(
            username='receptionist@test.edu',
            email='receptionist@test.edu',
            password='Password123!',
        )
        self.receptionist = self.receptionist_user.profile
        self.receptionist.role = RoleChoices.RECEPTIONIST
        self.receptionist.is_active = True
        self.receptionist.full_name = 'Test Receptionist'
        self.receptionist.save()

        # Sample Appointment assigned to counselor
        self.appointment = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=timezone.now(),
            status=AppointmentStatusChoices.CONFIRMED,
            concern_type=ConcernTypeChoices.ACADEMIC
        )

    # -------------------------------------------------------------------------
    # Public Screens (3 routes)
    # -------------------------------------------------------------------------
    def test_screen_01_landing(self):
        """1. GET / -> public/landing.html (HTTP 200)"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'public/landing.html')

    def test_screen_02_login(self):
        """2. GET /login/ -> registration/login.html (HTTP 200)"""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_screen_03_register(self):
        """3. GET /register/ -> registration/register.html (HTTP 200)"""
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

    # -------------------------------------------------------------------------
    # Student Screens (5 routes + widget overlay)
    # -------------------------------------------------------------------------
    def test_screen_04_student_dashboard(self):
        """4. GET /student/ -> student/dashboard.html (HTTP 200)"""
        self.client.force_login(self.student_user)
        response = self.client.get('/student/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'student/dashboard.html')
        self.assertTemplateUsed(response, 'widgets/chatbot.html')

    def test_screen_05_student_appointments(self):
        """5. GET /appointments/ -> student/appointments.html (HTTP 200)"""
        self.client.force_login(self.student_user)
        response = self.client.get('/appointments/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'student/appointments.html')

    def test_screen_06_student_chatbot(self):
        """6. GET /chatbot/ -> student/chatbot.html (HTTP 200)"""
        self.client.force_login(self.student_user)
        response = self.client.get('/chatbot/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'student/chatbot.html')

    def test_screen_07_student_profile(self):
        """7. GET /student/profile/ -> student/profile.html (HTTP 200)"""
        self.client.force_login(self.student_user)
        response = self.client.get('/student/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'student/profile.html')

    def test_screen_08_student_front_desk(self):
        """8. GET /student/front-desk/ -> student/front_desk.html (HTTP 200)"""
        self.client.force_login(self.student_user)
        response = self.client.get('/student/front-desk/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'student/front_desk.html')

    # -------------------------------------------------------------------------
    # Counselor Screens (2 routes)
    # -------------------------------------------------------------------------
    def test_screen_09_counselor_workspace(self):
        """9. GET /counselor/ -> counselor/workspace.html (HTTP 200)"""
        self.client.force_login(self.counselor_user)
        response = self.client.get('/counselor/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'counselor/workspace.html')

    def test_screen_10_counselor_case_note(self):
        """10. GET /counselor/case-notes/<id>/ -> counselor/case_note.html (HTTP 200)"""
        self.client.force_login(self.counselor_user)
        response = self.client.get(f'/counselor/case-notes/{self.appointment.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'counselor/case_note.html')

    # -------------------------------------------------------------------------
    # Administrator Screens (5 routes)
    # -------------------------------------------------------------------------
    def test_screen_11_admin_overview(self):
        """11. GET /admin-panel/ -> admin/overview.html (HTTP 200)"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-panel/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/overview.html')

    def test_screen_12_admin_users(self):
        """12. GET /admin-panel/users/ -> admin/users.html (HTTP 200)"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-panel/users/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/users.html')

    def test_screen_13_admin_audit(self):
        """13. GET /admin-panel/audit/ -> admin/audit_logs.html (HTTP 200)"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-panel/audit/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/audit_logs.html')

    def test_screen_14_admin_reports(self):
        """14. GET /admin-panel/reports/ -> admin/reports.html (HTTP 200)"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-panel/reports/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/reports.html')

    def test_screen_15_admin_profile(self):
        """15. GET /admin-panel/profile/ -> admin/profile.html (HTTP 200)"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-panel/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/profile.html')

    # -------------------------------------------------------------------------
    # Receptionist Screen (1 route)
    # -------------------------------------------------------------------------
    def test_screen_16_receptionist_booking(self):
        """16. GET /receptionist/ -> receptionist/booking.html (HTTP 200)"""
        self.client.force_login(self.receptionist_user)
        response = self.client.get('/receptionist/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'receptionist/booking.html')
