# ERD — GuidanceConnect Django Replica

Source of truth: original Supabase migrations in `../connectguidance1/supabase/migrations/`.  
This document is the **Django models spec** for Phase 2 — no field may be missing.

---

## Mermaid ERD

```mermaid
erDiagram
    AUTH_USER ||--o| PROFILE : "1:1 post_save trigger parity"
    PROFILE ||--o{ APPOINTMENT : "student_id CASCADE"
    PROFILE ||--o{ APPOINTMENT : "counselor_id PROTECT"
    APPOINTMENT ||--o{ CASE_NOTE : "appointment_id CASCADE"
    PROFILE ||--o{ CASE_NOTE : "counselor_id CASCADE"
    PROFILE ||--o{ AUDIT_LOG : "user_id SET_NULL"
    PROFILE ||--o{ CHATBOT_SESSION : "student_id CASCADE"
    PROFILE ||--o{ STUDENT_MOOD_ALERT : "student_id CASCADE"
    PROFILE ||--o{ STUDENT_MOOD_ALERT : "counselor_id CASCADE"
    AUDIT_LOG }o..o{ APPOINTMENT : "record_id polymorphic no FK"
    AUDIT_LOG }o..o{ CASE_NOTE : "record_id polymorphic no FK"
    AUDIT_LOG }o..o{ CHATBOT_SESSION : "record_id polymorphic no FK"
    AUDIT_LOG }o..o{ STUDENT_MOOD_ALERT : "record_id polymorphic no FK"
    AUDIT_LOG }o..o{ PROFILE : "record_id polymorphic no FK"

    AUTH_USER {
        int id PK "django.contrib.auth User"
        string username
        string email
        string password
        datetime date_joined
    }

    PROFILE {
        int id PK
        int user_id FK_1to1 "auth.User"
        string role "choices: admin|counselor|student|receptionist"
        string full_name "NOT NULL"
        string student_id "nullable"
        string department "nullable"
        bool is_active "default True"
        bigint user_no "UNIQUE sequence parity"
        datetime created_at "auto_now_add"
    }

    APPOINTMENT {
        int id PK
        int student_id FK "PROFILE CASCADE"
        int counselor_id FK "PROFILE PROTECT"
        datetime scheduled_at "NOT NULL hourly 09-16"
        string status "pending|confirmed|cancelled|completed default pending"
        string concern_type "academic|mental_health|career|personal|other"
        string notes "nullable max 2000"
        datetime created_at "auto_now_add"
    }

    CASE_NOTE {
        int id PK
        int appointment_id FK "APPOINTMENT CASCADE"
        int counselor_id FK "PROFILE CASCADE"
        text content "encrypted ciphertext NOT NULL"
        bool is_confidential "default False"
        datetime created_at "auto_now_add"
        datetime updated_at "auto_now"
    }

    AUDIT_LOG {
        int id PK
        int user_id FK "PROFILE SET_NULL nullable"
        string action "NOT NULL"
        string table_name "NOT NULL"
        uuid record_id "nullable polymorphic NO FK"
        json metadata "default {}"
        datetime created_at "auto_now_add"
    }

    CHATBOT_SESSION {
        int id PK
        int student_id FK "PROFILE CASCADE"
        json messages "default [] array of role/content"
        datetime created_at "auto_now_add"
    }

    STUDENT_MOOD_ALERT {
        int id PK
        int student_id FK "PROFILE CASCADE"
        int counselor_id FK "PROFILE CASCADE"
        string note "nullable CHECK length <= 500"
        datetime created_at "auto_now_add"
    }
```

---

## Enums / choices (Django)

### `APP_ROLE` (original: `public.app_role`)
```python
ROLE_CHOICES = [
    ("admin", "Admin"),
    ("counselor", "Counselor"),
    ("student", "Student"),
    ("receptionist", "Receptionist"),
]
```

### `APPOINTMENT_STATUS` (original: `public.appointment_status`)
```python
STATUS_CHOICES = [
    ("pending", "Pending"),
    ("confirmed", "Confirmed"),
    ("cancelled", "Cancelled"),
    ("completed", "Completed"),
]
```

### Concern presets (original: app-layer `lib/concerns.ts`, stored as text)
```python
CONCERN_CHOICES = [
    ("academic", "Academic"),
    ("mental_health", "Mental Health"),
    ("career", "Career"),
    ("personal", "Personal"),
    ("other", "Other"),
]
```

**Sequence parity:** original `profiles_user_no_seq` (bigint unique). In Django use `BigIntegerField(unique=True)` filled in `Profile.save()` via `MAX(user_no)+1` or a DB sequence.

---

## Entity dictionary (field-for-field)

### 1. `auth.User` (Django built-in — replaces `auth.users`)
| Field | Type | Notes |
|---|---|---|
| `id` | int PK | Django default |
| `username` | required by default auth | or custom user with email — keep default for skeleton simplicity |
| `email` | string | unique if using email login |
| `password` | hashed | Django auth |
| `date_joined` | datetime | |

### 2. `core.Profile` (replaces `public.profiles`)
| Field | Type | Constraints |
|---|---|---|
| `user` | OneToOneField(User) | `on_delete=CASCADE`, `related_name="profile"` |
| `role` | CharField(20) | choices=ROLE_CHOICES, default=`student` |
| `full_name` | CharField(200) | NOT NULL |
| `student_id` | CharField(100) | null=True, blank=True |
| `department` | CharField(200) | null=True, blank=True |
| `is_active` | BooleanField | default=True |
| `user_no` | BigIntegerField | unique=True |
| `created_at` | DateTimeField | auto_now_add=True |

**Triggers parity:**
- `on_auth_user_created_profile` → `post_save` signal on User: create Profile(role=student) if missing
- `trg_audit_profiles_changes` → `post_save`/`post_delete` → AuditLog

**Indexes:** `role`, `is_active`, unique `user_no`.

### 3. `core.Appointment` (replaces `public.appointments`)
| Field | Type | Constraints |
|---|---|---|
| `student` | ForeignKey(Profile) | CASCADE, related_name=`appointments_as_student` |
| `counselor` | ForeignKey(Profile) | **PROTECT** (parity with DB RESTRICT), related_name=`appointments_as_counselor` |
| `scheduled_at` | DateTimeField | NOT NULL |
| `status` | CharField(20) | STATUS_CHOICES, default=`pending` |
| `concern_type` | CharField(50) | CONCERN_CHOICES (or free CharField max 200 like original) |
| `notes` | TextField | null=True, blank=True (app validates ≤ 2000) |
| `created_at` | DateTimeField | auto_now_add=True |

**Indexes:** `student`, `counselor`, `scheduled_at`.

**Status transitions (service-layer only — same as original):**
| From | Allowed next | Who |
|---|---|---|
| pending | confirmed, cancelled | counselor |
| confirmed | completed, cancelled | counselor |
| pending | cancelled | student (own) |
| completed / cancelled | *(terminal — no updates)* | — |

**Counselor may only set:** `confirmed | cancelled | completed` (never back to pending).

### 4. `core.CaseNote` (replaces `public.case_notes`)
| Field | Type | Constraints |
|---|---|---|
| `appointment` | ForeignKey(Appointment) | CASCADE |
| `counselor` | ForeignKey(Profile) | CASCADE, related_name=`case_notes` |
| `content` | TextField | NOT NULL — **ciphertext only** |
| `is_confidential` | BooleanField | default=False |
| `created_at` | DateTimeField | auto_now_add=True |
| `updated_at` | DateTimeField | auto_now=True |

**Constraints:**
- `UniqueConstraint(fields=["appointment", "counselor"], name="uniq_case_note_appt_counselor")`
- `clean()` / service check: `counselor_id == appointment.counselor_id` (port integrity trigger `23514`)
- One note per appointment per counselor → **upsert** semantics in service

**Parity:** `trg_case_notes_updated_at` → `auto_now`; `trg_audit_case_notes_changes` → signals → AuditLog.

### 5. `core.AuditLog` (replaces `public.audit_logs`)
| Field | Type | Constraints |
|---|---|---|
| `user` | ForeignKey(Profile) | `SET_NULL`, `null=True`, `blank=True` |
| `action` | CharField(100) | NOT NULL |
| `table_name` | CharField(100) | NOT NULL (or `"application"`) |
| `record_id` | UUIDField | `null=True` — **no FK** (polymorphic) |
| `metadata` | JSONField | default=dict |
| `created_at` | DateTimeField | auto_now_add=True |

**Known actions:**  
`APPOINTMENT_CREATED`, `APPOINTMENT_STATUS_UPDATED`, `APPOINTMENT_CANCELLED_STUDENT`, `APPOINTMENT_CREATED_RECEPTION`, `CASE_NOTE_UPSERT`, `STUDENT_MOOD_CHECKIN`, `STUDENT_MOOD_ALERT`, `CHAT_SESSION_UPSERT`, `REPORT_EXPORT`, plus `INSERT`/`UPDATE`/`DELETE` from signals.

**Write sources:** (1) explicit `log_action()` in services (2) signals on Profile + CaseNote.

### 6. `core.ChatbotSession` (replaces `public.chatbot_sessions`)
| Field | Type | Constraints |
|---|---|---|
| `student` | ForeignKey(Profile) | CASCADE |
| `messages` | JSONField | default=list — `[{"role": "user"\|"assistant", "content": str}]` |
| `created_at` | DateTimeField | auto_now_add=True |

**App limits:** max 36 messages sent per request; content ≤ 24000 chars; hydrate **latest** session by `created_at` desc.

### 7. `core.StudentMoodAlert` (replaces `public.student_mood_alerts`)
| Field | Type | Constraints |
|---|---|---|
| `student` | ForeignKey(Profile) | CASCADE |
| `counselor` | ForeignKey(Profile) | CASCADE, related_name=`mood_alerts` |
| `note` | CharField(500) | null=True, blank=True — `CheckConstraint(length ≤ 500)` |
| `created_at` | DateTimeField | auto_now_add=True |

**Indexes:** `(counselor, -created_at)`, `(student, -created_at)`.

**Creation rules (app-layer, same as original RLS + action):**
- Only mood `low` creates a row
- Counselor = counselor of student’s **latest non-cancelled appointment**
- Requires existing appointment pair between student and counselor
- Note optional, max 500 chars
- Mood enum `good|okay|low` is **not stored** — only used to branch (good/okay → audit only)

---

## Delete semantics (parity with FK rules)

| FK | Original | Django |
|---|---|---|
| `Profile.user` | CASCADE | CASCADE |
| `Appointment.student` | CASCADE | CASCADE |
| `Appointment.counselor` | RESTRICT | **PROTECT** (blocks deleting counselor with appointments) |
| `CaseNote.appointment` | CASCADE | CASCADE |
| `CaseNote.counselor` | CASCADE | CASCADE |
| `AuditLog.user` | SET NULL | SET_NULL |
| `ChatbotSession.student` | CASCADE | CASCADE |
| `StudentMoodAlert.*` | CASCADE | CASCADE |

---

## What replaces Supabase-only features

| Supabase | Django replacement |
|---|---|
| `app_role` / `appointment_status` enums | Choice fields |
| RLS policies | View/service query scoping + `guards.py` (see `RLS_AND_SECURITY.md`) |
| DB triggers (audit, updated_at, integrity, profile-on-signup) | Django signals + `auto_now` + `clean()`/service checks |
| `profiles_user_no_seq` | App-assigned unique `user_no` or DB sequence |
| SQL migrations (18 files) | Django migrations under `core/migrations/` |
| `auth.users` | `django.contrib.auth.models.User` |

---

## Phase 2 verification

1. `python manage.py makemigrations core`
2. `python manage.py migrate`
3. Supabase table list contains: `core_profile`, `core_appointment`, `core_case_note`, `core_audit_log`, `core_chatbot_session`, `core_student_mood_alert`, plus Django core tables
4. `python manage.py check`
5. Tick every box in PLAN.md “Data (ERD)” checklist
