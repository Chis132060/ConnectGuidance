"""
tests/test_auth_guards.py — Tests for Phase 3: Auth views, routing, and role guards.
"""

from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import HttpResponse

from core.models import Profile
from core.choices import RoleChoices
from core.guards import (
    role_required,
    require_student,
    require_counselor,
    require_admin,
    require_receptionist,
    get_role_home,
)


class AuthAndGuardsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Create active users for each role
        self.student_user = User.objects.create_user(
            username='student@test.edu',
            email='student@test.edu',
            password='TestPassword123!',
            first_name='Test',
            last_name='Student',
        )
        # Profile is created via post_save signal on User
        self.student_profile = self.student_user.profile
        self.student_profile.role = RoleChoices.STUDENT
        self.student_profile.is_active = True
        self.student_profile.save()

        self.counselor_user = User.objects.create_user(
            username='counselor@test.edu',
            email='counselor@test.edu',
            password='TestPassword123!',
            first_name='Test',
            last_name='Counselor',
        )
        self.counselor_profile = self.counselor_user.profile
        self.counselor_profile.role = RoleChoices.COUNSELOR
        self.counselor_profile.is_active = True
        self.counselor_profile.save()

        self.admin_user = User.objects.create_user(
            username='admin@test.edu',
            email='admin@test.edu',
            password='TestPassword123!',
            first_name='Test',
            last_name='Admin',
        )
        self.admin_profile = self.admin_user.profile
        self.admin_profile.role = RoleChoices.ADMIN
        self.admin_profile.is_active = True
        self.admin_profile.save()

        self.receptionist_user = User.objects.create_user(
            username='receptionist@test.edu',
            email='receptionist@test.edu',
            password='TestPassword123!',
            first_name='Test',
            last_name='Receptionist',
        )
        self.receptionist_profile = self.receptionist_user.profile
        self.receptionist_profile.role = RoleChoices.RECEPTIONIST
        self.receptionist_profile.is_active = True
        self.receptionist_profile.save()

        # Inactive user
        self.inactive_user = User.objects.create_user(
            username='inactive@test.edu',
            email='inactive@test.edu',
            password='TestPassword123!',
        )
        self.inactive_profile = self.inactive_user.profile
        self.inactive_profile.role = RoleChoices.STUDENT
        self.inactive_profile.is_active = False
        self.inactive_profile.save()

    def test_register_creates_user_and_profile(self):
        """Registering a new student creates User and Profile with role=student."""
        response = self.client.post(reverse('register'), {
            'email': 'newstudent@test.edu',
            'full_name': 'Jane Student',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'student_id': 'STU-9999',
            'department': 'Computer Science',
        })
        # Successful registration redirects to login
        self.assertRedirects(response, reverse('login'))

        # Check User and Profile
        user = User.objects.filter(email='newstudent@test.edu').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'newstudent@test.edu')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.role, RoleChoices.STUDENT)
        self.assertEqual(user.profile.full_name, 'Jane Student')
        self.assertEqual(user.profile.student_id, 'STU-9999')
        self.assertEqual(user.profile.department, 'Computer Science')
        self.assertTrue(user.profile.is_active)

    def test_login_by_email_success(self):
        """User can login using their email and valid password."""
        response = self.client.post(reverse('login'), {
            'email': 'student@test.edu',
            'password': 'TestPassword123!',
        })
        # Should redirect to student role home (/student/)
        self.assertRedirects(response, '/student/')
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_wrong_password_fails(self):
        """Login with wrong password shows form error and does not authenticate."""
        response = self.client.post(reverse('login'), {
            'email': 'student@test.edu',
            'password': 'WrongPassword999!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password.')
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_login_inactive_redirects_deactivated(self):
        """Inactive user attempting login is redirected with error=deactivated."""
        response = self.client.post(reverse('login'), {
            'email': 'inactive@test.edu',
            'password': 'TestPassword123!',
        })
        self.assertRedirects(response, '/login/?error=deactivated')
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_logout_redirects_to_root(self):
        """Logout flushes session and redirects to /."""
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, '/')
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_role_home_redirects_all_four_roles(self):
        """role_home_view redirects each role to its designated dashboard URL."""
        role_map = [
            (self.student_user, '/student/'),
            (self.counselor_user, '/counselor/'),
            (self.admin_user, '/admin-panel/'),
            (self.receptionist_user, '/receptionist/'),
        ]
        for user, expected_url in role_map:
            self.client.force_login(user)
            response = self.client.get(reverse('role_home'))
            self.assertRedirects(response, expected_url)

    def test_authenticated_get_login_redirects_to_role_home(self):
        """Authenticated user accessing GET /login/ is redirected to their role home."""
        self.client.force_login(self.counselor_user)
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, '/counselor/')

    def test_authenticated_get_landing_redirects_to_role_home(self):
        """Authenticated user accessing GET / (landing) is redirected to their role home."""
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('landing'))
        self.assertRedirects(response, '/student/')

    def test_wrong_role_access_to_dummy_protected_view_redirects_role_home(self):
        """When a user visits a view guarded by @require_counselor, a student is redirected to /student/."""
        @require_counselor
        def dummy_counselor_view(request):
            return HttpResponse("Counselor Only Content")

        request = self.factory.get('/dummy-counselor/')
        request.user = self.student_user

        response = dummy_counselor_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/student/')

    def test_correct_role_access_to_protected_view_succeeds(self):
        """User with matching role passes through role guard."""
        @require_counselor
        def dummy_counselor_view(request):
            return HttpResponse("Counselor Only Content")

        request = self.factory.get('/dummy-counselor/')
        request.user = self.counselor_user

        response = dummy_counselor_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Counselor Only Content")
