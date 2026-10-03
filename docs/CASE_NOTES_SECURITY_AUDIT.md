# CASE NOTES FEATURE — SECURITY AUDIT
**Step 6D Pre-Migration Security Analysis**  
**Date:** October 2, 2026  
**Baseline Tests:** 81/81 passing ✅

---

## SECURITY SUMMARY

Case Notes is a **SECURITY-CRITICAL FEATURE** containing sensitive clinical information.

### Current Implementation Assessment: ✅ SECURE

The existing implementation follows industry best practices for sensitive data handling.

---

## AUTHORIZATION MATRIX (RLS)

### WHO MAY CREATE NOTES?
- ✅ **Counselors ONLY** assigned to the appointment
- ❌ Students cannot create notes
- ❌ Receptionists cannot create notes
- ❌ Admins cannot create notes

**Enforcement:**
```python
# core/services/case_notes.py:save_case_note()
if counselor.role != RoleChoices.COUNSELOR:
    raise PermissionDenied("Only counselors are authorized to create or modify case notes.")

if appointment.counselor_id != counselor.id:
    raise PermissionDenied("Integrity error: You are not assigned to this appointment.")
```

### WHO MAY VIEW NOTES?

**Confidential Notes (`is_confidential=True`):**
- ✅ **Author counselor ONLY**
- ❌ Other counselors denied
- ❌ Students denied (even if it's their appointment)
- ❌ Admins denied

**Non-Confidential Notes (`is_confidential=False`):**
- ✅ **Author counselor** (full access)
- ✅ **Student** (if it's their own appointment)
- ✅ **Admin** (system oversight)
- ❌ Other counselors denied

**Enforcement:**
```python
# core/services/case_notes.py:get_decrypted_case_note()
is_author = (viewer.id == case_note.counselor_id)
is_admin = (viewer.role == RoleChoices.ADMIN)
is_own_student = (viewer.id == case_note.appointment.student_id)

if is_author:
    return decrypted_data  # Full access

if case_note.is_confidential:
    return None  # Confidential = author-only

if is_admin or is_own_student:
    return decrypted_data  # Non-confidential visible

return None  # All others denied
```

### WHO MAY EDIT NOTES?
- ✅ **Author counselor** (upsert pattern)
- ❌ All others denied

**Enforcement:**
- Same authorization as create
- `update_or_create()` constraint: `(appointment, counselor)` unique

### WHO MAY DELETE NOTES?
- ⚠️ **Not implemented** in current system
- Database constraint allows deletion but no view endpoint exists
- Migration MUST preserve this behavior (no delete functionality)

---

## ENCRYPTION ARCHITECTURE

### Algorithm & Key Management
- **Algorithm:** AES-256-CBC
- **Padding:** PKCS7
- **Key Size:** 32 bytes (256 bits)
- **IV:** 16 bytes random (generated per encrypt operation)
- **Key Source:** `settings.ENCRYPTION_KEY` (env var `ENCRYPTION_KEY`)
- **Format:** `<32 hex chars IV><hex ciphertext>`

**Service:** `core/services/encryption.py`

### Encryption Flow
```python
plaintext → UTF-8 encode → PKCS7 pad → AES-256-CBC encrypt → hex encode → DB
```

### Decryption Flow
```python
DB → hex decode → AES-256-CBC decrypt → PKCS7 unpad → UTF-8 decode → plaintext
```

### Legacy Format Support
- **Legacy:** `gc:v1:<iv>:<tag>:<ciphertext>` (AES-GCM)
- **Current:** `<iv><ciphertext>` (AES-CBC)
- Backward compatibility MUST be preserved

### Encryption Key Requirements
- ✅ Must be 64 hex characters (32 bytes decoded)
- ✅ Stored in environment variable
- ✅ Missing key raises `ValueError` (caught by views)
- ✅ Invalid key caught during encrypt/decrypt

---

## AUDIT LOGGING

### What is Logged?
1. **Case Note Creation/Update** (`CASE_NOTE_UPSERT`)
   - Who: counselor profile
   - What: created vs updated flag
   - Where: appointment_id, case_note id
   - When: timestamp
   - Confidentiality: is_confidential flag

2. **Case Note Deletion** (`CASE_NOTE_DELETED`)
   - Triggered by Django signal
   - Logged even if done via admin panel

**Audit Service:** `apps/audit/services/logging.py:log_action()`

### What is NOT Logged?
- ✅ **Case note content** (plaintext or ciphertext) — NOT logged
- ✅ **Decrypted content** — NOT logged
- ✅ **Encryption keys** — NOT logged
- ✅ **Student name in case note context** — Logged only via appointment_id reference

### Audit Signal
```python
# apps/audit/signals.py
@receiver(post_save, sender=CaseNote)
def audit_casenote_save(sender, instance, created, **kwargs):
    # Logs creation/update WITHOUT exposing content
```

---

## SENSITIVE DATA EXPOSURE RISKS

### ✅ PROTECTED SURFACES

1. **Database Storage**
   - Content stored as hex ciphertext
   - Plaintext NEVER in database
   - Test verification: `test_save_produces_non_plaintext_ciphertext_in_db`

2. **Audit Logs**
   - Content NOT logged
   - Only metadata logged (appointment_id, is_confidential)

3. **Error Messages**
   - Encryption failures return generic "Encryption failed"
   - NO key material in error messages
   - NO plaintext in error messages

4. **Templates**
   - Decrypted content rendered server-side only
   - NO JavaScript access to decryption keys
   - NO API exposing bulk case notes

5. **URLs**
   - No sensitive data in URL paths
   - Pattern: `/counselor/case-notes/<appointment_id>/`
   - Appointment ID is non-sensitive reference

6. **HTTP Responses**
   - Encrypted content NEVER sent to client
   - Only decrypted content displayed (server-rendered)

---

## TEST COVERAGE

### Existing Tests (test_case_notes.py)

1. ✅ **Encryption at Rest**
   - `test_save_produces_non_plaintext_ciphertext_in_db`
   - Verifies DB contains ciphertext, not plaintext

2. ✅ **Upsert Uniqueness**
   - `test_upsert_updates_same_row`
   - Verifies no duplicate notes per (appointment, counselor)

3. ✅ **Authorization Integrity**
   - `test_integrity_second_counselor_rejected`
   - Verifies unassigned counselor cannot create/read notes

4. ✅ **Confidentiality Matrix — Student**
   - `test_student_cannot_fetch_confidential_note`
   - Verifies students see non-confidential only

5. ✅ **Confidentiality Matrix — Admin**
   - `test_admin_read_rules`
   - Verifies admins see non-confidential only

6. ✅ **Legacy Format**
   - `test_legacy_gc_v1_decrypt_path`
   - Verifies AES-GCM backward compatibility

7. ✅ **Missing Key Handling**
   - `test_missing_encryption_key_handling`
   - Verifies ValueError raised when key missing

**Coverage: COMPREHENSIVE ✅**

---

## CURRENT FILE LOCATIONS

### Services
- `core/services/case_notes.py` → `apps/case_notes/services/case_notes.py`
- `core/services/encryption.py` → `apps/case_notes/services/encryption.py`

### Views
- `core/views/counselor.py:counselor_case_note_view` → `apps/case_notes/views.py`

### Forms
- `core/forms.py:CaseNoteForm` → `apps/case_notes/forms.py`

### Templates
- `templates/counselor/case_note.html` → `apps/case_notes/templates/case_notes/editor.html`

### Tests
- `tests/test_case_notes.py` → `apps/case_notes/tests.py`

### URLs
- `core/urls.py` (case_note pattern) → `apps/case_notes/urls.py`

### Models
- `core/models.py:CaseNote` → **STAYS in core/models.py** (no model migration)

---

## DEPENDENCIES & IMPORTS

### Services Used By
- `core/views/counselor.py` — case note editor view
- `core/views/student.py` — dashboard shows non-confidential notes
- `tests/test_case_notes.py` — test suite
- `apps/common/management/commands/seed_roles.py` — seed data

### Services Dependencies
- `core/models` — Appointment, CaseNote, Profile
- `apps/common.choices` — RoleChoices
- `apps/audit.services.logging` — log_action()
- `django.conf.settings` — ENCRYPTION_KEY
- `cryptography` — AES encryption

### View Dependencies
- `apps/authentication.guards` — @require_counselor
- `core/services/case_notes` — save/decrypt services
- `core/forms` — CaseNoteForm

---

## MIGRATION SAFETY CHECKLIST

### ✅ MUST PRESERVE
1. **Encryption algorithm** — AES-256-CBC (do not change)
2. **Key source** — settings.ENCRYPTION_KEY
3. **Ciphertext format** — `<iv><ciphertext>` hex string
4. **Legacy format support** — gc:v1: AES-GCM decrypt
5. **Authorization matrix** — All RLS rules
6. **Audit logging** — All logged events
7. **Unique constraint** — (appointment, counselor)
8. **Test coverage** — All 7 tests must pass

### ✅ MUST NOT EXPOSE
1. Plaintext case note content in logs
2. Encryption keys in error messages
3. Decrypted content in audit logs
4. Ciphertext in URLs
5. Bulk case note APIs (no list endpoint)

### ✅ MUST VERIFY AFTER MIGRATION
1. All 81+ tests passing
2. Encryption service still works with test key
3. Authorization guards still enforce RLS
4. Audit signals still trigger
5. Legacy format still decrypts
6. Student dashboard still shows non-confidential notes
7. Counselor workspace still links to case note editor

---

## SECURITY RECOMMENDATIONS

### ✅ CURRENT STRENGTHS
1. Strong encryption (AES-256)
2. Comprehensive RLS enforcement
3. No sensitive data leakage
4. Audit logging without content exposure
5. Backward compatibility for legacy data
6. Comprehensive test coverage

### ⚠️ MINOR IMPROVEMENTS (FUTURE)
1. Consider key rotation mechanism (not in scope for migration)
2. Consider adding delete audit requirement (currently handled by signal)
3. Consider rate limiting on case note access (prevent brute force attempts)

### 🛑 CRITICAL: DO NOT
1. Do NOT weaken authorization checks
2. Do NOT expose decryption service as API endpoint
3. Do NOT log decrypted content
4. Do NOT change encryption algorithm without data migration plan
5. Do NOT remove unique constraint on (appointment, counselor)

---

## CONCLUSION

**Security Assessment: ✅ PRODUCTION-READY**

The current Case Notes implementation is secure and follows best practices:
- Defense in depth (encryption + authorization + audit)
- Principle of least privilege (role-based access)
- Secure by default (confidential flag)
- No sensitive data leakage

**Migration Clearance: ✅ APPROVED**

The feature can be safely migrated to `apps/case_notes/` provided:
1. All security checks are preserved
2. All tests remain passing
3. No authorization logic is weakened
4. Encryption mechanism is unchanged

**Next Step:** Execute Step 6D migration following OFFICIAL_SYSTEM_STANDARD.md

---

**END OF SECURITY AUDIT**
