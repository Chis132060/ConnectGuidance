"""
tests/test_slots.py — Tests for slot generation, counselor availability, clash windows, and next-available algorithm.
"""

import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Profile, Appointment
from core.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
from core.services.slots import (
    get_hourly_slots_for_date,
    get_available_slots_for_counselor,
    is_counselor_slot_free,
    get_first_available_counselor_slot,
)


class SlotsTestCase(TestCase):
    def setUp(self):
        # Create student
        self.student_user = User.objects.create_user(
            username='student1@test.edu',
            email='student1@test.edu',
            password='TestPassword123!',
        )
        self.student = self.student_user.profile
        self.student.role = RoleChoices.STUDENT
        self.student.is_active = True
        self.student.full_name = 'Alice Student'
        self.student.save()

        # Create 2 counselors with specific alphabetical names
        self.counselor_a_user = User.objects.create_user(
            username='counselor_a@test.edu',
            email='counselor_a@test.edu',
            password='TestPassword123!',
        )
        self.counselor_a = self.counselor_a_user.profile
        self.counselor_a.role = RoleChoices.COUNSELOR
        self.counselor_a.is_active = True
        self.counselor_a.full_name = 'Dr. Aaron Adams'
        self.counselor_a.save()

        self.counselor_b_user = User.objects.create_user(
            username='counselor_b@test.edu',
            email='counselor_b@test.edu',
            password='TestPassword123!',
        )
        self.counselor_b = self.counselor_b_user.profile
        self.counselor_b.role = RoleChoices.COUNSELOR
        self.counselor_b.is_active = True
        self.counselor_b.full_name = 'Dr. Beth Baker'
        self.counselor_b.save()

        # Target future date (10 days from now)
        self.target_date = timezone.localdate() + datetime.timedelta(days=10)

    def test_hourly_slots_range_09_to_16(self):
        """Slots must cover 09:00 to 16:00 inclusive (8 hourly slots)."""
        slots = get_hourly_slots_for_date(self.target_date)
        self.assertEqual(len(slots), 8)
        self.assertEqual(slots[0].hour, 9)
        self.assertEqual(slots[-1].hour, 16)

    def test_available_slots_subtracts_pending_and_confirmed(self):
        """Pending and Confirmed appointments make a slot unavailable, while Cancelled does not."""
        tz = timezone.get_current_timezone()
        slot_10am = timezone.make_aware(
            datetime.datetime.combine(self.target_date, datetime.time(10, 0)),
            tz
        )
        slot_11am = timezone.make_aware(
            datetime.datetime.combine(self.target_date, datetime.time(11, 0)),
            tz
        )
        slot_12pm = timezone.make_aware(
            datetime.datetime.combine(self.target_date, datetime.time(12, 0)),
            tz
        )

        # 10:00 is pending
        Appointment.objects.create(
            student=self.student,
            counselor=self.counselor_a,
            scheduled_at=slot_10am,
            status=AppointmentStatusChoices.PENDING,
            concern_type=ConcernTypeChoices.ACADEMIC
        )

        # 11:00 is confirmed
        Appointment.objects.create(
            student=self.student,
            counselor=self.counselor_a,
            scheduled_at=slot_11am,
            status=AppointmentStatusChoices.CONFIRMED,
            concern_type=ConcernTypeChoices.CAREER
        )

        # 12:00 was cancelled (should remain available)
        Appointment.objects.create(
            student=self.student,
            counselor=self.counselor_a,
            scheduled_at=slot_12pm,
            status=AppointmentStatusChoices.CANCELLED,
            concern_type=ConcernTypeChoices.PERSONAL
        )

        slots = get_available_slots_for_counselor(self.counselor_a, self.target_date)
        slot_map = {s['datetime'].hour: s['is_available'] for s in slots}

        self.assertFalse(slot_map[10], "Pending slot at 10:00 must be marked unavailable")
        self.assertFalse(slot_map[11], "Confirmed slot at 11:00 must be marked unavailable")
        self.assertTrue(slot_map[12], "Cancelled slot at 12:00 must remain available")
        self.assertTrue(slot_map[9], "Free slot at 09:00 must be available")

    def test_clash_window_conflict(self):
        """A booking within +/- 50 minutes of an existing booking triggers conflict."""
        tz = timezone.get_current_timezone()
        exact_slot = timezone.make_aware(
            datetime.datetime.combine(self.target_date, datetime.time(14, 0)),
            tz
        )

        Appointment.objects.create(
            student=self.student,
            counselor=self.counselor_a,
            scheduled_at=exact_slot,
            status=AppointmentStatusChoices.CONFIRMED,
            concern_type=ConcernTypeChoices.MENTAL_HEALTH
        )

        # 14:00 is taken
        self.assertFalse(is_counselor_slot_free(self.counselor_a, exact_slot))

        # 14:30 is within 50 minutes window -> not free
        clash_30m = exact_slot + datetime.timedelta(minutes=30)
        self.assertFalse(is_counselor_slot_free(self.counselor_a, clash_30m))

        # 15:00 is 60 minutes away -> free
        slot_next_hour = exact_slot + datetime.timedelta(hours=1)
        self.assertTrue(is_counselor_slot_free(self.counselor_a, slot_next_hour))

    def test_past_slot_is_not_free(self):
        """Slots in the past cannot be booked."""
        past_time = timezone.now() - datetime.timedelta(hours=2)
        self.assertFalse(is_counselor_slot_free(self.counselor_a, past_time))

    def test_get_first_available_counselor_slot_picks_alphabetically(self):
        """Picks the earliest free slot and the first counselor alphabetically (Aaron before Beth)."""
        tz = timezone.get_current_timezone()
        slot_9am = timezone.make_aware(
            datetime.datetime.combine(self.target_date, datetime.time(9, 0)),
            tz
        )

        # When both are free at 09:00, Dr. Aaron Adams should be picked first
        result = get_first_available_counselor_slot(self.target_date)
        self.assertIsNotNone(result)
        self.assertEqual(result['counselor'].id, self.counselor_a.id)
        self.assertEqual(result['slot'], slot_9am)

        # If Aaron is booked at 09:00, Dr. Beth Baker should be picked at 09:00
        Appointment.objects.create(
            student=self.student,
            counselor=self.counselor_a,
            scheduled_at=slot_9am,
            status=AppointmentStatusChoices.PENDING,
            concern_type=ConcernTypeChoices.ACADEMIC
        )

        result_after_aaron_booked = get_first_available_counselor_slot(self.target_date)
        self.assertIsNotNone(result_after_aaron_booked)
        self.assertEqual(result_after_aaron_booked['counselor'].id, self.counselor_b.id)
        self.assertEqual(result_after_aaron_booked['slot'], slot_9am)
