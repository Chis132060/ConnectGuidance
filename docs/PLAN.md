# GuidanceConnect — Django Replica Master Plan

| Field | Value |
|---|---|
| Target folder | `C:\School works\4yr_firstsem\connectguidance_django` |
| Django project | `config` (settings: `config.settings`) |
| Python | 3.12.10 (`.venv`) |
| Django | 5.2.x |
| Database | Supabase PostgreSQL (`sslmode=require`) |
| Original system | `../connectguidance1` — Next.js 16 + Supabase (source of truth) |
| UI approach | Django templates + server-rendered pages (16 screens) |
| Auth | Django session auth + custom role guards (replaces Supabase Auth + `proxy.ts`) |
| Companion docs | `ERD.md`, `FLOWS.md`, `INTERFACES.md`, `RLS_AND_SECURITY.md`, `REFERENCES.md` |

**Goal:** Feature-parity replica of GuidanceConnect in pure Django.

**Rule:** No step is done until its Verify column passes.

**Status legend:** done · needs fix · pending · later phase

---

## PHASE 1 — Foundation Skeleton (NO features)

| # | Action | Command / output | Status |
|---|---|---|---|
| 1 | Create `.venv` | `python3 -m venv .venv` → activate → `python` = 3.12.x | done |
| 2 | `requirements.txt` | Django, dj-database-url, python-dotenv, psycopg2-binary (or `psycopg[binary]`), gunicorn* | gunicorn at Phase 8 |
| 3 | Install deps | `pip install -r requirements.txt` | done |
| 4 | Scaffold | `django-admin startproject config .` → `manage.py` + `config/` | done |
| 5 | `.env` + `.env.example` | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` (real Supabase URI, `sslmode=require`) | placeholders only |
| 6 | `.gitignore` + `README.md` | ignore `.env`, `.venv/`, `__pycache__`, `db.sqlite3`, `staticfiles/` | done / expand |
| 7 | `config/settings.py` | `load_dotenv()`; `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` from env; `DATABASES` via `dj_database_url(..., conn_max_age=600, ssl_require=True)` | done |
| 8 | Verify | `python manage.py check` → no issues; **no migrate yet** (Option B) | pending |

### Env fixes required before Phase 2

```env
# .env (real values — never commit)
DJANGO_SECRET_KEY=<generate: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://postgres.[PROJECT]:[PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require
ENCRYPTION_KEY=<64 hex chars>          # Phase 5
GROQ_API_KEY=                          # Phase 6 (or ANTHROPIC_API_KEY)
```

**Phase 1 exit:** `check` passes + real `DATABASE_URL` in `.env`.

---

## PHASE 2 — Data Design (ERD → Django models)

| # | Action | Command / output |
|---|---|---|
| 9 | Create app | `python manage.py startapp core` |
| 10 | Register | add `'core'` to `INSTALLED_APPS` |
| 11 | Choices (enums) | `APP_ROLE = admin\|counselor\|student\|receptionist`; `APPOINTMENT_STATUS = pending\|confirmed\|cancelled\|completed` |
| 12 | Models | match `ERD.md` field-for-field |
| 13 | Constraints | FK `on_delete` rules, `unique_together(appointment, counselor)` on CaseNote, `CheckConstraint` note ≤ 500, `Meta.indexes` |
| 14 | Migrate | `makemigrations core` → `migrate` (creates tables on Supabase) |
| 15 | Verify | `check` · tables visible in Supabase · `ERD.md` checklist 100% |

### Models (Django) — no missing fields

| Model | Key fields (beyond `id`) | Critical rules |
|---|---|---|
| `Profile` | `user` OneToOne→`auth.User`; `role`; `full_name`; `student_id`; `department`; `is_active`; `user_no` unique; `created_at` | Role choices; auto-create on User `post_save` (signup trigger parity) |
| `Appointment` | `student` FK→Profile CASCADE; `counselor` FK→Profile **PROTECT**; `scheduled_at`; `status`; `concern_type`; `notes`; `created_at` | Status default `pending`; indexes student / counselor / scheduled_at |
| `CaseNote` | `appointment` FK CASCADE; `counselor` FK CASCADE; `content` (ciphertext); `is_confidential`; timestamps | **UNIQUE(appointment, counselor)**; `clean()` counselor must equal appointment.counselor |
| `AuditLog` | `user` FK→Profile **SET_NULL** null; `action`; `table_name`; `record_id` (UUID null, no FK); `metadata` JSON; `created_at` | append-only in app code |
| `ChatbotSession` | `student` FK CASCADE; `messages` JSON default `[]` | student owns session |
| `StudentMoodAlert` | `student` FK CASCADE; `counselor` FK CASCADE; `note` ≤ 500 null; `created_at` | indexes `(counselor, -created_at)`, `(student, -created_at)` |

**RLS → Django:** Supabase row-level security is NOT ported as DB RLS; it becomes query scoping + view/service guards — see `RLS_AND_SECURITY.md`.

---

## PHASE 3 — Auth + Role Guards (replaces Supabase Auth + proxy.ts)

| # | Action | Command / output |
|---|---|---|
| 16 | URLs | `login/`, `logout/`, `register/`, `password_change/` (`django.contrib.auth` + custom register) |
| 17 | Register | create User + Profile (`role=student`, `is_active`, `user_no`) — parity with signup trigger |
| 18 | Login flow | after login → `ROLE_HOME[role]` redirect (`/admin-panel`, `/counselor`, `/student`, `/receptionist`) |
| 19 | Guards | `@login_required` + `role_required('admin')` etc. → wrong role = redirect ROLE_HOME; inactive = logout + `login?error=deactivated` |
| 20 | Page guards | every protected view mirrors original: student×5, counselor×2, admin×5 (`requireAdmin`), receptionist×1 |
| 21 | Password change | Django `PasswordChangeView` (parity with `StudentChangePasswordForm`) |
| 22 | Staff bootstrap | `createsuperuser` + `seed_roles` management command (admin, counselor, receptionist, student test rows) |
| 23 | Verify | 4 roles log in; wrong-route redirect; deactivated blocked; password change works |

**Parity map:** `proxy.ts` → middleware/guards · `requireAdmin` → `role_required('admin')` · signin API → Django login view.

---

## PHASE 4 — Appointments (booking + state machine)

| # | Action | Command / output |
|---|---|---|
| 24 | `services/slots.py` | port `appointment-slots.ts`: 09:00–16:00 hourly, day bounds in `TIME_ZONE` |
| 25 | Availability view | student-only; subtract `pending`/`confirmed` slots |
| 26 | Book view | validate future time, counselor role, minute-window clash → status=`pending` → audit `APPOINTMENT_CREATED` |
| 27 | Student cancel | own row only; block if `cancelled`/`completed` → `APPOINTMENT_CANCELLED_STUDENT` |
| 28 | Counselor status | state machine only: pending→confirmed/cancelled; confirmed→completed/cancelled; terminal blocked → `APPOINTMENT_STATUS_UPDATED` |
| 29 | Receptionist book | search student; list counselors; any-free slots; specific counselor clash loop; next-available first-free alphabetically → `APPOINTMENT_CREATED_RECEPTION` |
| 30 | No Next.js revalidate | plain redirect/render after POST |
| 31 | Verify | full lifecycles from `FLOWS.md` sections 7–10, 16 |

### Status state machine (enforce in service)

| From | Allowed next |
|---|---|
| pending | confirmed, cancelled |
| confirmed | completed, cancelled |
| completed | *(terminal)* |
| cancelled | *(terminal)* |

---

## PHASE 5 — Case notes + encryption

| # | Action | Command / output |
|---|---|---|
| 32 | `services/encryption.py` | port `encryption.ts`: AES-256-CBC hex (iv+cipher); optional legacy `gc:v1:` GCM decrypt; key = `ENCRYPTION_KEY` (64 hex) |
| 33 | Save view | counselor author only; encrypt → upsert UNIQUE(appointment, counselor); audit `CASE_NOTE_UPSERT` |
| 34 | Integrity | reject if `note.counselor != appointment.counselor` (port DB trigger) |
| 35 | Read rules | author decrypt; admin only if `!is_confidential`; student sees only `!is_confidential` |
| 36 | Verify | wrong counselor 403; ciphertext at rest; toggle hides from student |

---

## PHASE 6 — Mood alerts + AI chatbot

| # | Action | Command / output |
|---|---|---|
| 37 | Mood view | `good`/`okay` → audit only; `low` → latest non-cancelled appointment’s counselor → `StudentMoodAlert`; none → booking error message |
| 38 | Counselor feed | workspace lists alerts (`counselor=me`) |
| 39 | Chat session GET | latest session by student → hydrate widget |
| 40 | Chat POST | rate limit 24/15 min; max 36 msgs; content ≤ 24000; `studentId=me`; stream SSE from Groq/Anthropic; persist messages; audit `CHAT_SESSION_UPSERT` |
| 41 | Book CTA | port `lib/chat/cta.ts` patterns → show “Book appointment” button |
| 42 | Crisis disclaimer | system prompt parity (`lib/chat/constants.ts`) |
| 43 | Verify | low mood alert; stream + restore; 429 after limit; CTA on crisis text |

---

## PHASE 7 — UI (16 screens + 1 overlay) — Django templates

| # | Screen | Route | Template |
|---|---|---|---|
| 44 | Base layout | — | `templates/base.html` (role sidebar/subnav, topbar, messages) |
| 45 | Landing | `/` | `public/landing.html` |
| 46 | Login | `/login/` | `registration/login.html` |
| 47 | Register | `/register/` | `registration/register.html` |
| 48 | Student dashboard | `/student/` | `student/dashboard.html` (mood, upcoming, history, chat widget) |
| 49 | Appointments | `/appointments/` | `student/appointments.html` (book + tables) |
| 50 | Chatbot page | `/chatbot/` | `student/chatbot.html` |
| 51 | Student profile | `/student/profile/` | `student/profile.html` |
| 52 | Front desk info | `/student/front-desk/` | `student/front_desk.html` |
| 53 | Counselor workspace | `/counselor/` | `counselor/workspace.html` (stats, alerts, actions) |
| 54 | Case note editor | `/counselor/case-notes/<uuid>/` | `counselor/case_note.html` |
| 55 | Admin overview | `/admin-panel/` | `admin/overview.html` (KPIs + charts) |
| 56 | Users | `/admin-panel/users/` | `admin/users.html` |
| 57 | Audit logs | `/admin-panel/audit/` | `admin/audit_logs.html` |
| 58 | Reports | `/admin-panel/reports/` | `admin/reports.html` |
| 59 | Admin profile | `/admin-panel/profile/` | `admin/profile.html` |
| 60 | Receptionist | `/receptionist/` | `receptionist/booking.html` (4-step) |
| 61 | Chat overlay | include | `widgets/chatbot.html` (JS SSE) |
| 62 | States | every page | empty / loading / error / success per `INTERFACES.md` |
| 63 | Verify | count **16 routes + 1 widget**; design tokens applied |

**Admin URL note:** App admin UI uses `/admin-panel/*` so Django’s built-in admin can remain at `/admin/` (ops only). Decide before Phase 7 if you prefer swapping.

**Stitch design tokens:** `#2563EB` primary · `#0D9488` accent · `#F8FAFC` background · `#0F172A` sidebar · radius 12px cards / 8px buttons · Inter/Poppins.

---

## PHASE 8 — Audit UI, reports, metrics, polish

| # | Action | Command / output |
|---|---|---|
| 64 | Audit service | `services/audit.py` `log_action()` — never raises (port `lib/audit.ts`) |
| 65 | Signals | `post_save`/`post_delete` on Profile + CaseNote → AuditLog (port DB triggers) |
| 66 | Admin audit viewer | filters user/action/table/date + pagination |
| 67 | Reports | date/dept/concern/status filters + preview (port `actions/reports.ts`) |
| 68 | Export | CSV always; PDF via `reportlab` (replaces jsPDF) + audit `REPORT_EXPORT` |
| 69 | Metrics | KPI counts + 8-week series + concern breakdown (port `admin-metrics.ts`) |
| 70 | User management | role change + activate/deactivate; **cannot demote/deactivate self**; **last active admin guards** (port `app/admin/actions.ts`) |
| 71 | Deps | add `gunicorn`, optional `whitenoise` → `requirements.txt` |
| 72 | README | setup, env, run, test, deploy (gunicorn) + links to all `docs/` |
| 73 | Full QA | execute every flow in `FLOWS.md` §1–24; tick master checklist |

---

## Folder blueprint (end state)

```text
connectguidance_django/
├── .venv/  .env  .env.example  .gitignore  README.md  requirements.txt  manage.py
├── config/            # settings, urls, asgi, wsgi
├── docs/              # PLAN.md + ERD + FLOWS + INTERFACES + RLS_AND_SECURITY + REFERENCES
├── core/
│   ├── models.py  choices.py  guards.py  admin.py  forms.py  urls.py  apps.py
│   ├── services/      # slots, encryption, audit, appointments, case_notes,
│   │                  # mood, chat, reports, receptionist, metrics
│   ├── views/         # auth, student, counselor, admin_views, receptionist, chat
│   └── migrations/
├── templates/         # base + registration + public + student×5 + counselor×2
│                      # admin×5 + receptionist×1 + widgets/chatbot.html  (=16+overlay)
├── static/            # css/ js/
├── tests/             # one test file per phase/flow
└── scripts/           # seed data management commands
```

---

## NO-MISSING-PARTS MASTER CHECKLIST

### Data (ERD)
- [ ] 6 app models + User/Profile 1:1
- [ ] 2 choice sets (role, status) + concern_type presets
- [ ] FK rules: Appointment.counselor PROTECT; AuditLog.user SET_NULL; rest CASCADE
- [ ] UNIQUE case_notes(appointment, counselor); note ≤ 500; user_no unique
- [ ] Indexes matching Supabase migrations
- [ ] Profile auto-create on user creation (signup parity)

### Functionality (Flows)
- [ ] Edge-equivalent guards on all protected routes (24 flows)
- [ ] Slot engine 09:00–16:00 + clash window
- [ ] Status state machine (terminal states enforced)
- [ ] Student cancel rules
- [ ] Receptionist next-available loop
- [ ] Case note encrypt/upsert/integrity/confidentiality
- [ ] Mood good/okay/low + no-counselor branch
- [ ] Chat: rate limits, 36-cap, stream, persist, CTA, crisis prompt
- [ ] Auth: register/login/logout/password, 4 ROLE_HOMEs, deactivated block
- [ ] Admin: role change, activate/deactivate, last-admin + self-guards
- [ ] Audit dual-write (explicit + signals)
- [ ] Reports filters + CSV/PDF + metrics charts

### UI (Interfaces)
- [ ] 16 pages listed in Phase 7 + floating chat overlay
- [ ] Empty / loading / error / success states
- [ ] Role subnavs + design tokens

### Security (RLS port)
- [ ] Query scoping matrix in `RLS_AND_SECURITY.md` implemented in views/services
- [ ] `ENCRYPTION_KEY` server-only; never in templates
- [ ] CSRF on all POSTs; secrets only in `.env`

---

## Verification commands (per phase)

| Phase | Command |
|---|---|
| 1 | `python manage.py check` |
| 2 | `makemigrations` / `migrate` / `check` + Supabase table list |
| 3 | manual 4-role login matrix |
| 4–6 | `python manage.py test` + manual flows |
| 7 | browse 16 routes (HTTP 200 + correct template) |
| 8 | full checklist sign-off |

---

## Roadmap position

| Phase | Outcome |
|---|---|
| 1 Foundation | skeleton + Supabase config |
| 2 Models | ERD in Django |
| 3 Auth/RBAC | 4 roles work |
| 4 Appointments | booking lifecycle |
| 5 Case notes | encrypted clinical notes |
| 6 Mood + Chat | wellness + AI |
| 7 UI | 16 screens |
| 8 Ops | audit / reports / exports — **replica complete** |

---

## Companion docs index

| Doc | Read when |
|---|---|
| [ERD.md](./ERD.md) | Phase 2 — building models |
| [FLOWS.md](./FLOWS.md) | Phases 3–6, 8 — building views/services |
| [INTERFACES.md](./INTERFACES.md) | Phase 7 — building templates |
| [RLS_AND_SECURITY.md](./RLS_AND_SECURITY.md) | Phases 3, 5 — access control |
| [REFERENCES.md](./REFERENCES.md) | anytime — pointers into original Next.js repo |
