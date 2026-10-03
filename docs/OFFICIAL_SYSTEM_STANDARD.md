# CONNECTGUIDANCE OFFICIAL SYSTEM STANDARD
**Version:** 1.0  
**Date:** October 2, 2026  
**Status:** Phase 0 Architecture Audit — Standardization Document  
**Project:** ConnectGuidance University Guidance & Counseling Platform

---

## DOCUMENT PURPOSE

This document establishes the **OFFICIAL, AUTHORITATIVE STANDARD** for ConnectGuidance. It defines:

1. **System Architecture** — folder structure, feature organization, migration status
2. **Role Definitions** — exact permissions and responsibilities for all 4 user roles
3. **Feature × Role Matrix** — what each role can/cannot access
4. **Navigation Standards** — consistent sidebar and routing patterns
5. **Security & Access Control** — authentication guards, RLS, audit requirements
6. **UI/UX Standards** — design system, minimal CSS approach, consistency rules
7. **Testing Standards** — test organization, coverage requirements
8. **Documentation Standards** — file structure, update protocols
9. **Code Quality Standards** — naming conventions, service patterns, view organization
10. **Migration Roadmap** — completed steps, current status, remaining work

**CRITICAL:** This is NOT a redesign. This is NOT a rewrite. This documents the CURRENT system state and establishes standards for future development.

---

## 1. SYSTEM ARCHITECTURE

### 1.1 Current Project Structure

```
ConnectGuidance/
├── config/                          # Django project settings
│   ├── settings/
│   │   ├── base.py                 # Base settings
│   │   ├── development.py          # Dev overrides
│   │   ├── production.py           # Production overrides
│   │   └── testing.py              # Test overrides
│   ├── urls.py                     # Root URL configuration
│   └── wsgi.py
│
├── apps/                            # Feature-first applications (NEW)
│   ├── analytics/                  # ✅ MIGRATED — Admin metrics & reports
│   │   ├── services/
│   │   │   ├── metrics.py         # KPI calculations
│   │   │   └── reports.py         # Export logic (CSV/PDF)
│   │   ├── templates/analytics/
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests.py
│   │
│   ├── audit/                      # ✅ MIGRATED — Audit logging
│   │   ├── services/
│   │   │   └── logger.py          # Audit log service
│   │   ├── templates/audit/
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests.py
│   │
│   ├── authentication/             # ✅ MIGRATED — Auth & registration
│   │   ├── guards.py              # Role-based decorators
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests.py
│   │
│   ├── users/                      # ✅ MIGRATED — User management
│   │   ├── services/
│   │   │   └── management.py      # User CRUD, role changes
│   │   ├── templates/users/
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests.py
│   │
│   ├── common/                     # ✅ MIGRATED — Shared utilities
│   │   ├── choices.py             # Enums (Roles, Status, Concerns)
│   │   ├── templates/common/
│   │   │   └── base.html          # Role-aware base template
│   │   └── utils.py
│   │
│   ├── appointments/               # ⏳ PENDING MIGRATION
│   ├── case_notes/                 # ⏳ PENDING MIGRATION
│   └── wellness/                   # ⏳ PENDING MIGRATION
│
├── core/                            # ⚠️ MONOLITHIC APP (Being Decomposed)
│   ├── models.py                   # 6 models (staying here)
│   ├── services/                   # Business logic
│   │   ├── appointments.py        # Booking, cancellation, status
│   │   ├── case_notes.py          # Note encryption/decryption
│   │   ├── chat.py                # Chatbot rate limits, crisis detection
│   │   ├── encryption.py          # Fernet encryption utilities
│   │   ├── mood.py                # Wellness check-in processing
│   │   ├── receptionist.py        # Student search, walk-in booking
│   │   └── slots.py               # Availability calculation
│   │
│   ├── views/                      # Feature views (will be migrated)
│   │   ├── student.py             # Student dashboard, appointments, mood
│   │   ├── counselor.py           # Workspace, status updates, case notes
│   │   ├── receptionist.py        # Desk dashboard, search, booking
│   │   └── chat.py                # Chatbot UI & API
│   │
│   ├── forms.py                    # Django forms
│   ├── admin.py                    # Django admin customization
│   ├── urls.py                     # Core feature routing
│   └── signals.py                  # Django signals
│
├── templates/                       # Global templates
│   ├── base.html                   # Public base template
│   ├── student/                    # Student role templates
│   │   ├── dashboard.html
│   │   ├── appointments.html
│   │   ├── profile.html
│   │   └── front_desk.html
│   ├── counselor/                  # Counselor role templates
│   │   └── workspace.html
│   ├── receptionist/               # Receptionist role templates
│   │   └── dashboard.html
│   ├── admin/                      # Admin templates (EMPTY — using apps/)
│   ├── partials/                   # Shared navigation components
│   │   ├── student_subnav.html
│   │   ├── counselor_subnav.html
│   │   ├── admin_subnav.html
│   │   └── receptionist_subnav.html
│   ├── public/                     # Landing & info pages
│   ├── registration/               # Login/register pages
│   └── widgets/                    # Reusable components
│       └── chatbot.html
│
├── static/                          # Static assets
│   └── css/
│       └── minimal.css             # Minimal design system (no gradients/shadows)
│
├── tests/                           # Test suite (81 tests passing)
│   ├── integration/
│   ├── test_admin_safeguards.py
│   ├── test_appointments.py
│   ├── test_auth_guards.py
│   ├── test_case_notes.py
│   ├── test_mood_chat.py
│   ├── test_slots.py
│   └── test_views_http.py
│
└── docs/                            # Documentation
    ├── ERD.md                      # Entity-Relationship Diagram
    ├── FLOWS.md                    # User flows by role
    ├── INTERFACES.md               # Screen-by-screen specs
    ├── PLAN.md                     # Original project plan
    ├── RLS_AND_SECURITY.md         # Security & RLS policies
    └── OFFICIAL_SYSTEM_STANDARD.md # This document
```

### 1.2 Architecture Migration Status

**Completed Steps (Steps 0–6C):**
- ✅ Step 0: Baseline test suite (70 tests → 81 tests now)
- ✅ Step 1-4: Foundation (settings split, common code, static reorganization)
- ✅ Step 5: Authentication feature extracted to `apps/authentication/`
- ✅ Step 6A: Audit feature extracted to `apps/audit/`
- ✅ Step 6B: Analytics feature extracted to `apps/analytics/`
- ✅ Step 6C: Users feature extracted to `apps/users/`

**Current Status:**
- 🛑 **PAUSED** for Phase 0 Standardization Audit (this document)
- All tests passing: **81/81** ✅
- Server running: `http://127.0.0.1:8000/`
- Branch: `feature/architecture-migration`

**Pending Migration (Steps 6D–6F):**
- ⏳ Step 6D: Case Notes → `apps/case_notes/`
- ⏳ Step 6E: Wellness/Mood → `apps/wellness/`
- ⏳ Step 6F: Appointments → `apps/appointments/`

**Architectural Decisions:**
1. **Models stay in `core/models.py`** — No model migration to avoid data risk
2. **Services migrated with features** — Business logic moves to feature apps
3. **Views migrated with features** — Each app owns its views
4. **Templates organized by role** — Role-specific template folders
5. **URL routing decentralized** — Each app has its own `urls.py`

---

## 2. ROLE DEFINITIONS & PERMISSIONS

### 2.1 Role Overview

ConnectGuidance has **EXACTLY 4 ROLES**:

| Role | Database Value | Purpose | Home URL |
|------|---------------|---------|----------|
| **Student** | `student` | Schedule appointments, access wellness tools, view case notes | `/student/` |
| **Counselor** | `counselor` | Manage appointments, write case notes, monitor alerts | `/counselor/` |
| **Receptionist** | `receptionist` | Walk-in booking, student search, front desk triage | `/receptionist/` |
| **Admin** | `admin` | User management, system analytics, audit logs, reports | `/admin-panel/` |

### 2.2 Role-Based Access Control (RBAC)

**Authentication Guards** (`apps/authentication/guards.py`):

```python
@require_student        # Allows ONLY Student role
@require_counselor      # Allows ONLY Counselor role
@require_receptionist   # Allows ONLY Receptionist role
@require_admin          # Allows ONLY Admin role
```

**Guard Behavior:**
1. Unauthenticated → Redirect to `/login/?next={path}`
2. No profile → Logout + redirect to `/login/?error=no_profile`
3. Inactive account → Logout + redirect to `/login/?error=deactivated`
4. Wrong role → Redirect to role home URL

**Role Home URLs:**
```python
ROLE_HOMES = {
    'admin': '/admin-panel/',
    'counselor': '/counselor/',
    'student': '/student/',
    'receptionist': '/receptionist/',
}
```

---

## 3. FEATURE × ROLE MATRIX

### 3.1 Student Permissions

**WHAT STUDENTS CAN DO:**
- ✅ Book appointments with counselors
- ✅ View their own appointments (upcoming & past)
- ✅ Cancel their own pending/confirmed appointments
- ✅ Submit daily mood/wellness check-ins
- ✅ View non-confidential case notes written by counselors
- ✅ Chat with AI wellness assistant (24/7, rate-limited)
- ✅ View front desk information (hours, locations, contact)
- ✅ Update their own password
- ✅ View their profile (read-only: email, student ID, department)

**WHAT STUDENTS CANNOT DO:**
- ❌ See other students' appointments or data
- ❌ Modify appointment status (only cancel)
- ❌ Access counselor workspace
- ❌ Access receptionist desk
- ❌ Access admin panel
- ❌ Create or modify user accounts
- ❌ View audit logs
- ❌ Export reports
- ❌ View confidential case notes

**Student Navigation:**
```
Dashboard              → /student/
My Appointments        → /appointments/
Book Appointment       → /appointments/book/
AI Chatbot             → /chatbot/
Front Desk Info        → /student/front-desk/
Profile & Password     → /student/profile/
```

### 3.2 Counselor Permissions

**WHAT COUNSELORS CAN DO:**
- ✅ View all appointments assigned to them (today, pending, upcoming, completed)
- ✅ Confirm pending appointment requests
- ✅ Cancel appointments
- ✅ Mark appointments as completed
- ✅ Write case notes (encrypted, confidential/non-confidential)
- ✅ View student mood alerts (low mood triggers)
- ✅ Access their own workspace dashboard
- ✅ Update their own password

**WHAT COUNSELORS CANNOT DO:**
- ❌ View appointments assigned to other counselors
- ❌ View confidential case notes written by other counselors
- ❌ Book appointments on behalf of students (receptionist-only)
- ❌ Access student dashboard
- ❌ Access receptionist desk
- ❌ Access admin panel
- ❌ Create or modify user accounts
- ❌ View system-wide analytics
- ❌ Export reports
- ❌ View audit logs

**Counselor Navigation:**
```
Workspace              → /counselor/
(Appointment status updates inline)
(Case note creation inline from workspace)
Profile & Password     → (not yet implemented — TBD)
```

### 3.3 Receptionist Permissions

**WHAT RECEPTIONISTS CAN DO:**
- ✅ View front desk dashboard
- ✅ Search for students by name, ID, or email
- ✅ Book walk-in appointments on behalf of students
- ✅ View available counselor slots
- ✅ Access front desk protocols

**WHAT RECEPTIONISTS CANNOT DO:**
- ❌ Modify appointment status (counselors-only)
- ❌ Write case notes
- ❌ View case notes
- ❌ View mood alerts
- ❌ Access student dashboard
- ❌ Access counselor workspace
- ❌ Access admin panel
- ❌ Create or modify user accounts
- ❌ View audit logs
- ❌ Export reports

**Receptionist Navigation:**
```
Dashboard              → /receptionist/
Search Students        → /receptionist/search-students/
Book Walk-In           → /receptionist/book/
Profile & Password     → (not yet implemented — TBD)
```

### 3.4 Admin Permissions

**WHAT ADMINS CAN DO:**
- ✅ View executive dashboard with KPIs (students, counselors, appointments, completion rate)
- ✅ View 8-week appointment trend charts
- ✅ View concern type distribution
- ✅ Create new user accounts (all roles)
- ✅ Modify user roles (student ↔ counselor ↔ receptionist ↔ admin)
- ✅ Activate/deactivate user accounts
- ✅ Search/filter users by name, ID, email, role, status
- ✅ View audit logs (all system actions)
- ✅ Generate appointment reports (filter by date, counselor, concern, status)
- ✅ Export reports (CSV & PDF)
- ✅ Update their own password

**WHAT ADMINS CANNOT DO:**
- ❌ Book appointments on behalf of students (receptionist-only)
- ❌ Write case notes (counselor-only)
- ❌ View encrypted case note content (counselor-only, encryption enforced)
- ❌ Access student dashboard
- ❌ Access counselor workspace
- ❌ Access receptionist desk
- ❌ Directly modify appointments (must use appropriate role)

**Admin Navigation:**
```
Overview Dashboard     → /admin-panel/
User Management        → /admin-panel/users/
Appointment Reports    → /admin-panel/reports/
Audit Logs             → /admin-panel/audit/
Profile & Password     → /admin-panel/profile/
```

---

## 4. NAVIGATION STANDARDS

### 4.1 Sidebar Structure

**Base Template:** `templates/base.html`  
**Partial Templates:** `templates/partials/{role}_subnav.html`

**Sidebar Behavior:**
- ✅ Collapsible with localStorage persistence (`cg_sidebar_collapsed`)
- ✅ Role-specific navigation via `{% include "partials/{role}_subnav.html" %}`
- ✅ White background (minimal design, no dark mode)
- ✅ User chip at bottom with avatar, name, role, sign-out

**Toggle Icon States:**
- Sidebar open → Show `panel-left-close` icon
- Sidebar collapsed → Show `panel-left-open` icon

### 4.2 URL Routing Patterns

**Authentication Routes** (`apps/authentication/urls.py`):
```
/                       → Landing page (public)
/login/                 → Login form
/register/              → Student registration
/logout/                → Sign out
/role-home/             → Role-based redirect
```

**Core Feature Routes** (`core/urls.py`):
```
/student/               → Student dashboard
/appointments/          → Student appointments list
/appointments/slots/    → Available slots API
/appointments/book/     → Booking form
/chatbot/               → AI chatbot UI
/counselor/             → Counselor workspace
/receptionist/          → Receptionist desk
```

**Admin Routes** (`apps/analytics/urls.py`, `apps/users/urls.py`, `apps/audit/urls.py`):
```
/admin-panel/           → Admin overview dashboard
/admin-panel/users/     → User management
/admin-panel/reports/   → Appointment reports
/admin-panel/audit/     → Audit logs
/admin-panel/profile/   → Admin profile
```

### 4.3 Route Guard Patterns

Every view MUST use a role guard:

```python
# Student views
@require_student
def student_dashboard_view(request):
    ...

# Counselor views
@require_counselor
def counselor_workspace_view(request):
    ...

# Receptionist views
@require_receptionist
def receptionist_dashboard_view(request):
    ...

# Admin views
@require_admin
def admin_overview_view(request):
    ...
```

**NO PUBLIC ACCESS** to authenticated features. All feature views require authentication + role check.

---

## 5. SECURITY & ACCESS CONTROL

### 5.1 Authentication Requirements

**All authenticated views MUST:**
1. Use `@require_{role}` decorator
2. Verify `request.user.is_authenticated`
3. Check `request.user.profile.is_active`
4. Enforce role-based URL access

**Inactive Accounts:**
- Logged out immediately upon access attempt
- Redirected to `/login/?error=deactivated`
- Cannot authenticate until reactivated by Admin

### 5.2 Row-Level Security (RLS)

**Students:**
- Can ONLY see their own appointments
- Can ONLY see their own non-confidential case notes
- Can ONLY cancel their own pending/confirmed appointments
- Filter: `Appointment.objects.filter(student=request.user.profile)`

**Counselors:**
- Can ONLY see appointments assigned to them
- Can ONLY write case notes for their own appointments
- Can ONLY update status for their own appointments
- Filter: `Appointment.objects.filter(counselor=request.user.profile)`

**Receptionists:**
- Can search all students
- Can book appointments for any student
- NO access to case notes or mood alerts

**Admins:**
- Can view all users (search, filter, manage)
- Can view aggregate analytics
- Can view all audit logs
- CANNOT access encrypted case note content (enforced by encryption key)

### 5.3 Data Encryption

**Case Notes Encryption:**
- Service: `core/services/encryption.py`
- Algorithm: Fernet symmetric encryption
- Key source: `settings.CASE_NOTE_ENCRYPTION_KEY`
- Encrypted fields: `CaseNote.encrypted_content`

**Encryption Rules:**
1. All case notes are encrypted at rest
2. Decryption only via `get_decrypted_case_note()` service
3. Confidential notes: ONLY counselor who wrote them can decrypt
4. Non-confidential notes: Student + original counselor can decrypt
5. Admins CANNOT decrypt case notes (no access to decryption service)

### 5.4 Audit Logging

**Audit Service:** `apps/audit/services/logger.py`

**Logged Actions:**
```python
def log_action(user: Profile, action: str, target: str = None, details: dict = None)
```

**Required Audit Events:**
- User creation, role change, status change (Admin)
- Appointment booking, cancellation, status updates
- Case note creation
- Mood alert triggers
- Report exports (CSV/PDF)
- Login/logout attempts

**Audit Log Fields:**
- `user` — Who performed the action
- `action` — What they did (verb phrase)
- `target` — What entity was affected
- `details` — JSON metadata
- `created_at` — Timestamp
- `ip_address` — Client IP

**Audit View Access:**
- Admin-only: `/admin-panel/audit/`
- Filterable by user, action, date range
- Read-only (no deletion allowed)

---

## 6. UI/UX STANDARDS

### 6.1 Minimal Design System

**Design Philosophy:**
- Clean, professional, accessible
- NO gradients, NO shadows, NO animations
- White backgrounds, simple borders
- Minimal color palette

**CSS File:** `static/css/minimal.css`

**Color Palette:**
```css
--c-primary: #2563eb;        /* Primary blue */
--c-primary-hover: #1d4ed8;
--c-text: #1e293b;           /* Dark text */
--c-muted: #64748b;          /* Muted gray */
--c-border: #e2e8f0;         /* Light border */
--c-bg: #f8fafc;             /* Background gray */
--c-surface: #ffffff;        /* Card surface */
```

**Component Classes:**
```css
.card-minimal                 /* White card, 1px border, 8px radius */
.btn                          /* Base button */
.btn-primary                  /* Primary action */
.btn-secondary                /* Secondary action */
.btn-sm                       /* Small button */
.form-group                   /* Form field wrapper */
.badge-confirmed              /* Green badge */
.badge-pending                /* Yellow badge */
.badge-cancelled              /* Red badge */
.badge-completed              /* Gray badge */
```

### 6.2 Sidebar Design

**Sidebar Styles:**
- Background: `#ffffff` (white)
- Border: `1px solid #e2e8f0`
- Width: `260px` (open), `72px` (collapsed)
- Position: Fixed left
- Z-index: 1000

**No Dark Mode:** White sidebar only (user requested removal of dark theme)

### 6.3 Responsive Behavior

**Breakpoints:**
- Desktop: `≥1024px` — Full sidebar + main content
- Tablet/Mobile: `<1024px` — Sidebar collapses by default

**Mobile Considerations:**
- All tables must be horizontally scrollable
- Card grids collapse to single column
- Buttons stack vertically

### 6.4 Accessibility (WCAG 2.1)

**Requirements:**
- ✅ All interactive elements keyboard-accessible
- ✅ Color contrast ratio ≥4.5:1 for normal text
- ✅ ARIA labels on icon buttons
- ✅ Semantic HTML (`<nav>`, `<main>`, `<header>`)
- ✅ Form labels properly associated with inputs
- ⚠️ Full WCAG validation requires manual testing with assistive tech

---

## 7. TESTING STANDARDS

### 7.1 Test Organization

**Test Location:** `tests/`

**Test Files:**
```
tests/
├── integration/                  # Integration test suite
├── test_admin_safeguards.py     # Admin permission tests
├── test_appointments.py          # Appointment booking/cancellation
├── test_auth_guards.py          # Role-based access control
├── test_case_notes.py           # Case note encryption/permissions
├── test_mood_chat.py            # Wellness & chatbot
├── test_slots.py                # Slot availability
└── test_views_http.py           # HTTP view responses
```

**Current Status:** 81/81 tests passing ✅

### 7.2 Test Coverage Requirements

**Required Test Types:**
1. **Unit Tests** — Business logic in `core/services/`
2. **Integration Tests** — Multi-step workflows
3. **Permission Tests** — Role-based access enforcement
4. **HTTP Tests** — View responses, redirects, status codes

**Coverage Targets:**
- Services: 100% (critical business logic)
- Views: ≥80% (authenticated paths)
- Models: ≥70% (validation logic)

### 7.3 Running Tests

**Commands:**
```bash
# Run all tests
python manage.py test

# Run specific test file
python manage.py test tests.test_appointments

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

**Test Database:** Separate SQLite database auto-created during test runs

---

## 8. DOCUMENTATION STANDARDS

### 8.1 Documentation Files

**Required Docs:**
- ✅ `README.md` — Project overview, setup instructions
- ✅ `docs/ERD.md` — Entity-Relationship Diagram
- ✅ `docs/FLOWS.md` — User flows by role
- ✅ `docs/INTERFACES.md` — Screen-by-screen specifications
- ✅ `docs/PLAN.md` — Original project plan
- ✅ `docs/RLS_AND_SECURITY.md` — Security policies
- ✅ `docs/OFFICIAL_SYSTEM_STANDARD.md` — This document

### 8.2 Code Documentation

**Python Docstrings:**
```python
def function_name(param: Type) -> ReturnType:
    """
    Brief description.
    
    Implements FLOWS §X or INTERFACES #Y.
    
    Args:
        param: Description
        
    Returns:
        Description
        
    Raises:
        ValidationError: When validation fails
    """
```

**View Docstrings MUST Reference:**
- FLOWS section number (if applicable)
- INTERFACES screen number (if applicable)
- URL pattern
- Allowed roles

---

## 9. CODE QUALITY STANDARDS

### 9.1 Service Layer Patterns

**Location:** `core/services/` (will migrate to feature apps)

**Service Function Signature:**
```python
def service_function(
    actor: Profile,
    target: Model,
    data: dict
) -> Model:
    """Service description."""
    # 1. Validate inputs
    # 2. Check permissions
    # 3. Perform business logic
    # 4. Log audit event
    # 5. Return result
```

**Error Handling:**
- Use `ValidationError` for business rule violations
- Use `PermissionDenied` for authorization failures
- Always provide user-friendly error messages

### 9.2 View Patterns

**Function-Based Views (Current Standard):**
```python
from apps.authentication.guards import require_role

@require_role
@require_http_methods(["GET", "POST"])
def view_function(request):
    """View description."""
    user_profile = request.user.profile
    
    if request.method == 'POST':
        # Handle form submission
        # Call service layer
        # Add messages
        # Redirect
    
    # GET: Prepare context
    context = {...}
    return render(request, 'path/template.html', context)
```

### 9.3 Naming Conventions

**Views:**
- `{role}_{feature}_{action}_view` → `student_appointments_list_view`

**Services:**
- `{verb}_{noun}` → `book_appointment`, `cancel_appointment`

**URLs:**
- `{role}_{feature}_{action}` → `student_appointments`, `counselor_workspace`

**Templates:**
- `{role}/{feature}.html` → `student/dashboard.html`

### 9.4 Import Order

```python
# 1. Standard library
import datetime
from typing import List, Dict

# 2. Django imports
from django.shortcuts import render, redirect
from django.contrib import messages

# 3. Local app imports
from apps.authentication.guards import require_student
from core.models import Appointment
from core.services.appointments import book_appointment
```

---

## 10. MIGRATION ROADMAP

### 10.1 Completed Work

**Phase 1: Foundation (Steps 0-4)** ✅
- Settings split (base/dev/prod/testing)
- Common app created
- Static files reorganized
- Baseline tests: 70 → 81

**Phase 2: Feature Extraction (Steps 5-6C)** ✅
- Authentication → `apps/authentication/`
- Audit → `apps/audit/`
- Analytics → `apps/analytics/`
- Users → `apps/users/`

### 10.2 Current Phase

**Phase 0: Standardization Audit** 🔄 IN PROGRESS
- 🛑 All code changes PAUSED
- 📋 This document created
- ⏳ Awaiting user approval
- ⏳ No Step 6D until approved

### 10.3 Remaining Work

**Phase 2 Continuation (Steps 6D-6F)** ⏳ BLOCKED
- Step 6D: Case Notes → `apps/case_notes/`
  - Extract `core/services/case_notes.py`
  - Extract `core/views/counselor.py` (case note views)
  - Create `apps/case_notes/views.py`, `urls.py`, `tests.py`
  
- Step 6E: Wellness → `apps/wellness/`
  - Extract `core/services/mood.py`
  - Extract `core/views/student.py` (mood check-in)
  - Create `apps/wellness/views.py`, `urls.py`, `tests.py`
  
- Step 6F: Appointments → `apps/appointments/`
  - Extract `core/services/appointments.py`, `slots.py`
  - Extract `core/views/student.py` (booking views)
  - Extract `core/views/counselor.py` (status updates)
  - Create `apps/appointments/views.py`, `urls.py`, `tests.py`

**Phase 3: Cleanup** ⏳ NOT STARTED
- Remove empty `core/views/` directory
- Remove empty `core/services/` directory
- Update documentation
- Final test verification

---

## 11. DATA MODEL REFERENCE

### 11.1 Models (core/models.py)

**6 Models (NO MIGRATION PLANNED):**

1. **Profile** (User extension)
   - `user` (OneToOne → Django User)
   - `role` (student/counselor/receptionist/admin)
   - `full_name`, `student_id`, `department`
   - `is_active` (account status)
   - `user_no` (auto-incrementing display ID)

2. **Appointment**
   - `student` (FK → Profile)
   - `counselor` (FK → Profile)
   - `scheduled_at` (datetime)
   - `status` (pending/confirmed/cancelled/completed)
   - `concern_type` (academic/mental_health/career/personal/other)
   - `notes` (student-provided context)
   - `created_by_receptionist` (boolean)

3. **CaseNote**
   - `appointment` (FK → Appointment)
   - `counselor` (FK → Profile, who wrote it)
   - `encrypted_content` (Fernet-encrypted text)
   - `is_confidential` (boolean)
   - `created_at`, `updated_at`

4. **AuditLog**
   - `user` (FK → Profile, nullable)
   - `action` (verb phrase)
   - `target` (entity affected)
   - `details` (JSONField)
   - `ip_address`
   - `created_at`

5. **ChatbotSession**
   - `student` (FK → Profile)
   - `conversation_history` (JSONField)
   - `created_at`, `updated_at`

6. **StudentMoodAlert**
   - `student` (FK → Profile)
   - `mood` (good/okay/low)
   - `note` (optional reflection)
   - `alert_dispatched` (boolean)
   - `created_at`

### 11.2 Choices/Enums (apps/common/choices.py)

```python
RoleChoices:
    ADMIN = 'admin'
    COUNSELOR = 'counselor'
    STUDENT = 'student'
    RECEPTIONIST = 'receptionist'

AppointmentStatusChoices:
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'

ConcernTypeChoices:
    ACADEMIC = 'academic'
    MENTAL_HEALTH = 'mental_health'
    CAREER = 'career'
    PERSONAL = 'personal'
    OTHER = 'other'
```

---

## 12. TECHNOLOGY STACK

**Backend:**
- Python 3.12
- Django 5.2.17
- PostgreSQL (production: Supabase)
- SQLite (development/testing)

**Frontend:**
- HTML5 + Django Templates
- CSS3 (Minimal design system)
- JavaScript (Vanilla, Lucide icons)
- NO frontend framework (React/Vue/etc.)

**Deployment:**
- Development server: `http://127.0.0.1:8000/`
- Production: TBD (Supabase backend configured)

**Security:**
- Fernet symmetric encryption (case notes)
- Django CSRF protection
- Role-based access control (custom decorators)
- Audit logging (all sensitive actions)

---

## 13. KNOWN GAPS & FUTURE WORK

### 13.1 Missing Features

**Counselor Profile Page:**
- Counselors cannot currently update their profile/password
- Need: `/counselor/profile/` view similar to `student_profile_view`

**Receptionist Profile Page:**
- Receptionists cannot currently update their profile/password
- Need: `/receptionist/profile/` view

**Email Notifications:**
- No email sent on appointment booking/confirmation/cancellation
- Future: Integrate Django email backend

**Real-Time Updates:**
- Counselor workspace does not auto-refresh
- Future: WebSocket integration or polling

### 13.2 Known Issues

None currently identified. All 81 tests passing ✅

### 13.3 Technical Debt

1. **Monolithic core/views/** — Will be resolved by completing Steps 6D-6F
2. **Monolithic core/services/** — Will be resolved by completing Steps 6D-6F
3. **Template duplication** — Some HTML repeated across role templates (consider shared partials)

---

## 14. COMPLIANCE & STANDARDS CHECKLIST

Use this checklist when adding NEW features or modifying EXISTING features:

### 14.1 Architecture Compliance
- [ ] Code placed in correct `apps/{feature}/` directory
- [ ] Services in `services/` subdirectory
- [ ] Templates in `templates/{feature}/` subdirectory
- [ ] URLs in feature `urls.py`, included in root
- [ ] Tests in feature `tests.py`

### 14.2 Security Compliance
- [ ] View uses `@require_{role}` decorator
- [ ] Row-level security filters applied (student/counselor-only data)
- [ ] Sensitive actions logged via `log_action()`
- [ ] Encrypted data uses `encryption.py` service
- [ ] No raw SQL queries (use Django ORM)

### 14.3 UI/UX Compliance
- [ ] Uses minimal.css classes (no custom gradients/shadows)
- [ ] Navigation added to appropriate `partials/{role}_subnav.html`
- [ ] Mobile-responsive (grid collapses, tables scrollable)
- [ ] ARIA labels on icon-only buttons
- [ ] Form labels properly associated

### 14.4 Testing Compliance
- [ ] Unit tests for service functions
- [ ] Permission tests for role-based access
- [ ] HTTP tests for view responses
- [ ] All tests passing before commit

### 14.5 Documentation Compliance
- [ ] View docstring references FLOWS/INTERFACES
- [ ] Service docstring explains business logic
- [ ] URL pattern added to this document (if new route)
- [ ] Feature × Role Matrix updated (if new permission)

---

## 15. APPROVAL & MAINTENANCE

**Document Owner:** Project Lead  
**Last Updated:** October 2, 2026  
**Next Review:** After Step 6D (Case Notes migration)

**Approval Status:** ⏳ PENDING USER APPROVAL

**Change Control:**
- Any deviation from this standard MUST be approved before implementation
- This document is the SOURCE OF TRUTH for architecture decisions
- Update this document BEFORE making conflicting changes

**Version History:**
- v1.0 (2026-10-02): Initial Phase 0 standardization audit

---

## 16. QUICK REFERENCE

### 16.1 Role Permission Summary

| Feature | Student | Counselor | Receptionist | Admin |
|---------|---------|-----------|--------------|-------|
| View own appointments | ✅ | ✅ (assigned) | ❌ | ❌ |
| Book appointments | ✅ | ❌ | ✅ (for others) | ❌ |
| Cancel appointments | ✅ (own) | ✅ (assigned) | ❌ | ❌ |
| Update appt status | ❌ | ✅ | ❌ | ❌ |
| Write case notes | ❌ | ✅ | ❌ | ❌ |
| View case notes | ✅ (non-conf) | ✅ (own) | ❌ | ❌ |
| Mood check-in | ✅ | ❌ | ❌ | ❌ |
| AI chatbot | ✅ | ❌ | ❌ | ❌ |
| Student search | ❌ | ❌ | ✅ | ✅ |
| User management | ❌ | ❌ | ❌ | ✅ |
| Analytics/reports | ❌ | ❌ | ❌ | ✅ |
| Audit logs | ❌ | ❌ | ❌ | ✅ |

### 16.2 Essential Commands

```bash
# Run development server
python manage.py runserver

# Run all tests
python manage.py test

# Create migrations (if models change)
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser (admin)
python manage.py createsuperuser

# Collect static files (production)
python manage.py collectstatic
```

### 16.3 Key File Locations

```
Authentication guards    → apps/authentication/guards.py
Role choices            → apps/common/choices.py
All models              → core/models.py
Audit service           → apps/audit/services/logger.py
Encryption service      → core/services/encryption.py
Minimal CSS             → static/css/minimal.css
Base template           → templates/base.html
Role home URLs          → apps/authentication/guards.py (ROLE_HOMES)
```

---

**END OF OFFICIAL SYSTEM STANDARD v1.0**

This document is AUTHORITATIVE and COMPLETE. No code changes proceed until this is reviewed and approved.
