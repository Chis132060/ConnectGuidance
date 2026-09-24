# GuidanceConnect — Django Enterprise Replica

A feature-complete, production-grade Django web application replica of **GuidanceConnect** (originally built with Next.js & Supabase). This system provides end-to-end guidance counseling management, clinical appointment scheduling, AES-256 encrypted case notes, an AI-powered wellness chatbot with real-time SSE streaming and crisis protocols, role-based access control (RBAC) across four distinct roles, an executive analytics suite, and tamper-evident audit logging.

---

## 📚 Master Documentation Index

All architectural blueprints, system flowcharts, and technical specifications are documented in the [`docs/`](docs/) directory:

| Document | Description |
|---|---|
| [**`docs/PLAN.md`**](docs/PLAN.md) | Master 8-phase execution plan (73 steps) with 50-item No-Missing-Parts checklist. |
| [**`docs/FLOWS.md`**](docs/FLOWS.md) | Complete flowcharts for all 24 system flows (happy paths, edge guards, and error branches). |
| [**`docs/INTERFACES.md`**](docs/INTERFACES.md) | Exact specifications for all 16 screen templates + floating chat widget overlay. |
| [**`docs/ERD.md`**](docs/ERD.md) | Relational schema definitions, constraints, indexes, and field-level specifications. |
| [**`docs/RLS_AND_SECURITY.md`**](docs/RLS_AND_SECURITY.md) | Query-scoping matrix (Supabase RLS ported to Django ORM), cryptographic standards, and rate limits. |
| [**`docs/AUDIT_LOG.md`**](docs/AUDIT_LOG.md) | Comprehensive record of phase-by-phase implementation actions and validation metrics. |
| [**`docs/REMAINING_STEPS.md`**](docs/REMAINING_STEPS.md) | Execution tracker detailing completion milestones across all phases. |
| [**`docs/REFERENCES.md`**](docs/REFERENCES.md) | Mapping matrix between the original Next.js codebase and this Django replica. |

---

## 🏛️ System Architecture

```text
connectguidance_django/
├── .venv/                      # Isolated virtual environment
├── config/                     # Core Django project configuration
│   ├── settings.py             # Settings, DB config, authentication, and security headers
│   ├── urls.py                 # Top-level URL routing (including admin-panel and auth)
│   ├── asgi.py                 # ASGI entrypoint
│   └── wsgi.py                 # WSGI entrypoint (for Gunicorn production)
├── core/                       # Primary guidance application
│   ├── models.py               # 6 domain models + User/Profile 1:1 relationship
│   ├── choices.py              # RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
│   ├── guards.py               # Edge-equivalent RBAC route decorators (@require_role, etc.)
│   ├── signals.py              # Profile auto-create & AuditLog triggers (insert/update/delete)
│   ├── admin.py                # Django administrative interface configuration
│   ├── services/               # Clean service layer (thin views call services):
│   │   ├── admin_users.py      # User creation, role change & status toggle with safeguards
│   │   ├── appointments.py     # Appointment booking, cancellation, state machine transitions
│   │   ├── audit.py            # Non-raising append-only audit trail logging
│   │   ├── case_notes.py       # Encrypted clinical note authoring, retrieval & verification
│   │   ├── chat.py             # SSE streaming generator, 36-cap, crisis prompt, CTA detection
│   │   ├── encryption.py       # AES-256-CBC encryption + backward-compatible gc:v1 GCM
│   │   ├── metrics.py          # KPIs, 8-week Monday-start series, top-8 concern breakdown
│   │   ├── mood.py             # Wellness check-in logging & low-mood counselor alerts
│   │   ├── receptionist.py     # Next-available slot engine & in-person walk-in booking
│   │   ├── reports.py          # Filtered appointment reports, RFC-4180 CSV & ReportLab PDF
│   │   └── slots.py            # 09:00–16:00 slot generator (12:00 lunch excluded) & clash checks
│   └── views/                  # HTTP route adapters:
│       ├── admin_views.py      # Overview, users, audit log viewer, reports, profile
│       ├── auth.py             # Login, register, logout, password change
│       ├── chat.py             # Real-time SSE streaming endpoint & session hydration
│       ├── counselor.py        # Workspace, status updates, case notes, mood alerts
│       ├── receptionist.py     # 4-step walk-in appointment booking workflow
│       └── student.py          # Dashboard, appointment booking/cancellation, profile, front-desk
├── static/                     # Design tokens & client assets
│   ├── css/app.css             # Stitch UI tokens (#2563EB, #0D9488, #0F172A, #F8FAFC)
│   └── js/                     # Client-side dynamic slot booking & Chart.js charts
├── templates/                  # 16 Semantic screens + 1 global floating chatbot overlay
│   ├── base.html               # Persistent layout with role-aware subnavs & toast alerts
│   ├── public/                 # Landing screen
│   ├── registration/           # Login, registration, password update
│   ├── student/                # Dashboard, booking, appointments, profile, front-desk, chatbot
│   ├── counselor/              # Counselor workspace & encrypted case note editor
│   ├── receptionist/           # Walk-in booking screen
│   ├── admin/                  # Analytics overview, user management, audit logs, reports, profile
│   └── widgets/chatbot.html    # Global floating AI wellness chatbot widget (FAB + SSE stream)
├── tests/                      # Full-stack automated test suite (58+ test cases)
│   ├── test_auth_guards.py     # Role-based guards and authentication
│   ├── test_slots.py           # Slot generator, business hours & clash detection
│   ├── test_appointments.py    # Appointment lifecycle & cancellation rules
│   ├── test_case_notes.py      # AES-256 encryption, access control & integrity
│   ├── test_mood_chat.py       # Mood check-ins, counselor alerts & SSE chat stream
│   ├── test_views_http.py      # HTTP 200 checks across all 16 screen routes
│   └── test_admin_safeguards.py# Admin RBAC safeguards, metrics, CSV/PDF reports & signals
└── manage.py
```

---

## 👥 Role Matrix & Routing

| Role | Default Route (`ROLE_HOME`) | Capabilities |
|---|---|---|
| **Student** | `/student/` | Book/cancel appointments, submit mood check-ins, chat with wellness AI, view history, manage profile. |
| **Counselor** | `/counselor/` | Manage appointments, update statuses (confirm/complete/cancel/no-show), write encrypted case notes, review mood alerts. |
| **Receptionist** | `/receptionist/` | Book walk-in appointments on behalf of students with automatic next-available slot resolution. |
| **Administrator** | `/admin-panel/` | Executive KPI analytics, user management with demotion/deactivation safeguards, audit log viewer, custom PDF/CSV report generation. |

---

## 🔒 Security & Data Protection

- **Encrypted Case Notes:** All counselor clinical notes are encrypted using **AES-256-CBC** (with legacy support for `gc:v1:` AES-GCM ciphertexts). Encryption keys are strictly server-side and never exposed to templates or client JavaScript.
- **Admin Safeguards:**
  - An administrator cannot demote or deactivate their own account.
  - The system blocks demoting or deactivating the last remaining active administrator account.
- **Audit Logging Dual-Write:** Every critical action (auth, role changes, appointments, case notes, report exports) is logged via both explicit service calls and Django signals (`post_save`/`post_delete`). Audit logging is non-raising to ensure primary transaction integrity.
- **AI Rate Limiting & Safety:** Chat endpoints enforce strict rate limits (24 messages per 15 minutes), 36-message session caps, input sanitization, automated appointment booking CTA suggestions, and emergency crisis intervention prompts.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- PostgreSQL database (or Supabase PostgreSQL instance)
- Git

### 2. Clone and Setup Environment

```powershell
# Clone the repository
git clone <repo-url> connectguidance_django
cd connectguidance_django

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Windows
# source .venv/bin/activate    # On Linux/macOS
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your configuration:

```powershell
Copy-Item .env.example .env
```

Key variables in `.env`:
```ini
DJANGO_SECRET_KEY=your-secure-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
ENCRYPTION_KEY=64-char-hex-or-base64-32-byte-key
AI_API_KEY=your-groq-or-anthropic-api-key
AI_PROVIDER=groq
```

### 5. Apply Migrations

```powershell
python manage.py makemigrations
python manage.py migrate
```

### 6. Run the Test Suite

```powershell
python manage.py test
```

### 7. Start the Development Server

```powershell
python manage.py runserver
```

Open your browser at `http://127.0.0.1:8000/`.

---

## 🚢 Production Deployment

For production deployments (e.g. on Linux servers, Render, Fly.io, AWS, or Railway):

1. **Set Environment Variables:**
   - Set `DJANGO_DEBUG=False`.
   - Set `DJANGO_ALLOWED_HOSTS` to your production domain(s).
   - Provide a strong `DJANGO_SECRET_KEY` and `ENCRYPTION_KEY`.

2. **Collect Static Files:**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Run with Gunicorn:**
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
   ```

---

## 📄 License & Attribution

Developed as an enterprise-grade Django educational guidance counseling platform replica of GuidanceConnect.
