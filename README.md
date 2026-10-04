# ConnectGuidance — University Guidance & Counseling Management System

**ConnectGuidance** is a web-based University Guidance and Counseling Management System developed with Python and the Django Web Framework. Designed for university guidance offices, this application streamlines student mental health support, appointment scheduling, counselor case documentation, walk-in front desk triage, administrative reporting, and student wellness tracking.

Built following the Django Model-View-Template (MVT) architecture, the system incorporates role-based access control, cryptographic data protection for clinical notes, automated appointment conflict resolution, and comprehensive audit trails.

---

## 🌟 Key Features

### 1. Multi-Role Access Control (RBAC)
The application defines four distinct user roles, each with designated workflows, dashboards, and security boundaries:
- **Student:** Book and cancel counseling appointments, complete wellness mood check-ins, consult the automated AI guidance chatbot, view upcoming/past sessions, and update personal profile details.
- **Guidance Counselor:** Manage assigned appointments, transition session states (`confirmed`, `completed`, `cancelled`), author encrypted clinical case notes, and receive instant alerts when a student logs a low mood score.
- **Receptionist / Front Desk:** Search students by ID or name, view counselor availability across business hours, and schedule walk-in counseling appointments with automated next-available counselor assignment.
- **Administrator:** Monitor university-wide counseling KPIs, view 8-week trend analytics and concern distributions, manage user accounts with last-admin safeguards, inspect tamper-evident audit logs, and export reports in CSV and PDF formats.

### 2. Intelligent Appointment Scheduling & Conflict Protection
- Generates hourly consultation slots between 09:00 and 16:00.
- Automatic conflict detection prevents double-booking within a 50-minute buffer window.
- Strict appointment lifecycle state transitions: `pending` → `confirmed` → `completed` or `cancelled`.

### 3. Encrypted Clinical Case Notes
- Counselor case documentation is protected using server-side **AES-256** encryption before persistence to the database.
- Strictly isolated to authorized counselors and never exposed in unencrypted form to unauthorized roles or client-side scripts.

### 4. Student Wellness Mood Tracking & Alert Dispatch
- Students can submit periodic mood check-ins (`good`, `okay`, `low`).
- When a student indicates distress (`low` mood) and has an active counseling record, the system immediately flags the assigned counselor and generates an alert.

### 5. Automated AI Wellness Assistant
- Built-in conversational support with streaming responses.
- Enforces rate limiting (24 messages per 15-minute window for chat, 60 requests for session retrieval).
- Detects distress keywords and automatically recommends scheduling an in-person session with a campus guidance counselor.

### 6. Audit Logging & Administrative Safeguards
- Audit logs capture security-sensitive operations (login, role updates, appointment creation/cancellation, case note edits, and report exports).
- Admin safeguards prevent self-demotion, self-deactivation, or removing the last remaining active system administrator.

---

## 🏛️ System Architecture

```text
ConnectGuidance/
├── config/                     # Core Django configuration
│   ├── settings.py             # Application settings, database configuration, security
│   ├── urls.py                 # Top-level URL routing
│   ├── asgi.py                 # ASGI configuration
│   └── wsgi.py                 # WSGI production entrypoint
├── core/                       # Core guidance and counseling application
│   ├── models.py               # Domain models: Profile, Appointment, CaseNote, AuditLog, etc.
│   ├── choices.py              # Enumerations for roles, appointment statuses, and concern types
│   ├── guards.py               # Role-based view decorators (@role_required)
│   ├── signals.py              # Signals for automatic Profile creation and audit event logging
│   ├── forms.py                # Standard Django forms with clean validation
│   ├── services/               # Modular business logic services:
│   │   ├── admin_users.py      # Admin provisioning and safeguard rules
│   │   ├── appointments.py     # Appointment booking and state machine
│   │   ├── audit.py            # Non-blocking audit logger
│   │   ├── case_notes.py       # Encrypted case note authoring & retrieval
│   │   ├── chat.py             # Chatbot rate limits, crisis prompts, and session history
│   │   ├── encryption.py       # AES-256 cryptographic routines
│   │   ├── metrics.py          # Dashboard analytics, weekly series, and concern distributions
│   │   ├── mood.py             # Wellness check-in processing and counselor alerts
│   │   ├── receptionist.py     # Walk-in desk scheduling and student lookup
│   │   ├── reports.py          # Filtered query reports, CSV and PDF exporters
│   │   └── slots.py            # Hourly appointment slot generator and clash detection
│   └── views/                  # View handlers organized by functional domain:
│       ├── admin_views.py      # Administrator dashboard, users, audit logs, and reports
│       ├── auth.py             # User registration, authentication, and password management
│       ├── chat.py             # Wellness chatbot endpoints and session persistence
│       ├── counselor.py        # Counselor workspace, appointments, and case notes
│       ├── receptionist.py     # Front-desk walk-in appointment scheduling
│       └── student.py          # Student dashboard, booking, and profile
├── static/                     # CSS stylesheets, JavaScript helpers, and assets
│   ├── css/app.css             # Unified application styles and theme
│   └── js/                     # Dynamic frontend interactions
├── templates/                  # Django HTML templates (MVT layout)
│   ├── base.html               # Main base template with navigation and alert messages
│   ├── common/                 # Public landing screens
│   ├── authentication/         # Login, registration, and password change screens
│   ├── student/                # Student portal templates
│   ├── counselor/              # Counselor workspace and case note templates
│   ├── receptionist/           # Front desk booking interface
│   ├── analytics/              # Admin dashboard metrics and reports
│   ├── users/                  # User management and profile screens
│   ├── audit/                  # Audit log browser
│   └── widgets/                # Reusable template components (wellness chatbot widget)
├── tests/                      # Automated test suite
└── manage.py                   # Django management utility
```

---

## 👥 Role Directory & Default Routes

| Role | Default Portal Route | Primary Functions |
|---|---|---|
| **Student** | `/student/` | Book appointments, mood check-ins, AI wellness chat, view session history. |
| **Counselor** | `/counselor/` | Daily schedule, appointment confirmation/completion, confidential case notes, student mood alerts. |
| **Receptionist** | `/receptionist/` | Student lookup, front desk walk-in scheduling, automatic next-available counselor matching. |
| **Administrator** | `/admin-panel/` | System analytics, user account management, audit logs, PDF & CSV report exports. |

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12
- Git

### 2. Environment Setup

```powershell
# Navigate to the project root directory
cd ConnectGuidance

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1    # On Windows PowerShell
# source .venv/bin/activate     # On Linux / macOS
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configuration

Copy `.env.example` to `.env` (or run with default SQLite configuration for local testing):

```powershell
Copy-Item .env.example .env
```

Key environment variables in `.env`:
```ini
DJANGO_SECRET_KEY=your-secure-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
ENCRYPTION_KEY=your-32-byte-hex-or-base64-encryption-key
```

### 5. Apply Database Migrations

```powershell
python manage.py migrate
```

### 6. Seed Demo Test Accounts

The project includes a management command to populate the database with default test accounts across all roles:

```powershell
python manage.py seed_roles
```

#### Default Test Credentials:

| Role | Email / Username | Password |
|---|---|---|
| **Administrator** | `admin@guidance.edu` | `AdminPassword123!` |
| **Counselor 1** | `counselor@guidance.edu` | `CounselorPassword123!` |
| **Counselor 2** | `counselor2@guidance.edu` | `CounselorPassword123!` |
| **Receptionist** | `receptionist@guidance.edu` | `ReceptionPassword123!` |
| **Student 1** | `student@university.edu` | `StudentPassword123!` |
| **Student 2** | `student2@university.edu` | `StudentPassword123!` |

### 7. Run the Automated Test Suite

```powershell
python manage.py test
```

### 8. Run the Development Server

```powershell
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your web browser.

---

## 🔒 Security Best Practices

- **CSRF Protection:** All form submissions are protected with Django's standard CSRF tokens.
- **Password Hashing:** Passwords are encrypted using Django's default PBKDF2 with SHA-256 hashing.
- **SQL Injection Prevention:** Queries utilize the Django Object-Relational Mapper (ORM) with parameterized queries.
- **Role Enforcement:** Access controls are validated on every request via Python decorators (`@role_required`) verifying session data against database records.
- **Data Encryption:** Clinical notes are encrypted at rest with AES-256.

---

## 📄 Academic Project Attribution

Developed as a senior capstone project for university guidance and counseling management.
Built with Python and Django.
