# PERMISSIONS_ANALYSIS — What Users / Stakeholders CAN and CANNOT Do

**System:** GuidanceConnect (Django session auth + custom RBAC guards in `core/guards.py`)
**Roles (4):** `admin`, `counselor`, `student`, `receptionist` (stored on `Profile.role`)
**Enforcement:** `role_required()` decorator on all 24 app views + service-layer re-checks + query scoping.
**Wrong-role behavior:** silent 302 redirect to the user's own role home. **Deactivated:** forced logout → `/login/?error=deactivated`.

---

## 1. Architectural Blueprint — Access Model

```
Anonymous ──► Landing / Login / Register / Logout
Any authed ──► /password_change/ · /role-home/
student ────► /student/* · /appointments/* · /chatbot/* · /chat/*   (11 routes)
counselor ──► /counselor/*                                          (3 routes)
receptionist► /receptionist/*                                       (3 routes)
admin ──────► /admin-panel/*  (+ Django /admin/ if is_staff)        (5 routes)
```

### Route → role guard matrix

| Route group | anon | student | counselor | receptionist | admin |
|---|---|---|---|---|---|
| `/` landing, `/login/`, `/register/`, `/logout/` | ✅ public | → own home | → own home | → own home | → own home |
| `/password_change/`, `/role-home/` | 🔒 login | ✅ | ✅ | ✅ | ✅ |
| 8 student views (`/student/*`, `/appointments/*`) | 🔒 | ✅ | → `/counselor/` | → `/receptionist/` | → `/admin-panel/` |
| 3 chat views (`/chatbot/`, `/chat/*`) | 🔒 | ✅ | → `/counselor/` | → `/receptionist/` | → `/admin-panel/` |
| 3 counselor views (`/counselor/*`) | 🔒 | → `/student/` | ✅ | → `/receptionist/` | → `/admin-panel/` |
| 3 receptionist views (`/receptionist/*`) | 🔒 | → `/student/` | → `/counselor/` | ✅ | → `/admin-panel/` |
| 5 admin views (`/admin-panel/*`) | 🔒 | → `/student/` | → `/counselor/` | → `/receptionist/` | ✅ |
| Django `/admin/` (built-in) | 🔒 | ❌ | ❌ | ❌ | ✅ if `is_staff`/superuser |

### Data matrix — Role × table (S=select, I=insert, U=update, D=delete, —=deny)

| Table | Admin | Counselor | Student | Receptionist |
|---|---|---|---|---|
| **profiles** | S I U D (all) | S (self, counselor directory, assigned students) · U (self) | S (self) · U (self) | S (active students only) |
| **appointments** | S I U D (all) | S (assigned) · U (assigned status only) | S (own) · I (own booking) · U (cancel own → status) | S (all, read) · I (book for student) |
| **case_notes** | S (all) · decrypt only if NOT confidential | S I U D (own authored) | S (only `is_confidential=False`, own appts) | — none |
| **audit_logs** | S (all) + CSV export | — | — | — |
| **chatbot_sessions** | S (optional) | — | S I U (own) | — |
| **student_mood_alerts** | S I U D (all) | S (where counselor = me) | S (own) · I (via mood flow) | — |
| **audit inserts** | via signals/service on every sensitive action | same | same | same |

---

## 2. Role-by-Role: What They CAN Do

### 2.1 Anonymous (not logged in)

- View the landing page `/`
- Log in with email + password `/login/`
- Self-register — **always creates a Student account** (signal forces `role=student`) `/register/`
- Log out `/logout/`
- Any protected URL → redirected to `/login/?next=…`

### 2.2 Student (11 guarded routes)

**Appointments**
- View own upcoming/past appointments (`/appointments/`)
- View available 09:00–16:00 slots for any **active** counselor (`/appointments/slots/`)
- Book own appointment with an active counselor (`/appointments/book/`)
- Cancel **own** pending/confirmed appointment — POST only; completed/cancelled are blocked (`/appointments/<pk>/cancel/`)

**Wellbeing**
- Submit mood check-in `good|okay|low` + note ≤500 chars (POST only) — `low` auto-creates a mood alert for the assigned counselor
- Use AI chatbot: view page, load own session, stream messages
  - Rate limits: 24 POST / 15 min, 60 GET / 15 min → HTTP 429
  - Body caps: ≤24,000 chars, 36 messages, last message must be role `user`
  - Crisis keywords short-circuit the LLM flow

**Dashboard / Profile**
- View dashboard: own appointments + **non-confidential** case notes decrypted for their appointments
- View own profile (read-only) + change own password
- View static front-desk info (`/student/front-desk/`)

### 2.3 Counselor (3 guarded routes)

- View workspace: appointments **assigned to them**, mood alerts scoped to them, stats (`/counselor/`)
- Update status of **own assigned** appointment (POST) — enforced state machine:
  - `pending → confirmed | cancelled`
  - `confirmed → completed | cancelled`
  - `completed` / `cancelled` = terminal (no further changes)
  - Row check: `appointment.counselor_id == me` else **403**
- Create/edit/delete **their own** case notes on assigned appointments (`/counselor/case-notes/<appt_id>/`)
  - Content encrypted AES-256-CBC at rest
  - May toggle `is_confidential` (author-only control)
  - Integrity check: author must equal `appointment.counselor` else `PermissionDenied`
- Read any case note they authored (including confidential)
- Read/decrypt non-confidential case notes
- Change own password

### 2.4 Receptionist (3 guarded routes)

- View dashboard with 4-step booking UI + **today's appointments across all students/counselors** (`/receptionist/`)
- Search active students (JSON: id, name, student_id, email, department; limit 25) (`/receptionist/search-students/`)
- Book appointment **on behalf of** a student with an active counselor (POST)
  - Validates both parties: student must be `role=STUDENT, is_active=True`; counselor must be `role=COUNSELOR, is_active=True`
- Change own password

### 2.5 Admin (5 app routes + Django admin)

**Overview / KPIs** (`/admin-panel/`)
- View KPIs, 8-week series, concern-type breakdown, recent 10 audit logs

**User management** (`/admin-panel/users/`)
- Search / filter / paginate **all** profiles
- Create any user with any role (`create_user` — syncs `is_staff` for admin role)
- Change any user's role (`change_role` — syncs `is_staff`)
- Activate / deactivate any user (`toggle_status` — syncs `user.is_active`; deactivated users are logged out at next request)
- All actions dual-written to audit log

**Audit logs** (`/admin-panel/audit/`)
- View full `AuditLog` trail
- CSV export (500 rows) via `?export=true` — the export itself is audited

**Reports** (`/admin-panel/reports/`)
- Filter all appointments; preview 50 rows
- Export CSV or PDF (`?export=csv|pdf`) — audited as `REPORT_EXPORT`

**Profile** (`/admin-panel/profile/`)
- Own profile + password change

**Django built-in `/admin/`** — only if `is_staff`/superuser (role change to admin auto-sets `is_staff`; only the seeded admin is superuser)

**Change anything about anyone:** yes, subject to §4 safeguards.

---

## 3. What Each Stakeholder CANNOT Do

### 3.1 Student CANNOT

| Denied | Enforcement |
|---|---|
| Access any counselor/receptionist/admin route | `role_required` → 302 to `/student/` |
| See another student's appointments/notes | Query scoped `student=request.user.profile`; wrong id → 404 |
| See **confidential** case notes | Filter `is_confidential=False`; decrypt matrix returns `None` |
| Edit their own appointment status | No route; only cancel (POST, own, non-terminal) |
| Cancel completed/cancelled appointments | Service blocks terminal states |
| Create/edit case notes | No route; `save_case_note` raises `PermissionDenied` for non-counselors |
| Book for another student / pick inactive counselor | Role + `is_active` checks in booking service |
| View audit logs, reports, user management | Admin-only routes |
| Use receptionist quick-search or walk-in booking | Receptionist-only routes |
| Exceed chat rate limits | 429 + `Retry-After`; body caps: ≤24,000 chars, 36 messages, last message must be `user` |
| Access their chat session if not owner | `session.student_id != me` → 403 |
| Self-promote role | No route; registration always `student` |
| Edit own profile fields (name/student_id/department) | Profile page is read-only (form exists but is unused) |
| Log in if deactivated | Login + guard force logout `/login/?error=deactivated` |

### 3.2 Counselor CANNOT

| Denied | Enforcement |
|---|---|
| Access student/receptionist/admin routes | 302 to `/counselor/` |
| Update an appointment **not assigned to them** | View 403 + service check `counselor_id == me` |
| Make illegal status transitions | `ALLOWED_TRANSITIONS` state machine (terminal states locked) |
| Write case notes on appointments they don't own | `PermissionDenied` in `save_case_note` |
| Read another counselor's **confidential** note | Decrypt matrix: confidential → author only |
| Delete appointments or profiles | No route; no delete permission |
| View audit logs / reports / manage users | Admin-only |
| Book appointments (student or receptionist flow) | No route |
| Submit mood check-ins | Mood service: role must be `student` |
| Access chatbot | Student-only routes |
| Promote/demote anyone or change activation | Admin-only |

### 3.3 Receptionist CANNOT

| Denied | Enforcement |
|---|---|
| Access student/counselor/admin routes | 302 to `/receptionist/` |
| Read or write case notes | Matrix: `—`; no route |
| View audit logs / reports / manage users | Admin-only |
| Update appointment status after booking | No status route (counselor-only) |
| Book inactive students/counselors | Role + `is_active` validation in `receptionist_book_view` |
| Edit appointment records | No update route (only create) |
| Use chatbot / mood check-in | Student-only |
| Access chat sessions or mood alerts data | No route; matrix `—` |

### 3.4 Admin CANNOT

| Denied | Enforcement |
|---|---|
| Demote **their own** role away from admin | `"You cannot demote your own admin account here."` |
| Remove the **last** admin (role change) | `"Cannot remove the last admin account."` |
| **Deactivate themselves** | `"You cannot deactivate your own account."` |
| Deactivate the **last active admin** | `"Cannot deactivate the last active admin."` |
| **Decrypt confidential case notes** (even as admin) | Decrypt matrix: confidential → author only; admin gets `None` |
| Edit another counselor's case note content | Write path is counselor-author-only (`save_case_note` role + ownership check) |
| Access student booking/chatbot/counselor/receptionist routes | 302 to `/admin-panel/` (routes are role-locked, not "any staff") |
| View raw chat sessions of students via UI (by default) | Matrix allows optional select, but no app route exposes them |
| Escape audit trails | Role change, status toggle, user create, report export, audit CSV export all log actions |

### 3.5 Anonymous / Public CANNOT

- Open any guarded URL (all 24 redirect to login)
- Register as counselor/receptionist/admin (signal always creates `student`)
- Login with deactivated account or missing profile (`?error=deactivated` / `?error=no_profile`)
- Perform POST actions without CSRF token

---

## 4. Cross-Cutting Safeguards (apply system-wide)

1. **Route guard** — `role_required` (`core/guards.py:27`): unauthenticated → login; no profile → logout; inactive → logout; wrong role → own home.
2. **Object ownership** — student appointments filtered by self; counselor rows 403 if not assigned; chat session 403 if not owner.
3. **Status state machine** — only `pending→{confirmed,cancelled}`, `confirmed→{completed,cancelled}`; terminal states immutable.
4. **Case-note confidentiality** — encrypted at rest; read matrix: author always / confidential author-only / non-confidential → admin + own student / everyone else denied.
5. **Admin 4 safeguards** — self-demotion, last-admin, self-deactivate, last-active-admin blocks (`core/services/admin_users.py`).
6. **Chat rate limits** — 24 POST + 60 GET per 15 min per student → HTTP 429.
7. **Audit dual-write** — every sensitive mutation logged; viewer/export admin-only.
8. **FK protections** — appointment→counselor `PROTECT` (can't delete counselor with appointments); profile deletion cascades appropriately.
9. **`is_staff` sync** — role==admin → staff; only superuser reaches full Django admin power.
10. **Registration lockdown** — self-signup always student; staff accounts provisioned only by admin/seed.

---

## 5. Verification & Tests

```bash
python manage.py check
python manage.py test tests -v 2
```

| Suite | Covers |
|---|---|
| `test_auth_guards.py` | Route/role redirects, deactivated logout |
| `test_appointments.py` | Booking/cancel/state machine/ownership |
| `test_case_notes.py` | Confidentiality decrypt matrix |
| `test_admin_safeguards.py` | 4 admin blocks |
| `test_mood_chat.py` | Role checks + rate limits |
| `test_views_http.py` | HTTP-level access per role |
| `test_slots.py` | Slot engine |

---

## 6. Identified Gaps

| # | Gap | Risk |
|---|---|---|
| 1 | Wrong role → **302 redirect, not 403** | Silent; tests must follow redirects to assert blocking |
| 2 | **No `LoginRequiredMiddleware`** — a newly added view is public by default | Future routes may ship unguarded |
| 3 | Chat rate limits are **in-memory per process** | Reset on restart; not shared across workers |
| 4 | `SECRET_KEY` has insecure hardcoded **fallback** in settings | Production secret exposure if env unset |
| 5 | `logout` accepts **GET** (no CSRF) | Logout CSRF annoyance |
| 6 | Student/receptionist **profile edit forms are dead code** | Profile fields not user-editable in UI |
| 7 | Admin can view confidential-note **metadata** but not content (by design) | Confirm stakeholders expect this |
| 8 | Mood alerts: no counselor **acknowledge/delete** route | Alerts accumulate |
| 9 | No password-reset/forgot-password flow | Admin must intervene manually |
| 10 | No object-level delete for appointments (cancel only) | By design — audit-friendly |

---

## Summary

- **Students** manage their own bookings, mood check-ins, and AI chat — and see only **non-confidential** case notes on **their own** appointments.
- **Counselors** manage only **assigned** appointments and their **own encrypted** case notes (confidential = author-only).
- **Receptionists** only search students and create bookings for them — no notes, no status updates, no reports.
- **Admins** manage everything **except decrypting confidential notes**, and are hard-blocked from self-demotion, self-deactivation, and removing the last admin.
- **Anonymous users** get only landing / login / register / logout; registration always yields a **student**.
