# Antigravity Session Prompts — ConnectGuidance Django

Complete prompt set for building the feature-complete Django replica of GuidanceConnect.
Copy-paste one prompt per Antigravity session. Follow the order below.

| Field | Value |
|---|---|
| Total prompts | 9 (master + 8 phase/session prompts) |
| Covers | PLAN (73 steps), FLOWS (24), INTERFACES (16+1), RLS (13+matrix), REFERENCES (G1–G8) |
| Defaults | Login = email; Logout → `/` |
| Build order | Paste PROMPT 0 once → then 1→2→3→4→5→6 (7 parallel OK, 8 last) |

---

## PROMPT 0 — Master kickoff (paste once at session start)

```text
PROJECT: ConnectGuidance Django — build feature-complete replica of GuidanceConnect.
You are the full team (Architect/Backend/Frontend/QA). Production-grade only.

=== READ BEFORE CODING (order) ===
1. docs/PLAN.md — 8 phases, 73 steps, No-Missing-Parts checklist (50 boxes)
2. docs/FLOWS.md — 24 flows; implement EVERY branch + error path
3. docs/INTERFACES.md — 16 screens + 1 overlay, exact routes, design tokens, states
4. docs/ERD.md — models spec (ALREADY IMPLEMENTED — do not change schema)
5. docs/RLS_AND_SECURITY.md — query scoping matrix, encryption, rate limits, admin guards, 13-box checklist
6. docs/REFERENCES.md — original Next.js file → Django target map (open original when behavior is ambiguous)
7. AGENTS.md — standards: full files, no placeholders, no TODOs, no "implement later"
8. docs/AUDIT_LOG.md — what exists + gap register (append an entry after EVERY phase)

=== ALREADY DONE — DO NOT REBUILD ===
- Phase 1: config/, settings (Supabase DATABASE_URL + SQLite fallback), requirements.txt, .env.example
- Phase 2: 6 models (Profile, Appointment, CaseNote, AuditLog, ChatbotSession, StudentMoodAlert)
  + migration core/0001_initial (APPLIED — never edit this migration)
- Services: slots, appointments, case_notes, encryption, mood, chat, reports, audit (24 functions)
- core/guards.py (role_required + require_admin/counselor/student/receptionist, ROLE_HOMES)
- 6 forms, signals (profile auto-create + audit dual-write), admin 6/6, seed_roles command
- 6 companion docs complete

=== STATE ===
Overall ~30–35%. Views: 0. App URLs: 0 (only /admin/). Templates: 0. Static: 0. Tests: 0.
settings LOGIN_URL='login' and LOGIN_REDIRECT_URL='role_home' — these named URLs DO NOT EXIST YET.
DB = SQLite until .env has real Supabase URI.

=== DECISIONS (locked) ===
- Login identifier: EMAIL (parity with original signin). Use username=email on User create OR custom AuthenticationForm accepting email.
- Logout redirect: '/' (FLOWS §4). Set LOGOUT_REDIRECT_URL='/'.
- Public paths: /, /login/, /register/ only. Authenticated user hitting public path → redirect ROLE_HOME (FLOWS §1).
- App admin UI: /admin-panel/*. Django built-in admin stays at /admin/ (ops only).
- Password change UI: embedded in student profile + admin profile pages; route password_change/ still required (PLAN step 16/21).
- services/metrics.py: metrics live in reports.py::get_admin_metrics — DO NOT create duplicate; thin alias OK.
- scripts/: seed lives at core/management/commands/seed_roles.py — intentional, no scripts/ folder needed.
- OAuth callback: SKIP (no Supabase OAuth).

=== BUILD ORDER (stop after each phase for review) ===
Phase 3 → 4 → 5 → 6 → 7 → 8, with tests alongside.

=== GLOBAL RULES ===
- Views are THIN adapters: call existing services/forms/guards — never reimplement business logic.
- Every protected view: correct @role_required + query scoping per RLS §1 matrix.
- Every POST: {% csrf_token %}. CSRF middleware already on.
- Secrets (ENCRYPTION_KEY, DB, API keys) only in .env — never templates/JS/logs.
- Error strings should match FLOWS.md branches exactly where shown.
- After each phase:
  1) python manage.py check → 0 issues
  2) run/extend tests for that phase
  3) append docs/AUDIT_LOG.md entry (date, phase, files, verify result)
  4) tick PLAN.md checkboxes ONLY for steps whose Verify row passes
  5) update gap register in AUDIT_LOG.md
- Do not touch core/migrations/0001_initial.py field names.
- No placeholder code. Output complete files with paths.

START: Phase 3 only. Output full files, then a "How to verify" block.
```

---

## PROMPT 1 — Phase 3: Auth + URLs (+ public redirect)

```text
CONTEXT: Read PROMPT 0 rules (or assume them). Execute PHASE 3 ONLY (PLAN steps 16–23).
Services/guards/forms exist. You create the HTTP layer.

=== CREATE ===
1. core/views/__init__.py
2. core/views/auth.py — landing, login, logout, register, password_change, role_home
3. core/views/public.py — or fold landing into auth.py (your call; document it)
4. core/urls.py — all named routes below
5. Edit config/urls.py — path('', include('core.urls'))

=== NAMED URLS (must match settings + guards) ===
- name='login' → /login/ (email + password; preserve ?next=; show ?error=deactivated|no_profile)
- name='logout' → /logout/ (POST preferred; also allow GET for parity) → redirect '/'
- name='register' → /register/ (StudentRegistrationForm; students only; on success → auto-login optional → redirect login or student home)
- name='password_change' → /password_change/ (django.contrib.auth PasswordChangeView; login_required; success stays signed in, toast via messages)
- name='role_home' → /role-home/ (read profile.role → ROLE_HOMES redirect; handles settings LOGIN_REDIRECT_URL)
- name='landing' → / (public page)

=== BEHAVIOR (FLOWS §1–6 — all branches) ===
- Public path + authenticated + is_active → redirect ROLE_HOME
- Public path + authenticated + inactive → logout + /login/?error=deactivated
- Login: invalid creds → form error; profile missing → ?error=no_profile; inactive → logout + ?error=deactivated; success → ROLE_HOME
- Register: email dup / weak password → field errors (form already validates ≥8); User create with username=email; signal auto-creates Profile role=student
- Guards: every future protected view will use core/guards.py — do not rewrite guards unless a bug is found

=== SETTINGS EDITS ===
- LOGOUT_REDIRECT_URL = '/'
- Ensure LOGIN_URL='login', LOGIN_REDIRECT_URL='role_home' resolve (they will once urls exist)

=== TEMPLATES (minimum for phase to be testable; full polish in Phase 7) ===
- templates/base.html (stub OK if Phase 7 will replace — but include {{ messages }} block)
- templates/public/landing.html, templates/registration/login.html, register.html, password_change.html
- Apply INTERFACES tokens if trivial; full UI later.

=== TESTS ===
tests/test_auth_guards.py:
- register creates User+Profile(student)
- login by email works (or username=email — assert your chosen mechanism)
- wrong password fails; inactive → deactivated redirect
- logout → /
- role_home: 4 roles → correct paths
- authenticated GET /login/ → ROLE_HOME
- wrong-role access to a dummy protected view redirects ROLE_HOME

=== VERIFY ===
python manage.py check
python manage.py test tests.test_auth_guards
Manual: seed_roles accounts log in (admin/counselor1/student/receptionist).

Then: AUDIT_LOG entry + tick PLAN steps 16–23 that pass. STOP.
```

---

## PROMPT 2 — Phase 4: Appointment views

```text
CONTEXT: Phase 3 done. Execute PHASE 4 ONLY (PLAN steps 24–31, FLOWS §7–10, §16).
Services exist: slots.py, appointments.py. Forms exist: AppointmentBookingForm, ReceptionistBookingForm.
Create thin views only.

=== CREATE ===
core/views/student.py
- availability: GET counselor+date → get_available_slots_for_counselor JSON or partial (student-only)
- book: GET/POST AppointmentBookingForm → book_appointment() → redirect /appointments/ + messages
  Errors per FLOWS §8: future date, active student, counselor role, clash "That time was just taken", DB fail
- cancel: POST own row only → student_cancel_appointment() → APPOINTMENT_CANCELLED_STUDENT
  Errors: not own → 404; terminal → "Can no longer be cancelled"
- list: /appointments/ upcoming (+cancel) + past/cancelled tables

core/views/counselor.py
- workspace data loader: stats today/upcoming/past, sessions, tables (template Phase 7; view context now)
- status_update: POST → counselor_update_status() state machine only
  pending→confirmed/cancelled; confirmed→completed/cancelled; terminal blocked; not assigned → deny
  → APPOINTMENT_STATUS_UPDATED

core/views/receptionist.py (+ core/services/receptionist.py NEW)
- service: search_students(q) name|student_id ILIKE, active only, limit 25 (G-gap)
- service wrappers: list counselors A-Z, any-free slots, book path using get_first_available_counselor_slot
- views: 4-step flow endpoints or single page POST actions (match INTERFACES #16 steps 1–4)
- audit action name: APPOINTMENT_CREATED_RECEPTION
- errors: inactive student, no counselors, clash, none free, invalid future datetime

core/urls.py: add routes
/student/ (dashboard shell OK), /appointments/, slots endpoint, cancel, status update, /receptionist/ (+search)

ALL views: require_student / require_counselor / require_receptionist from guards.

=== TESTS (tests/test_slots.py + tests/test_appointments.py) ===
- slots 09:00–16:00; booked pending/confirmed subtracted; clash ± window
- book creates pending + audit row
- student cancel only own; terminal blocked
- counselor illegal transitions rejected (incl. pending→completed)
- receptionist search limit 25 + active only
- receptionist next-available A–Z picks first free
- wrong role → redirect ROLE_HOME

=== VERIFY ===
manage.py check + tests + FLOWS §7–10, §16 manual walk with seed data.
AUDIT_LOG entry + tick PLAN 24–31. STOP.
```

---

## PROMPT 3 — Phase 5: Case notes

```text
CONTEXT: Execute PHASE 5 ONLY (PLAN steps 32–36, FLOWS §11–12, RLS §3 §7).
encryption.py + case_notes.py exist.

=== ADD/EDIT ===
core/views/counselor.py
- case_note editor GET/POST /counselor/case-notes/<uuid:appointment_id>/
  - active counselor + appointment.counselor == me else 404/403
  - wire CaseNoteForm → save_case_note() (encrypt + upsert UNIQUE)
  - integrity: counselor mismatch → error (service clean already; surface message)
  - confidentiality toggle only author
- case note read path: author decrypt; student sees only is_confidential=False via own appointments;
  admin decrypt only if not is_confidential (get_decrypted_case_note)

URL: /counselor/case-notes/<uuid>/ name='case_note'

ENCRYPTION_KEY: if missing/invalid → user-friendly "Encryption failed" (FLOWS §11), never 500.

=== TESTS tests/test_case_notes.py ===
- save produces non-plaintext content in DB
- upsert updates same (appointment, counselor) row — still 1 row
- second counselor cannot save/read on same appointment (integrity)
- student cannot fetch confidential note
- admin non-confidential OK; admin confidential denied decrypt
- legacy gc:v1: decrypt path if fixture provided

=== VERIFY ===
check + tests + RLS §7 confidentiality walk.
AUDIT_LOG + tick PLAN 32–36. STOP.
```

---

## PROMPT 4 — Phase 6: Mood + Chat (SSE)

```text
CONTEXT: Execute PHASE 6 ONLY (PLAN steps 37–43, FLOWS §13–15).
mood.py + chat.py exist — chat is NOT streaming yet. FIX that.

=== CREATE core/views/student.py (mood) ===
- POST mood check-in (MoodCheckInForm) → process_mood_checkin()
- branches FLOWS §13: good/okay → audit + notified=false;
  low + no appt → "book a session first or front desk";
  low + appt → StudentMoodAlert + notified=true + counselorName;
  counselor no longer counselor → error

=== CREATE core/views/counselor.py (feed) ===
- workspace context: StudentMoodAlert.objects.filter(counselor=me) feed

=== CREATE core/views/chat.py ===
- GET session: active student only; rate limit GET 60/15min → 429; return latest ChatbotSession or empty (FLOW 14)
- POST /chat/ (FLOW 15) — STREAMING:
  - 503 if no GROQ_API_KEY and no ANTHROPIC_API_KEY
  - 400 invalid body / last role!=user / content>24000
  - 401/403 not active student or not session owner
  - 429 POST rate 24/15min + Retry-After header
  - system prompt parity (counselor assistant + escalate) — from original lib/chat/constants.ts if available
  - StreamHttpResponse / StreamingHttpResponse pumping SSE deltas from upstream
  - accumulate → save_or_update_session() → CHAT_SESSION_UPSERT audit
  - mid-stream fail → SSE error event; client rolls back
  - CTA: should_trigger_booking_cta → should_suggest flag for widget "Book appointment"

=== SETTINGS GAPS (G4) ===
Add:
CHAT_RATE_LIMIT_WINDOW_MS = int(os.getenv('CHAT_RATE_LIMIT_WINDOW_MS', 900000))
CHAT_SESSION_GET_WINDOW = int(os.getenv('CHAT_SESSION_GET_WINDOW_MS', 900000))
Use them in rate limiter (parity RLS §4).

=== SERVICE UPGRADE ===
core/services/chat.py: add streaming generator (e.g. stream_chat_response) while keeping generate_chat_response as fallback/tests. Do not remove CTA/crisis/rate-limit/36-cap logic.

=== TESTS tests/test_mood_chat.py ===
- mood good/okay/low/no-appt branches
- rate limit → 429 after 24 (mock time or loop)
- history cap 36, content ≤24000 → 400
- no API key → 503
- crisis text sets flag; CTA trigger text sets should_suggest
- session GET hydrates + ownership isolation

=== VERIFY ===
check + tests + FLOWS §13–15. AUDIT_LOG + tick PLAN 37–43 (40 only when SSE works). STOP.
```

---

## PROMPT 5 — Phase 7: Full UI (16 + overlay + static)

```text
CONTEXT: Phases 3–6 views exist. Execute PHASE 7 ONLY (PLAN steps 44–63, ALL of INTERFACES.md).
templates/ and static/ are EMPTY. Build everything.

=== EXACT TEMPLATE LIST (16 + 1 + partials) ===
1  templates/base.html                          chrome: sidebar #0F172A, topbar, {{ messages }}, blocks
2  templates/public/landing.html                /                hero, CTAs, 3 audience cards, footer
3  templates/registration/login.html            /login/          email+password, link register, error query params
4  templates/registration/register.html         /register/       fields per form, client+server errors
5  templates/student/dashboard.html             /student/        greeting, mood widget, upcoming, history, chat FAB  (FLOW 22)
6  templates/student/appointments.html          /appointments/   book form (counselor/date/9AM–4PM slots/concern/notes≤2000), tables+cancel, status badges
7  templates/student/chatbot.html               /chatbot/        info cards, crisis banner, embedded widget
8  templates/student/profile.html               /student/profile/  read-only fields + change password card
9  templates/student/front_desk.html            /student/front-desk/ static info
10 templates/counselor/workspace.html           /counselor/      stat chips, alert feed, today sessions, Confirm/Cancel/Complete buttons, tabs+pagination (FLOW 23)
11 templates/counselor/case_note.html           /counselor/case-notes/<uuid>/  sticky left summary+legend, right textarea min 320px, counter, confidentiality switch, states
12 templates/admin/overview.html                /admin-panel/    KPI×4, 8-week bar, concern donut (Chart.js CDN), recent activity→audit
13 templates/admin/users.html                   /admin-panel/users/  +Add user, search, role/status filter, sort, table, inline role select, activate/deactivate confirm, GUARD copy for self/last-admin
14 templates/admin/audit_logs.html              /admin-panel/audit/  filters user/action/table/date, **Export CSV**, table, metadata expand JSON, pagination, empty state
15 templates/admin/reports.html                 /admin-panel/reports/  filters, generate, summary, preview 50, Export PDF+CSV+print, skeleton/empty
16 templates/admin/profile.html                 /admin-panel/profile/  account card + change password
17 templates/receptionist/booking.html           /receptionist/   4-step wizard + Next Available + slot grid 9–16 + confirmation + "slot just taken" error (FLOW 16)
+  templates/widgets/chatbot.html               include          FAB amber, panel 380×560 r16, streaming dots, CTA card, crisis dismiss, composer, empty/loading/error/reset
+  partials: StudentSubnav, CounselorSubnav, AdminSubnav, ReceptionistSubnav, _messages.html
+  templates/registration/password_change.html  if not embedded only

=== VIEW↔TEMPLATE BINDING ===
Ensure every route in INTERFACES "Template route checklist" renders the matching template (render(..., template_name=...)).
Missing contexts from FLOWS 22–23 must be wired now (dashboard non-confidential case history, counselor actions).

=== STATIC ===
static/css/app.css — ALL tokens: #2563EB #0D9488 #F8FAFC #0F172A; cards r12; buttons r8 h40;
  table header #F1F5F9 row 48 hover #F8FAFC; status/role/concern colors; 1440px layout; spacing 4/8/12/16/24/32;
  fonts Inter/Poppins (Google Fonts or local stack); empty/loading/error/success styles
static/js/chat.js — fetch + ReadableStream/SSE client against Django stream; CTA; rollback on error; new conversation
static/js/slots.js — slot picker states available/hover/selected/booked
static/js/admin-charts.js — Chart.js CDN wiring for overview
(optional) static/js/receptionist.js — step wizard

=== STATES (every page) ===
empty · loading (skeleton or JS) · error · success toast via django.contrib.messages

=== VERIFY (PLAN step 63) ===
- Count: 16 routes + 1 widget all HTTP 200, correct template
- python manage.py test tests.test_views_http (create if absent): parametrize route→template
- Design tokens present in app.css
- Chat widget streams against Phase 6 endpoint
AUDIT_LOG + tick PLAN 44–63. STOP.
```

---

## PROMPT 6 — Phase 8: Admin UI, guards, exports, ops, QA

```text
CONTEXT: Execute PHASE 8 ONLY (PLAN steps 64–73, FLOWS §17–21, §24, RLS §5 §10).
audit.py + signals already exist (64–65 done). reports.py has metrics/CSV/PDF.

=== CREATE core/views/admin_views.py + URLs under /admin-panel/ (all @require_admin) ===
1. overview — get_admin_metrics() KPIs + 8-week series + concern breakdown + recent AuditLogs
2. users — list/search/filter/sort
   + **ADD USER** (G1): create User+Profile, role select, staff only for admin; username=email;
   role change + activate/deactivate toggles
   + **SAFEGUARDS (RLS §5 / FLOWS 17–18) — service core/services/admin_users.py NEW:**
     - cannot demote self → "You cannot demote your own admin account here."
     - cannot remove last admin → "Cannot remove the last admin account."
     - cannot deactivate self → "You cannot deactivate your own account."
     - cannot deactivate last active admin → "Cannot deactivate the last active admin."
3. audit — filters user/action/table/date range + pagination + metadata JSON expand
   + **Export CSV of filtered audit rows** (G2) + empty state
4. reports — filter_appointments → preview (note first 50) →
   export_appointments_csv + export_appointments_pdf + audit REPORT_EXPORT on export
5. profile — account info + PasswordChangeForm card

=== TESTS ===
tests/test_admin_guards.py — all 4 safeguard errors + happy paths
tests/test_reports_audit.py — metrics keys, CSV non-empty, PDF bytes, log_action never raises
tests/test_views_http.py — extend: /admin-panel/* 200 for admin, redirect for others

=== OPS ===
- requirements.txt: add gunicorn (and whitenoise optional); pin versions
- settings: SecurityMiddleware whitenoise if added; STATIC_ROOT collectstatic note
- README.md final: setup, env table, run, **test command**, seed, deploy (gunicorn config.wsgi), links to all docs/
- Confirm .env gitignored; run with DJANGO_DEBUG=False → check still clean (ALLOWED_HOSTS set)

=== FINAL QA (PLAN step 73) ===
- Execute all 24 FLOWS.md flows; record pass/fail in AUDIT_LOG.md QA section
- Tick ALL 50 PLAN.md master checklist boxes that pass
- Tick ALL 13 RLS_AND_SECURITY.md §10 boxes
- python manage.py test → full suite green
- python manage.py check → 0 issues
- Count routes: 16 templates + overlay verified again

AUDIT_LOG final entry "replica complete" or list residual gaps. STOP.
```

---

## PROMPT 7 — Tests-only session (can run anytime after Phase 3)

```text
Create/complete tests/ to match PLAN verification:
tests/test_models.py, test_auth_guards.py, test_slots.py, test_appointments.py,
test_case_notes.py, test_mood_chat.py, test_reports_audit.py, test_admin_guards.py,
test_views_http.py
Rules: use Django TestCase, seed_roles-like fixtures in setUpTestData, no real network
(mock Groq), no real Supabase (test SQLite). Command must be: python manage.py test
After: append AUDIT_LOG entry with pass counts.
```

---

## PROMPT 8 — Security close-out session

```text
Walk docs/RLS_AND_SECURITY.md §10 (13 items) + §1 matrix against the live code.
For each: evidence (test name or manual step) or FIX the gap (view/form/template).
Never weaken guards to make a test pass. Output a table: item | status | evidence.
Append result to docs/AUDIT_LOG.md. Tick the 13 boxes only when evidenced.
```

---

## Prompt hygiene for Antigravity

| Rule | Detail |
|---|---|
| One phase per session | "Execute PHASE N ONLY… STOP" |
| Always | `check` → `test` → AUDIT_LOG → tick PLAN |
| Read docs first | "Read docs X before coding" every session |
| Review before commit | After any agent run: you review `git diff` before commit |
| Order | Paste PROMPT 0 once; then 1→2→3→4→5→6 (7 parallel OK, 8 last) |

**Coverage:** No missing parts vs PLAN (73), FLOWS (24), INTERFACES (16+1), RLS (13+matrix), REFERENCES (incl. G1–G8).
