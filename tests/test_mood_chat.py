"""
tests/test_mood_chat.py — Tests for Phase 6: Student Mood Check-in and AI Chatbot (SSE streaming,
rate limits, history caps, crisis protocols, and session hydration).
"""

import json
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from core.models import Profile, Appointment, StudentMoodAlert, ChatbotSession, AuditLog
from core.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
from core.services.mood import process_mood_checkin
from core.services.chat import (
    check_chat_rate_limit,
    check_session_get_rate_limit,
    is_crisis_text,
    should_trigger_booking_cta,
    save_or_update_session,
    _RATE_LIMIT_STORE_POST,
    _RATE_LIMIT_STORE_GET,
)


class MoodAndChatTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        _RATE_LIMIT_STORE_POST.clear()
        _RATE_LIMIT_STORE_GET.clear()

        # Student 1
        self.student_user = User.objects.create_user(
            username='student1@test.edu',
            email='student1@test.edu',
            password='TestPassword123!',
        )
        self.student = self.student_user.profile
        self.student.role = RoleChoices.STUDENT
        self.student.is_active = True
        self.student.full_name = 'Student One'
        self.student.save()

        # Student 2
        self.student_user_2 = User.objects.create_user(
            username='student2@test.edu',
            email='student2@test.edu',
            password='TestPassword123!',
        )
        self.student_2 = self.student_user_2.profile
        self.student_2.role = RoleChoices.STUDENT
        self.student_2.is_active = True
        self.student_2.full_name = 'Student Two'
        self.student_2.save()

        # Counselor
        self.counselor_user = User.objects.create_user(
            username='counselor@test.edu',
            email='counselor@test.edu',
            password='TestPassword123!',
        )
        self.counselor = self.counselor_user.profile
        self.counselor.role = RoleChoices.COUNSELOR
        self.counselor.is_active = True
        self.counselor.full_name = 'Dr. Emily Stones'
        self.counselor.save()

    # -------------------------------------------------------------------------
    # Mood Check-in Tests (FLOWS §13)
    # -------------------------------------------------------------------------

    def test_mood_checkin_good_and_okay_branches(self):
        """'good' and 'okay' mood check-ins log audit and do not dispatch counselor alerts."""
        res_good = process_mood_checkin(self.student, 'good', 'Feeling optimistic about midterms')
        self.assertEqual(res_good['status'], 'success')
        self.assertFalse(res_good['alert_created'])

        res_okay = process_mood_checkin(self.student, 'okay')
        self.assertEqual(res_okay['status'], 'success')
        self.assertFalse(res_okay['alert_created'])

        # Verify audit log
        audit = AuditLog.objects.filter(action="STUDENT_MOOD_CHECKIN", user=self.student)
        self.assertEqual(audit.count(), 2)

    def test_mood_checkin_low_without_appointment_warns_student(self):
        """'low' mood with no active/past appointment creates no alert and prompts booking."""
        res_low = process_mood_checkin(self.student, 'low', 'Feeling very overwhelmed')
        self.assertEqual(res_low['status'], 'warning')
        self.assertFalse(res_low['alert_created'])
        self.assertIn("book a guidance appointment", res_low['message'].lower())
        self.assertEqual(StudentMoodAlert.objects.filter(student=self.student).count(), 0)

    def test_mood_checkin_low_with_appointment_dispatches_alert(self):
        """'low' mood with an appointment alerts the latest assigned counselor."""
        Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=timezone.now(),
            status=AppointmentStatusChoices.CONFIRMED,
            concern_type=ConcernTypeChoices.MENTAL_HEALTH
        )

        res_low = process_mood_checkin(self.student, 'low', 'Need urgent check-in')
        self.assertEqual(res_low['status'], 'alert_dispatched')
        self.assertTrue(res_low['alert_created'])
        self.assertEqual(res_low['counselor_name'], self.counselor.full_name)

        # Assert alert record in DB
        alert = StudentMoodAlert.objects.filter(student=self.student, counselor=self.counselor).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.note, 'Need urgent check-in')

        # Assert audit log
        audit = AuditLog.objects.filter(action="STUDENT_MOOD_ALERT", user=self.student).first()
        self.assertIsNotNone(audit)

    # -------------------------------------------------------------------------
    # Chat Rate Limit Tests (FLOWS §14 & §15)
    # -------------------------------------------------------------------------

    def test_chat_post_rate_limit_24_per_window(self):
        """POST /chat/ allows at most 24 requests per 15-minute window; 25th returns 429."""
        self.client.force_login(self.student_user)

        with patch('core.views.chat.has_llm_api_key', return_value=True):
            # Fill 24 slots
            for _ in range(24):
                self.assertTrue(check_chat_rate_limit(self.student.id))

            # 25th should be rejected
            self.assertFalse(check_chat_rate_limit(self.student.id))

            # Test through view
            resp = self.client.post(
                reverse('chat_stream_post'),
                data=json.dumps({'messages': [{'role': 'user', 'content': 'Hello'}]}),
                content_type='application/json'
            )
            self.assertEqual(resp.status_code, 429)
            self.assertTrue('Retry-After' in resp.headers)

    def test_chat_get_session_rate_limit_60_per_window(self):
        """GET /chat/session/ allows at most 60 requests per window; 61st returns 429."""
        self.client.force_login(self.student_user)

        for _ in range(60):
            self.assertTrue(check_session_get_rate_limit(self.student.id))

        self.assertFalse(check_session_get_rate_limit(self.student.id))

        resp = self.client.get(reverse('chat_session_get'))
        self.assertEqual(resp.status_code, 429)
        self.assertTrue('Retry-After' in resp.headers)

    # -------------------------------------------------------------------------
    # Chat Input Constraints & Validation
    # -------------------------------------------------------------------------

    @override_settings(GROQ_API_KEY='dummy-groq-key')
    def test_chat_post_validations(self):
        """Validates payload schema: non-empty, role='user', and content <= 24,000 characters."""
        self.client.force_login(self.student_user)

        # 1. Invalid role (last message assistant) -> 400
        resp = self.client.post(
            reverse('chat_stream_post'),
            data=json.dumps({'messages': [{'role': 'assistant', 'content': 'Hello'}]}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 400)

        # 2. Total content exceeds 24,000 characters -> 400
        oversized_text = "x" * 24001
        resp_oversized = self.client.post(
            reverse('chat_stream_post'),
            data=json.dumps({'messages': [{'role': 'user', 'content': oversized_text}]}),
            content_type='application/json'
        )
        self.assertEqual(resp_oversized.status_code, 400)

    def test_chat_post_503_when_no_api_keys(self):
        """POST /chat/ returns 503 Service Unavailable when neither Groq nor Anthropic keys exist."""
        self.client.force_login(self.student_user)

        with override_settings(GROQ_API_KEY='', ANTHROPIC_API_KEY=''):
            with patch('core.views.chat.has_llm_api_key', return_value=False):
                resp = self.client.post(
                    reverse('chat_stream_post'),
                    data=json.dumps({'messages': [{'role': 'user', 'content': 'Hello AI'}]}),
                    content_type='application/json'
                )
                self.assertEqual(resp.status_code, 503)

    def test_chat_history_cap_at_36(self):
        """Chat history is capped at the 36 most recent messages upon persistence."""
        long_history = [{'role': 'user' if i % 2 == 0 else 'assistant', 'content': f'msg {i}'} for i in range(50)]
        session = save_or_update_session(self.student, long_history)
        self.assertEqual(len(session.messages), 36)
        self.assertEqual(session.messages[-1]['content'], 'msg 49')

    # -------------------------------------------------------------------------
    # Crisis Detection & CTA Triggers
    # -------------------------------------------------------------------------

    def test_crisis_and_booking_cta_triggers(self):
        """Keywords trigger crisis protocol and booking CTA suggestions."""
        # Crisis text detection
        self.assertTrue(is_crisis_text("I feel like I want to die and end my life"))
        self.assertFalse(is_crisis_text("I need help with my calculus homework"))

        # Booking CTA detection
        self.assertTrue(should_trigger_booking_cta("I think I should schedule an appointment with a counselor"))
        self.assertTrue(should_trigger_booking_cta("I am experiencing severe burnout and stress"))
        self.assertFalse(should_trigger_booking_cta("What is the campus library schedule?"))

    # -------------------------------------------------------------------------
    # Session Hydration & Ownership Isolation
    # -------------------------------------------------------------------------

    def test_session_hydration_and_ownership_isolation(self):
        """Student gets their own session history; accessing another student's session is forbidden."""
        # Save session for Student 1
        session1 = ChatbotSession.objects.create(
            student=self.student,
            messages=[{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}]
        )

        # Student 1 gets their session
        self.client.force_login(self.student_user)
        resp1 = self.client.get(reverse('chat_session_get'))
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertEqual(data1['sessionId'], session1.id)
        self.assertEqual(len(data1['messages']), 2)

        # Student 2 logs in -> should have empty session
        self.client.force_login(self.student_user_2)
        resp2 = self.client.get(reverse('chat_session_get'))
        self.assertEqual(resp2.status_code, 200)
        self.assertIsNone(resp2.json()['sessionId'])

        # Student 2 attempts to post with Student 1's sessionId -> 403 Forbidden
        with patch('core.views.chat.has_llm_api_key', return_value=True):
            resp_cross = self.client.post(
                reverse('chat_stream_post'),
                data=json.dumps({
                    'sessionId': session1.id,
                    'messages': [{'role': 'user', 'content': 'Hijack attempt'}]
                }),
                content_type='application/json'
            )
            self.assertEqual(resp_cross.status_code, 403)
