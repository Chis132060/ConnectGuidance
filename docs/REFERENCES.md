# ConnectGuidance — Component & Module Reference Guide

This document describes the architectural layout, modular organization, and service dependencies for the **ConnectGuidance** Django application.

---

## 🏛️ Application Architecture Overview

ConnectGuidance follows the **Django Model-View-Template (MVT)** design pattern, augmented by an explicit **Service Layer** under `core/services/`. This keeps view controllers thin and maintains business logic separation.

```text
[HTTP Request]
       │
       ▼
 [core/urls.py]
       │
       ▼
 [core/guards.py]  ──── (Role authentication check)
       │
       ▼
 [core/views/*.py] ──── [core/forms.py] (Form validation)
       │
       ▼
[core/services/*.py] ── (Business operations & domain rules)
       │
       ▼
 [core/models.py]  ──── [core/signals.py] (Audit logging & triggers)
       │
       ▼
[Database / SQLite]
```

---

## 📦 Service Layer Catalog

All business operations, encryption, analytics, and rate limits are managed in `core/services/`:

| Service Module | Purpose & Core Functions | Key Consumers |
|---|---|---|
| `core/services/slots.py` | Calculates hourly appointment slots (09:00–16:00), conflict window checks (+/- 50 mins), and next-available counselor lookup. | `views/student.py`, `views/receptionist.py` |
| `core/services/appointments.py` | Enforces appointment booking rules, student cancellation permissions, and counselor state machine transitions (`pending` → `confirmed` → `completed`). | `views/student.py`, `views/counselor.py` |
| `core/services/case_notes.py` | Encrypted clinical documentation. Handles secure note creation, updates, and decryption for authorized counselors. | `views/counselor.py` |
| `core/services/encryption.py` | Cryptographic engine providing AES-256 encryption at rest with derived key security. | `services/case_notes.py` |
| `core/services/mood.py` | Student wellness mood recording (`good`, `okay`, `low`) and counselor crisis alerting logic. | `views/student.py` |
| `core/services/chat.py` | AI wellness assistant streaming generator, rate-limiting stores (24 POST / 60 GET), crisis keyword detection, and 36-message history cap. | `views/chat.py` |
| `core/services/receptionist.py` | Front desk student lookup by name or ID, walk-in appointment scheduling, and automated counselor assignment. | `views/receptionist.py` |
| `core/services/metrics.py` | Aggregates system KPIs, calculates 8-week trend distributions, and groups appointment concern types. | `views/admin_views.py` |
| `core/services/reports.py` | Multi-filter query engine, RFC-4180 CSV export, and PDF appointment summary generation. | `views/admin_views.py` |
| `core/services/admin_users.py` | Administrative account provisioning and role updates with self-demotion and last-admin safeguards. | `views/admin_views.py` |
| `core/services/audit.py` | Non-blocking, append-only security event logger recording administrative and clinical actions. | All views and services |

---

## 🔐 Security & Access Control Reference

Access control is enforced using decorators defined in `core/guards.py`:
- `@role_required("student")`
- `@role_required("counselor")`
- `@role_required("receptionist")`
- `@role_required("admin")`

When an unauthenticated user accesses a protected route, they are redirected to `/login/`. If an authenticated user accesses a portal outside their assigned role, they are redirected to their designated home portal.
