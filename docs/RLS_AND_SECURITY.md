# System Security & Role-Based Access Control Specification

This document details the security architecture, role authorization matrices, and cryptographic protections implemented across the **ConnectGuidance** system.

---

## 1. Role × Resource Access Matrix

The system enforces strict permission boundaries across four user roles:

| Domain Entity | Administrator | Guidance Counselor | Student | Receptionist |
|---|---|---|---|---|
| **User Profiles** | Full management (view, create, update, activate/deactivate) | Directory lookup of counselors and assigned students | View and edit own profile only | Read-only search of active students for booking |
| **Appointments** | System-wide view and report generation | View assigned sessions; update statuses (`confirmed`, `completed`, `cancelled`) | View own sessions; book new slots; cancel pending/confirmed sessions | View calendar slots; book walk-in appointments for active students |
| **Case Notes** | Prohibited from viewing clinical note content | Create, update, and view own authored case notes | View non-confidential notes from past sessions only | Strictly Denied |
| **Audit Logs** | System-wide inspection and compliance review | Strictly Denied | Strictly Denied | Strictly Denied |
| **Chat Sessions** | System administration | Strictly Denied | View and stream own wellness chat sessions | Strictly Denied |
| **Mood Alerts** | System audit overview | View alerts dispatched by assigned students | Submit periodic check-ins (`good`, `okay`, `low`) | Strictly Denied |

---

## 2. Multi-Layer Enforcement Architecture

Security in ConnectGuidance is implemented defense-in-depth across multiple application layers:

### Layer 1: HTTP View Decorators (`core/guards.py`)
- Every portal view is annotated with `@role_required("student")`, `@role_required("counselor")`, etc.
- Unauthenticated requests are rejected and redirected to `/login/`.
- Authenticated users attempting cross-role escalation are redirected to their designated home dashboard.

### Layer 2: ORM Query Scoping
- Views and services explicitly scope database queries to the authenticated user's profile (`Appointment.objects.filter(student=profile)` or `Appointment.objects.filter(counselor=profile)`).
- Cross-student access is structurally impossible even with forged object IDs.

### Layer 3: Service-Level Validation & State Machine
- Business operations (cancellation, status updates, case note authoring) verify ownership and lifecycle rules before executing mutations.
- Terminal appointments (`completed` or `cancelled`) cannot be modified.

---

## 3. Cryptographic Storage of Clinical Notes

Counselor case documentation contains sensitive student disclosures and is protected using **AES-256** encryption before persistence:
- Encrypted payloads include initialization vectors and ciphertext.
- Decryption keys are derived securely from application secrets and never sent to client browsers or templates.
- Students only receive authorized non-confidential summaries, while confidential notes remain strictly isolated to the authoring counselor.

---

## 4. Rate Limiting and Safety Guardrails

- **Chat POST Endpoint:** Maximum 24 requests per 15-minute sliding window. Exceeding requests return HTTP 429 with `Retry-After`.
- **Session GET Endpoint:** Maximum 60 requests per 15-minute sliding window.
- **Payload Limits:** Maximum 24,000 characters per chat prompt, with history persistence capped at the 36 most recent messages.
- **Crisis Intervention:** Automatic detection of crisis keywords triggers supportive crisis hotline referrals and urgent counselor booking recommendations.

---

## 5. Administrative Safeguards

To prevent operational deadlocks and privilege lockouts:
1. Administrators cannot demote their own account to a lower role.
2. Administrators cannot deactivate their own account.
3. The system rejects any action that would deactivate or demote the last remaining active administrator account in the university.
