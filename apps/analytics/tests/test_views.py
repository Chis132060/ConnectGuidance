"""
apps/analytics/tests/test_views.py — Tests for analytics and reporting views.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Profile
from apps.common.choices import RoleChoices


class AnalyticsViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="AdminPass123!"
        )
        self.admin_profile = self.admin_user.profile
        self.admin_profile.role = RoleChoices.ADMIN
        self.admin_profile.full_name = "Admin User"
        self.admin_profile.is_active = True
        self.admin_profile.save()
        
        # Create student user for access tests
        self.student_user = User.objects.create_user(
            username="student@test.com",
            email="student@test.com",
            password="StudentPass123!"
        )
        self.student_profile = self.student_user.profile
        self.student_profile.role = RoleChoices.STUDENT
        self.student_profile.full_name = "Student User"
        self.student_profile.is_active = True
        self.student_profile.save()

    def test_admin_overview_requires_admin_role(self):
        """Non-admin users should not access overview"""
        self.client.login(username="student@test.com", password="StudentPass123!")
        response = self.client.get(reverse('admin_overview'))
        self.assertEqual(response.status_code, 302)  # Redirect to login or forbidden

    def test_admin_overview_accessible_by_admin(self):
        """Admin users should access overview"""
        self.client.login(username="admin@test.com", password="AdminPass123!")
        response = self.client.get(reverse('admin_overview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'metrics')

    def test_admin_reports_requires_admin_role(self):
        """Non-admin users should not access reports"""
        self.client.login(username="student@test.com", password="StudentPass123!")
        response = self.client.get(reverse('admin_reports'))
        self.assertEqual(response.status_code, 302)

    def test_admin_reports_accessible_by_admin(self):
        """Admin users should access reports"""
        self.client.login(username="admin@test.com", password="AdminPass123!")
        response = self.client.get(reverse('admin_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'report')
