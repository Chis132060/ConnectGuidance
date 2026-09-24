"""
tests/test_case_notes.py — Tests for Case Notes: AES-256 encryption at rest, upsert uniqueness,
counselor assignment integrity, RLS confidentiality matrix, and legacy format decrypt.
"""

import os
import binascii
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError

from core.models import Profile, Appointment, CaseNote, AuditLog
from core.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
from core.services.case_notes import save_case_note, get_decrypted_case_note
from core.services.encryption import encrypt_text, decrypt_text

TEST_HEX_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


@override_settings(ENCRYPTION_KEY=TEST_HEX_KEY)
class CaseNotesTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Assigned Counselor
        self.counselor_user = User.objects.create_user(
            username='counselor1@test.edu',
            email='counselor1@test.edu',
            password='TestPassword123!',
        )
        self.counselor = self.counselor_user.profile
        self.counselor.role = RoleChoices.COUNSELOR
        self.counselor.is_active = True
        self.counselor.full_name = 'Dr. Primary Counselor'
        self.counselor.save()

        # Unassigned Counselor
        self.other_counselor_user = User.objects.create_user(
            username='counselor2@test.edu',
            email='counselor2@test.edu',
            password='TestPassword123!',
        )
        self.other_counselor = self.other_counselor_user.profile
        self.other_counselor.role = RoleChoices.COUNSELOR
        self.other_counselor.is_active = True
        self.other_counselor.full_name = 'Dr. Other Counselor'
        self.other_counselor.save()

        # Student
        self.student_user = User.objects.create_user(
            username='student@test.edu',
            email='student@test.edu',
            password='TestPassword123!',
        )
        self.student = self.student_user.profile
        self.student.role = RoleChoices.STUDENT
        self.student.is_active = True
        self.student.full_name = 'Alex Student'
        self.student.save()

        # Admin
        self.admin_user = User.objects.create_user(
            username='admin@test.edu',
            email='admin@test.edu',
            password='TestPassword123!',
        )
        self.admin = self.admin_user.profile
        self.admin.role = RoleChoices.ADMIN
        self.admin.is_active = True
        self.admin.full_name = 'Chief Admin'
        self.admin.save()

        # Appointment assigned to counselor
        self.appointment = Appointment.objects.create(
            student=self.student,
            counselor=self.counselor,
            scheduled_at=timezone.now(),
            status=AppointmentStatusChoices.CONFIRMED,
            concern_type=ConcernTypeChoices.ACADEMIC
        )

    def test_save_produces_non_plaintext_ciphertext_in_db(self):
        """Content stored in CaseNote.content must be encrypted ciphertext, never plaintext."""
        plaintext = "Patient exhibits signs of moderate academic burnout. Follow up next week."
        note = save_case_note(
            appointment=self.appointment,
            counselor=self.counselor,
            raw_content=plaintext,
            is_confidential=False
        )

        # Reload directly from DB
        db_note = CaseNote.objects.get(id=note.id)
        self.assertNotEqual(db_note.content, plaintext)
        self.assertNotIn(plaintext, db_note.content)
        # Should be valid hex string
        self.assertTrue(all(c in '0123456789abcdefABCDEF' for c in db_note.content))

        # Author can decrypt back to exact plaintext
        data = get_decrypted_case_note(db_note, self.counselor)
        self.assertIsNotNone(data)
        self.assertEqual(data['content'], plaintext)

        # Audit log verification (record_id is stored as UUID, not raw int)
        audit = AuditLog.objects.filter(action="CASE_NOTE_UPSERT").order_by('-created_at').first()
        self.assertIsNotNone(audit)

    def test_upsert_updates_same_row(self):
        """Repeated saves on same (appointment, counselor) update the row without duplicating."""
        first_text = "First clinical impression."
        note1 = save_case_note(self.appointment, self.counselor, first_text, is_confidential=False)

        second_text = "Updated clinical impression with revised treatment goals."
        note2 = save_case_note(self.appointment, self.counselor, second_text, is_confidential=True)

        self.assertEqual(note1.id, note2.id)
        self.assertEqual(CaseNote.objects.filter(appointment=self.appointment).count(), 1)

        db_note = CaseNote.objects.get(id=note1.id)
        self.assertTrue(db_note.is_confidential)
        data = get_decrypted_case_note(db_note, self.counselor)
        self.assertEqual(data['content'], second_text)

    def test_integrity_second_counselor_rejected(self):
        """A counselor not assigned to the appointment cannot save or decrypt notes."""
        with self.assertRaises(PermissionDenied):
            save_case_note(
                appointment=self.appointment,
                counselor=self.other_counselor,
                raw_content="Unauthorized clinical note"
            )

        # Even if a note exists by the author, second counselor cannot read it
        note = save_case_note(self.appointment, self.counselor, "Authorized note", is_confidential=False)
        result = get_decrypted_case_note(note, self.other_counselor)
        self.assertIsNone(result)

    def test_student_cannot_fetch_confidential_note(self):
        """Students can decrypt non-confidential notes from their own appointment, but NOT confidential ones."""
        # 1. Non-confidential note -> readable by own student
        note_shared = save_case_note(self.appointment, self.counselor, "Shared advice for student", is_confidential=False)
        shared_data = get_decrypted_case_note(note_shared, self.student)
        self.assertIsNotNone(shared_data)
        self.assertEqual(shared_data['content'], "Shared advice for student")

        # 2. Confidential note -> hidden from student
        note_confidential = save_case_note(self.appointment, self.counselor, "Strictly private counselor observation", is_confidential=True)
        conf_data = get_decrypted_case_note(note_confidential, self.student)
        self.assertIsNone(conf_data)

    def test_admin_read_rules(self):
        """Admin can decrypt non-confidential notes, but is denied decrypt on confidential notes."""
        # Non-confidential -> Admin OK
        note_public = save_case_note(self.appointment, self.counselor, "Administrative session summary", is_confidential=False)
        admin_data = get_decrypted_case_note(note_public, self.admin)
        self.assertIsNotNone(admin_data)
        self.assertEqual(admin_data['content'], "Administrative session summary")

        # Confidential -> Admin denied
        note_private = save_case_note(self.appointment, self.counselor, "Private diagnostic note", is_confidential=True)
        admin_private = get_decrypted_case_note(note_private, self.admin)
        self.assertIsNone(admin_private)

    def test_legacy_gc_v1_decrypt_path(self):
        """Tests decryption of legacy gc:v1:<iv>:<tag>:<ciphertext> GCM format."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        key_bytes = binascii.unhexlify(TEST_HEX_KEY)
        iv = os.urandom(12)
        plaintext = "Legacy note content from previous version."

        cipher = Cipher(algorithms.AES(key_bytes), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()
        tag = encryptor.tag

        legacy_payload = f"gc:v1:{binascii.hexlify(iv).decode('ascii')}:{binascii.hexlify(tag).decode('ascii')}:{binascii.hexlify(ciphertext).decode('ascii')}"

        decrypted = decrypt_text(legacy_payload)
        self.assertEqual(decrypted, plaintext)

    @override_settings(ENCRYPTION_KEY='')
    def test_missing_encryption_key_handling(self):
        """When ENCRYPTION_KEY is missing, saving throws ValueError which the view catches."""
        with self.assertRaises(ValueError) as ctx:
            save_case_note(self.appointment, self.counselor, "Will fail encryption")
        self.assertIn("ENCRYPTION_KEY", str(ctx.exception))
