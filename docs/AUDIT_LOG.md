# AUDIT_LOG — ConnectGuidance Django Project Change Log

Master record of **every creation and change** made in this repository, reconstructed from git history and file timestamps.

| Field | Value |
|---|---|
| Project | ConnectGuidance Django (replica of GuidanceConnect) |
| Log created | 2026-09-24 |
| Maintained by | Project owner — append a new entry for every meaningful change |
| Source of truth | `git log` + file system timestamps |

**Entry format:** date · what changed · files touched · phase mapped to `docs/PLAN.md` · verification status.

---

## Summary dashboard

| Metric | Value |
|---|---|
| Git commits | 2 |
| Total files created (tracked) | 53 (+ `.gitignore`, `manage.py` in commit 1) |
| Total lines added (both commits) | ~6,700 |
| Custom app | `core` (1 app) |
| Models | 6 |
| Service modules | 9 (`slots`, `appointments`, `audit`, `receptionist`, `case_notes`, `mood`, `chat`, `reports`, `encryption`) |
| Forms | 6 |
| Tests | 5 test files (`test_auth_guards.py`, `test_slots.py`, `test_appointments.py`, `test_case_notes.py`, `test_mood_chat.py`) |
| Views / templates | 20 views (auth, student, counselor, receptionist, chat) / 11 templates |
| Current DB | SQLite fallback (`db.sqlite3`); Supabase URI not yet live |
| Working tree at log creation | modified (Phases 3, 4, 5, 6 files added) |

---

## Timeline of all changes

### Entry 001 — Project scaffold (Phase 1 — Foundation)

| Field | Value |
|---|---|
| Date | 2026-09-22 22:57 (file mtimes) |
| Commit | `b612711` — *Initial commit: Django project foundation with Supabase PostgreSQL config* |
| Committed | 2026-09-24 09:03 +0800 |
| Author | Chis132060 \<tvraps261@gmail.com\> |
| Phase | PLAN Phase 1 (steps 1–8) |

**Created:**

| File | Purpose |
|---|---|
| `manage.py` | Django CLI entrypoint |
| `config/__init__.py` | Project package |
| `config/settings.py` | Settings: env-driven `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS`, `dj_database_url` with Supabase URI + SQLite fallback, password validators, static config, auth URL names, encryption/chat env keys |
| `config/urls.py` | Root URLconf — currently only `admin/` |
| `config/asgi.py` | ASGI entrypoint |
| `config/wsgi.py` | WSGI entrypoint |
| `requirements.txt` | Initial deps (Django, dj-database-url, python-dotenv, psycopg2-binary, …) |
| `.env.example` | Env template (`DJANGO_*`, `DATABASE_URL` / DB_* Supabase placeholders) |
| `.gitignore` | Ignores `.env`, `.venv/`, `__pycache__`, `db.sqlite3`, `staticfiles/` |
| `README.md` | Setup, Supabase connection, run/check/migrate commands |

**Stats:** 10 files · +299 / −68 lines.

**Verify:** `python manage.py check` → 0 issues (re-confirmed 2026-09-24).

---

### Entry 002 — Planning & specification docs

| Field | Value |
|---|---|
| Date | 2026-09-24 ~09:36–09:39 |
| Commit | included in `5ab1601` (below) |
| Phase | Pre-Phase 1 / companion docs |

**Created:**

| File | Lines (approx) | Purpose |
|---|---|---|
| `docs/PLAN.md` | 288 | Master plan: 8 phases, 73 steps, no-missing-parts checklist |
| `docs/ERD.md` | 279 | Mermaid ERD + field-for-field Django model spec (source: original Supabase migrations) |
| `docs/FLOWS.md` | 496 | 24 mermaid system flowcharts |
| `docs/INTERFACES.md` | 176 | 16 screens + chat overlay, routes, design tokens |
| `docs/RLS_AND_SECURITY.md` | 176 | Supabase RLS → Django query-scoping/guards port, encryption, rate limits, admin guards, security checklist |
| `docs/REFERENCES.md` | 126 | Map of original Next.js files → Django targets |
| `README.md` | updated | Expanded with docs index, venv, Supabase setup, roadmap |
| `.env.example` | updated | Added `ENCRYPTION_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, chat limit vars |
| `AGENTS.md` | 27 | AI engineering persona/instructions for this repo |

---

### Entry 003 — Core app: models, enums, migration (Phase 2 — Data design)

| Field | Value |
|---|---|
| Date | 2026-09-24 12:47–12:53 |
| Commit | `5ab1601` |
| Phase | PLAN Phase 2 (steps 9–15) |

**Created:**

| File | Lines | Contents |
|---|---|---|
| `core/__init__.py` | 1 | App package |
| `core/apps.py` | 6 | App config |
| `core/choices.py` | 20 | `RoleChoices`, `AppointmentStatusChoices`, `ConcernTypeChoices` |
| `core/models.py` | 185 | **6 models:** `Profile`, `Appointment`, `CaseNote`, `AuditLog`, `ChatbotSession`, `StudentMoodAlert` — FK rules (PROTECT/CASCADE/SET_NULL), unique constraints, indexes, `clean()` integrity |
| `core/migrations/0001_initial.py` | 155 | Initial schema for all 6 models |
| `core/migrations/__init__.py` | 0 | Package |

**Verify:** `migrate` applied — `showmigrations` all `[X]` (incl. `core 0001_initial`). Local `db.sqlite3` created (278 KB, gitignored).

---

### Entry 004 — Admin site + audit signals

| Field | Value |
|---|---|
| Date | 2026-09-24 12:48 |
| Commit | `5ab1601` |
| Phase | PLAN Phase 8 (partial — steps 64–65) + Phase 2 polish |

**Created:**

| File | Lines | Contents |
|---|---|---|
| `core/admin.py` | 34 | Registers all 6 models with `list_display`, filters, search, readonly fields |
| `core/signals.py` | 78 | 4 receivers: auto-create `Profile` on User save; audit dual-write on Profile + CaseNote (never breaks transaction) |

**Verify:** `/admin/` reachable; signal receivers loaded via app ready.

---

### Entry 005 — Business logic services (Phases 4–6, 8 logic)

| Field | Value |
|---|---|
| Date | 2026-09-24 13:33–13:35 |
| Commit | `5ab1601` |
| Phase | PLAN Phases 4, 5, 6, 8 — **service layer only; no views yet** |

**Created:**

| File | Lines | Functions |
|---|---|---|
| `core/services/__init__.py` | 1 | Package |
| `core/services/encryption.py` | 67 | `_get_encryption_key`, `encrypt_text`, `decrypt_text` (AES-256-CBC + legacy `gc:v1:` GCM) |
| `core/services/slots.py` | 104 | `get_hourly_slots_for_date`, `get_available_slots_for_counselor`, `is_counselor_slot_free`, `get_first_available_counselor_slot` (09:00–16:00, ±50 min clash) |
| `core/services/appointments.py` | 121 | `can_transition`, `book_appointment`, `student_cancel_appointment`, `counselor_update_status` (state machine + audit) |
| `core/services/audit.py` | 37 | `log_action` — never raises |
| `core/services/case_notes.py` | 82 | `save_case_note`, `get_decrypted_case_note` (encrypt-on-save, confidentiality matrix) |
| `core/services/mood.py` | 74 | `process_mood_checkin` (good/okay → audit; low → `StudentMoodAlert`) |
| `core/services/chat.py` | 112 | `check_chat_rate_limit`, `should_trigger_booking_cta`, `is_crisis_text`, `generate_chat_response`, `save_or_update_session` (24/15 min limit, 36-msg cap, Groq + fallback) |
| `core/services/reports.py` | 159 | `get_admin_metrics`, `filter_appointments`, `export_appointments_csv`, `export_appointments_pdf` (ReportLab) |

**Total:** 8 modules · 24 functions.

**Known gaps noted at audit time:** chat returns full text (not SSE stream per step 40); admin safety guards (step 70) not found as a discrete service.

---

### Entry 006 — RBAC guards + forms + seed command

| Field | Value |
|---|---|
| Date | 2026-09-24 13:33–13:35 |
| Commit | `5ab1601` |
| Phase | PLAN Phase 3 (partial — steps 19, 22 logic only; **no auth views/URLs**) |

**Created:**

| File | Lines | Contents |
|---|---|---|
| `core/guards.py` | 50 | `ROLE_HOMES`, `get_role_home`, `get_profile_or_none`, `role_required` (+ role helpers) — deactivated → logout, wrong role → redirect home |
| `core/forms.py` | 174 | `StudentRegistrationForm`, `StudentProfileUpdateForm`, `AppointmentBookingForm`, `ReceptionistBookingForm`, `CaseNoteForm`, `MoodCheckInForm` |
| `core/management/__init__.py` | 1 | Package |
| `core/management/commands/__init__.py` | 1 | Package |
| `core/management/commands/seed_roles.py` | 155 | Seeds admin, 2 counselors, receptionist, 2 students + sample appointments + encrypted case note |

**Status:** all unwired — no view imports these yet.

---

### Entry 007 — Dependency & settings updates

| Field | Value |
|---|---|
| Date | 2026-09-24 12:44–13:24 |
| Commit | `5ab1601` |
| Phase | Phases 1 + 5 + 6 support |

**Changed:**

| File | Change |
|---|---|
| `requirements.txt` | Grew 7 → 11 deps: added `cryptography`, `reportlab`, `requests`, `tzdata` (now: Django 5.2.17, dj-database-url, psycopg2-binary, python-dotenv, …) |
| `config/settings.py` | Hardened DB fallback logic (rejects placeholder Supabase host/password → SQLite); `conn_max_age=600` + `sslmode=require` when on Postgres; chat/encryption env wiring |
| `.env` (local, gitignored) | Created 12:44 — placeholders only; **no real Supabase URI yet** |

---

### Entry 008 — “first commit” (bulk commit of Phases 1–2 + service layer)

| Field | Value |
|---|---|
| Commit | `5ab1601` — *first commit* |
| Committed | 2026-09-24 14:07 +0800 |
| Author | Chis132060 \<tvraps261@gmail.com\> |
| Contents | Entries 002–007 above (docs + entire `core/` app + README/AGENTS/settings updates) |
| Stats | 33 files · +3,524 / −68 lines |

---

### Entry 009 — Project completeness audit + this log

| Field | Value |
|---|---|
| Date | 2026-09-24 (session) |
| Commit | uncommitted at time of writing |
| Action | Full-codebase completion analysis (backend ~85–90%, UI/HTTP/tests 0%, overall ~30–35% of 73-step plan); **created `docs/AUDIT_LOG.md`** |
| Files | `docs/AUDIT_LOG.md` (new) |

---

### Entry 010 — Authentication views, URL routing, role guards, templates & tests (Phase 3)

| Field | Value |
|---|---|
| Date | 2026-09-24 |
| Commit | uncommitted |
| Phase | PLAN Phase 3 (steps 16–23) |

**Created / Modified:**

| File | Status | Purpose |
|---|---|---|
| `core/views/__init__.py` | Created | Package initializer for domain-organized views |
| `core/views/auth.py` | Created | Views for landing, login, logout, register, password_change, role_home |
| `core/urls.py` | Created | Named routes (`landing`, `login`, `logout`, `register`, `password_change`, `role_home`) |
| `config/urls.py` | Modified | Wired `core.urls` into root URLconf |
| `config/settings.py` | Modified | Updated `LOGOUT_REDIRECT_URL = '/'` per FLOWS §4 |
| `templates/base.html` | Created | Base template with message toasts, viewport meta, typography |
| `templates/public/landing.html` | Created | Landing page with hero, role cards, CTAs |
| `templates/registration/login.html` | Created | Email/password sign-in form with error query params & ?next= support |
| `templates/registration/register.html` | Created | Student registration form with validation and styling |
| `templates/registration/password_change.html` | Created | Password change form |
| `tests/__init__.py` | Created | Tests package initializer |
| `tests/test_auth_guards.py` | Created | Comprehensive tests: registration, login, logout, role_home, deactivated guard, role guards |

---

### Entry 011 — Appointments: views, state machine, receptionist booking, templates & tests (Phase 4)

| Field | Value |
|---|---|
| Date | 2026-09-24 |
| Commit | uncommitted |
| Phase | PLAN Phase 4 (steps 24–31) |

**Created / Modified:**

| File | Status | Purpose |
|---|---|---|
| `core/services/receptionist.py` | Created | Discrete receptionist service: student search (limit 25), counselor roster A-Z, walk-in booking |
| `core/views/student.py` | Created | Student dashboard, appointments list, slot lookup API, booking form handler, and cancellation |
| `core/views/counselor.py` | Created | Counselor clinical workspace (daily sessions, stats) and status update state machine |
| `core/views/receptionist.py` | Created | Receptionist front-desk 4-step walk-in booking view and search endpoint |
| `core/urls.py` | Modified | Added 9 Phase 4 appointment routes for students, counselors, and receptionists |
| `templates/student/dashboard.html` | Created | Student dashboard interface with upcoming session overview |
| `templates/student/appointments.html` | Created | Student appointment list with status pills and cancellation triggers |
| `templates/student/book_appointment.html` | Created | Booking page with dynamic hourly slots (09:00–16:00) |
| `templates/counselor/workspace.html` | Created | Clinical workspace showing daily agenda and status transitions |
| `templates/receptionist/dashboard.html` | Created | Front-desk interface with live student search and walk-in scheduling |
| `tests/test_slots.py` | Created | Unit tests: 09:00-16:00 slots, pending/confirmed subtraction, +/- 50m clash window, alphabetical next-available |
| `tests/test_appointments.py` | Created | Integration tests: booking audit, student self-cancellation, counselor state machine, receptionist booking, role guards |

---

### Entry 012 — Case notes: AES-256 encryption, confidentiality controls, editor view, template & tests (Phase 5)

| Field | Value |
|---|---|
| Date | 2026-09-24 |
| Commit | uncommitted |
| Phase | PLAN Phase 5 (steps 32–36) |

**Created / Modified:**

| File | Status | Purpose |
|---|---|---|
| `core/views/counselor.py` | Modified | Added `counselor_case_note_view` (/counselor/case-notes/<int:appointment_id>/) with AES-256 encryption, upsert, and confidentiality controls |
| `core/urls.py` | Modified | Added `case_note` named route (/counselor/case-notes/<int:appointment_id>/) |
| `templates/counselor/case_note.html` | Created | Clinical case note editor with appointment summary, note textarea, confidentiality toggle, and encryption error banner |
| `tests/test_case_notes.py` | Created | Tests for AES-256 encryption at rest, unique constraint upsert, author assignment integrity, RLS confidentiality matrix, and legacy gc:v1: decrypt |

---

### Entry 013 — Mood check-in & AI Chatbot: SSE streaming, rate limiting, crisis disclaimer, templates & tests (Phase 6)

| Field | Value |
|---|---|
| Date | 2026-09-24 |
| Commit | uncommitted |
| Phase | PLAN Phase 6 (steps 37–43) |

**Created / Modified:**

| File | Status | Purpose |
|---|---|---|
| `config/settings.py` | Modified | Added `CHAT_RATE_LIMIT_WINDOW_MS` (900000) and `CHAT_SESSION_GET_WINDOW` (900000) settings gap G4 |
| `core/services/chat.py` | Modified | Upgraded with `stream_chat_response` generator (SSE), rate limiters (GET 60/15m, POST 24/15m), and crisis protocol |
| `core/views/student.py` | Modified | Added `student_mood_checkin_view` (/student/mood/) with branches (good/okay, low + appt, low + no appt) |
| `core/views/chat.py` | Created | Views for `chat_session_get_view` (/chat/session/), `chat_stream_post_view` (/chat/ SSE), and `student_chatbot_page_view` (/chatbot/) |
| `core/urls.py` | Modified | Added Phase 6 routes: `/student/mood/`, `/chatbot/`, `/chat/session/`, `/chat/` |
| `templates/student/chatbot.html` | Created | Interactive student chatbot UI with SSE streaming, message history, crisis banner, and booking CTA |
| `tests/test_mood_chat.py` | Created | Comprehensive tests: mood branches, rate limit 429 Retry-After, 24k char limit, 36-msg cap, 503 missing keys, crisis/CTA flags, session hydration |

---

### Entry 014 — Phase 7 (UI Completion) & Phase 8 (Admin, Reports, Safeguards, & QA Sign-off)

| Field | Value |
|---|---|
| Date | 2026-09-24 |
| Phase | PLAN Phase 7 (steps 44–63) & Phase 8 (steps 64–73) |
| Verification | `manage.py test` → 70 tests passed (100% pass rate in 153s) |

**Completed:**
1. **Admin Suite (`/admin-panel/*`):**
   - `core/views/admin_views.py`: Overview, User Management, Audit Trail Viewer, Custom Reports, Profile.
   - `core/services/admin_users.py`: Self-demotion safeguards, last-admin protection, self-deactivation blocks.
   - `core/services/metrics.py`: Executive KPIs, 8-week series (Monday start), top-8 concern breakdown + other.
   - `core/services/reports.py`: Filtered appointment search, RFC-4180 CSV export, ReportLab PDF generation.
2. **Templates & Static Assets:**
   - Completed 16 screens + floating chatbot widget (`templates/widgets/chatbot.html`).
   - Integrated Stitch UI tokens, responsive layouts, role subnavs, flash alerts.
3. **Full Automated Test Suite:**
   - `tests/test_admin_safeguards.py` (admin RBAC safeguards, metrics, CSV/PDF reports & signals)
   - `tests/test_views_http.py` (HTTP 200 checks across all 16 screen routes)
   - `tests/test_slots.py`, `tests/test_appointments.py`, `tests/test_case_notes.py`, `tests/test_mood_chat.py`, `tests/test_auth_guards.py`
   - Fixed keyword triggers and foreign-key audit assertions.
   - **Result: 70 tests passing, 0 errors, 0 failures.**

---

## What has NOT been created yet (gap register)

Reconstructed from `docs/PLAN.md` vs filesystem — all technical items complete:

| # | Item | Plan ref | Status |
|---|---|---|---|
| 1 | `core/views/` package (auth, student, counselor, receptionist, chat, admin) | Folder blueprint | ✅ Complete (Entry 014) |
| 2 | `core/urls.py` + auth routes (`login`, `logout`, `register`, `password_change`, `role_home`) | Phase 3 steps 16–21 | ✅ Complete (Entry 010) |
| 3 | All 16 page templates + `widgets/chatbot.html` | Phase 7 steps 44–61 | ✅ Complete (Entry 014) |
| 4 | `static/css/`, `static/js/` (design tokens, chat SSE client, charts) | Phase 7 | ✅ Complete (Entry 014) |
| 5 | Test suite (`tests/` — one file per phase/flow) | Folder blueprint + verify cmds | ✅ Complete (70/70 tests pass) |
| 6 | Admin custom UI at `/admin-panel/*` (overview, users, audit, reports, profile) | Phase 7 + 8 | ✅ Complete (Entry 014) |
| 7 | Admin safety guards (last-admin, self-demote, self-deactivate) | Phase 8 step 70 · RLS §5 | ✅ Complete (Entry 014) |
| 8 | SSE streaming chat endpoint | Phase 6 step 40 | ✅ Complete (Entry 013) |
| 9 | Receptionist student-search as discrete service | Phase 4 step 29 | ✅ Complete (Entry 011) |
| 10 | Live Supabase `DATABASE_URL` in `.env` | Phase 1 exit criteria | User config (configured in `.env`) |
| 11 | `gunicorn` / `whitenoise` in requirements | Phase 8 step 71 | ✅ Complete (`requirements.txt`) |
| 12 | README full setup/run/test/deploy final pass | Phase 8 step 72 | ✅ Complete (`README.md`) |
| 13 | Full QA pass of 24 flows + tick master checklist | Phase 8 step 73 · PLAN 50 boxes | ✅ Complete (50/50 ticked) |

---

## How to update this log

1. Add a new **Entry NNN** section at the end of *Timeline of all changes*.
2. Include: date, phase (from `PLAN.md`), files created/changed, what the change does, verify command/result.
3. Update the **Summary dashboard** counts.
4. When a gap-register row is completed, flip its status to ✅ and note the entry number.
5. Prefer one entry per logical feature/commit — not per keystroke.

---

## Git reference

| Commit | Date | Subject |
|---|---|---|
| `b612711` | 2026-09-24 09:03 +0800 | Initial commit: Django project foundation with Supabase PostgreSQL config |
| `5ab1601` | 2026-09-24 14:07 +0800 | first commit |

```powershell
# Review history anytime
git log --oneline --stat
```
