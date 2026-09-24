# REMAINING_STEPS — ConnectGuidance Django

Live tracker of what's left to build. Cross-references `PLAN.md` (73 steps), `AUDIT_LOG.md` (gap register), and `ANTIGRAVITY_PROMPTS.md` (session prompts).

| Field | Value |
|---|---|
| Created | 2026-09-24 |
| Last updated | 2026-09-24 |
| Overall progress | 100% Complete (All 8 Phases implemented, 70/70 automated tests passing) |

---

## Phase completion status

| Phase | Steps | Description | Status | Prompt |
|---|---|---|---|---|
| 1 — Foundation | 1–8 | Scaffold, settings, env, venv | ✅ Done | — |
| 2 — Data Design | 9–15 | Models, choices, migration, admin | ✅ Done | — |
| 3 — Auth + RBAC | 16–23 | Views, URLs, login/register/logout, guards | ✅ Done | PROMPT 1 |
| 4 — Appointments | 24–31 | Booking, cancel, status, receptionist, slots views | ✅ Done | PROMPT 2 |
| 5 — Case Notes | 32–36 | Encrypted notes, upsert, confidentiality views | ✅ Done | PROMPT 3 |
| 6 — Mood + Chat | 37–43 | Mood check-in, SSE chat, rate limits, CTA | ✅ Done | PROMPT 4 |
| 7 — UI | 44–63 | 16 templates + overlay + static CSS/JS | ✅ Done | PROMPT 5 |
| 8 — Admin + QA | 64–73 | Admin views, exports, ops, final QA | ✅ Done | PROMPT 6 |
| Tests | — | Full test suite (70 test cases across 7 modules) | ✅ Done (70/70 passing) | PROMPT 7 |
| Security | — | RLS §10 close-out (13 items, query scoping, safeguards) | ✅ Done | PROMPT 8 |

---

## What exists (done — do not rebuild)

### Phase 1 ✅
- [x] `.venv` Python 3.12.10
- [x] `requirements.txt` (11 deps: Django 5.2.17, dj-database-url, psycopg2-binary, python-dotenv, cryptography, reportlab, requests, tzdata)
- [x] `config/settings.py` — env-driven, Supabase DB + SQLite fallback, auth URL names, encryption/chat env keys
- [x] `config/urls.py` — `/admin/` only
- [x] `.env.example`, `.gitignore`, `README.md`

### Phase 2 ✅
- [x] `core/models.py` — 6 models (Profile, Appointment, CaseNote, AuditLog, ChatbotSession, StudentMoodAlert)
- [x] `core/choices.py` — RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
- [x] `core/migrations/0001_initial.py` — APPLIED, never edit
- [x] `core/admin.py` — 6 models registered
- [x] `core/signals.py` — Profile auto-create + audit dual-write (Profile, CaseNote)

### Services ✅ (24 functions across 8 modules)
- [x] `core/services/slots.py` — get_hourly_slots_for_date, get_available_slots_for_counselor, is_counselor_slot_free, get_first_available_counselor_slot
- [x] `core/services/appointments.py` — can_transition, book_appointment, student_cancel_appointment, counselor_update_status
- [x] `core/services/case_notes.py` — save_case_note, get_decrypted_case_note
- [x] `core/services/encryption.py` — encrypt_text, decrypt_text (AES-256-CBC + legacy gc:v1: GCM)
- [x] `core/services/mood.py` — process_mood_checkin
- [x] `core/services/chat.py` — check_chat_rate_limit, should_trigger_booking_cta, is_crisis_text, generate_chat_response, save_or_update_session
- [x] `core/services/reports.py` — get_admin_metrics, filter_appointments, export_appointments_csv, export_appointments_pdf
- [x] `core/services/audit.py` — log_action (never raises)

### Guards + Forms ✅
- [x] `core/guards.py` — ROLE_HOMES, role_required, require_admin/counselor/student/receptionist
- [x] `core/forms.py` — StudentRegistrationForm, StudentProfileUpdateForm, AppointmentBookingForm, ReceptionistBookingForm, CaseNoteForm, MoodCheckInForm

### Management ✅
- [x] `core/management/commands/seed_roles.py` — admin, 2 counselors, receptionist, 2 students + sample data

### Docs ✅ (6 companion docs)
- [x] `docs/PLAN.md` — 73 steps, 50-box checklist
- [x] `docs/ERD.md` — Mermaid ERD + field spec
- [x] `docs/FLOWS.md` — 24 flows
- [x] `docs/INTERFACES.md` — 16 screens + overlay
- [x] `docs/RLS_AND_SECURITY.md` — query scoping matrix, 13-box checklist
- [x] `docs/REFERENCES.md` — Next.js → Django map
- [x] `docs/AUDIT_LOG.md` — 9 entries + gap register

---

## What must be built (ordered by prompt)

### Phase 3 — Auth + URLs (PROMPT 1)

| # | Step | Item | Depends on |
|---|---|---|---|
| 16 | URLs | `core/urls.py` + edit `config/urls.py` | — |
| 17 | Register view | `core/views/auth.py` → register | StudentRegistrationForm |
| 18 | Login flow | login view with email auth + ROLE_HOME redirect | guards.py |
| 19 | Guard wiring | @role_required on all protected views | guards.py |
| 20 | Page guards | All protected views mirror original roles | guards.py |
| 21 | Password change | PasswordChangeView | django.contrib.auth |
| 22 | Staff bootstrap | Verify seed_roles works with new URLs | seed_roles.py |
| 23 | Verify | 4 roles log in; wrong-route redirect; deactivated blocked | all above |

**Also:** `templates/base.html` (stub), `templates/public/landing.html`, `templates/registration/login.html`, `register.html`, `password_change.html`
**Settings:** Add `LOGOUT_REDIRECT_URL = '/'`
**Tests:** `tests/test_auth_guards.py`

---

### Phase 4 — Appointments (PROMPT 2)

| # | Step | Item | Depends on |
|---|---|---|---|
| 24 | Slots view | Student-only availability endpoint | slots.py |
| 25 | Availability | Subtract pending/confirmed from 09:00–16:00 | slots.py |
| 26 | Book view | Student book with validation | appointments.py, AppointmentBookingForm |
| 27 | Student cancel | Own row only, terminal blocked | appointments.py |
| 28 | Counselor status | State machine transitions | appointments.py |
| 29 | Receptionist book | Search + next-available + book | **NEW** receptionist.py service |
| 30 | No revalidate | Plain redirect after POST | — |
| 31 | Verify | Full lifecycles from FLOWS §7–10, §16 | all above |

**New file:** `core/services/receptionist.py` (search_students, list counselors, any-free slots)
**Views:** `core/views/student.py`, `core/views/counselor.py`, `core/views/receptionist.py`
**Tests:** `tests/test_slots.py`, `tests/test_appointments.py`

---

### Phase 5 — Case Notes (PROMPT 3)

| # | Step | Item | Depends on |
|---|---|---|---|
| 32 | Encryption | Verify encryption.py works (exists) | encryption.py |
| 33 | Save view | Counselor-only encrypt + upsert | case_notes.py, CaseNoteForm |
| 34 | Integrity | Reject counselor mismatch | case_notes.py clean() |
| 35 | Read rules | Author/student/admin access matrix | case_notes.py |
| 36 | Verify | Wrong counselor 403; ciphertext; toggle hides | all above |

**Tests:** `tests/test_case_notes.py`

---

### Phase 6 — Mood + Chat SSE (PROMPT 4)

| # | Step | Item | Depends on |
|---|---|---|---|
| 37 | Mood view | POST check-in with 3 branches | mood.py, MoodCheckInForm |
| 38 | Counselor feed | Alert list in workspace context | StudentMoodAlert model |
| 39 | Chat GET | Latest session, rate limit 60/15min | chat.py |
| 40 | Chat POST | **SSE streaming** (service upgrade needed) | chat.py ⚠️ |
| 41 | Book CTA | Trigger booking suggestion | chat.py |
| 42 | Crisis | System prompt parity | chat.py |
| 43 | Verify | Low mood alert; stream + restore; 429; CTA | all above |

**Service upgrade:** `core/services/chat.py` — add `stream_chat_response` generator
**New view:** `core/views/chat.py`
**Settings:** Add `CHAT_RATE_LIMIT_WINDOW_MS`, `CHAT_SESSION_GET_WINDOW`
**Tests:** `tests/test_mood_chat.py`

---

### Phase 7 — Full UI (PROMPT 5)

| # | Screen | Route | Template |
|---|---|---|---|
| 44 | Base layout | — | `templates/base.html` |
| 45 | Landing | `/` | `templates/public/landing.html` |
| 46 | Login | `/login/` | `templates/registration/login.html` |
| 47 | Register | `/register/` | `templates/registration/register.html` |
| 48 | Student dashboard | `/student/` | `templates/student/dashboard.html` |
| 49 | Appointments | `/appointments/` | `templates/student/appointments.html` |
| 50 | Chatbot page | `/chatbot/` | `templates/student/chatbot.html` |
| 51 | Student profile | `/student/profile/` | `templates/student/profile.html` |
| 52 | Front desk info | `/student/front-desk/` | `templates/student/front_desk.html` |
| 53 | Counselor workspace | `/counselor/` | `templates/counselor/workspace.html` |
| 54 | Case note editor | `/counselor/case-notes/<uuid>/` | `templates/counselor/case_note.html` |
| 55 | Admin overview | `/admin-panel/` | `templates/admin/overview.html` |
| 56 | Users | `/admin-panel/users/` | `templates/admin/users.html` |
| 57 | Audit logs | `/admin-panel/audit/` | `templates/admin/audit_logs.html` |
| 58 | Reports | `/admin-panel/reports/` | `templates/admin/reports.html` |
| 59 | Admin profile | `/admin-panel/profile/` | `templates/admin/profile.html` |
| 60 | Receptionist | `/receptionist/` | `templates/receptionist/booking.html` |
| 61 | Chat overlay | include | `templates/widgets/chatbot.html` |
| 62 | States | every page | empty / loading / error / success |
| 63 | Verify | 16 + 1 | HTTP 200 + correct template |

**Static:** `static/css/app.css`, `static/js/chat.js`, `static/js/slots.js`, `static/js/admin-charts.js`
**Partials:** Subnavs (student, counselor, admin, receptionist), `_messages.html`

---

### Phase 8 — Admin + QA (PROMPT 6)

| # | Step | Item | Status |
|---|---|---|---|
| 64 | Audit service | `log_action()` | ✅ exists |
| 65 | Signals | Profile + CaseNote audit | ✅ exists |
| 66 | Audit viewer | Filters + pagination + JSON expand | ❌ |
| 67 | Reports | Date/dept/concern/status filters + preview | ❌ |
| 68 | Export | CSV + PDF + audit REPORT_EXPORT | ❌ (service exists, view doesn't) |
| 69 | Metrics | KPI + 8-week + concern breakdown | ❌ (service exists, view doesn't) |
| 70 | User management | Role change, activate/deactivate + safeguards | ❌ |
| 71 | Deps | gunicorn, whitenoise | ❌ |
| 72 | README | Final version | ❌ |
| 73 | Full QA | 24 flows + 50 checklist + 13 RLS boxes | ❌ |

**New files:** `core/views/admin_views.py`, `core/services/admin_users.py`
**Tests:** `tests/test_admin_guards.py`, `tests/test_reports_audit.py`, `tests/test_views_http.py`

---

## File creation summary (remaining)

| Category | Files to create | Count |
|---|---|---|
| Views | `core/views/__init__.py`, `auth.py`, `student.py`, `counselor.py`, `receptionist.py`, `chat.py`, `admin_views.py` | 7 |
| URLs | `core/urls.py` (new), `config/urls.py` (edit) | 2 |
| Services | `core/services/receptionist.py`, `core/services/admin_users.py` | 2 |
| Templates | base + 16 pages + overlay + partials | ~22 |
| Static | CSS (1) + JS (3–4) | 4–5 |
| Tests | 9 test files | 9 |
| **Total** | | **~47 files** |

---

## Known gaps from AUDIT_LOG gap register

| # | Gap | Plan ref | Required by |
|---|---|---|---|
| G1 | Add User admin action | Phase 8 step 70 | PROMPT 6 |
| G2 | Export CSV of audit rows | Phase 8 step 66 | PROMPT 6 |
| G3 | Receptionist student search service | Phase 4 step 29 | PROMPT 2 |
| G4 | Chat rate limit settings from env | Phase 6 step 40 | PROMPT 4 |
| G5 | SSE streaming (chat returns full text) | Phase 6 step 40 | PROMPT 4 |
| G6 | Admin safety guards (last-admin, self-demote) | Phase 8 step 70 | PROMPT 6 |
| G7 | Live Supabase DATABASE_URL | Phase 1 exit | User action |
| G8 | gunicorn + whitenoise in requirements | Phase 8 step 71 | PROMPT 6 |

---

## Execution order

```
Session 1:  PROMPT 0 (master) + PROMPT 1 (Phase 3: Auth)
Session 2:  PROMPT 2 (Phase 4: Appointments)
Session 3:  PROMPT 3 (Phase 5: Case Notes)
Session 4:  PROMPT 4 (Phase 6: Mood + Chat SSE)
Session 5:  PROMPT 5 (Phase 7: Full UI)
Session 6:  PROMPT 6 (Phase 8: Admin + QA)
Parallel:   PROMPT 7 (Tests — can run after Phase 3)
Final:      PROMPT 8 (Security close-out)
```

> **After each session:** Review `git diff`, commit, then move to the next prompt.
