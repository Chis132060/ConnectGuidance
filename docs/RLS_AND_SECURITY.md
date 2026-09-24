# RLS_AND_SECURITY — Supabase → Django port

Original: Row Level Security on every public table + app-layer checks.  
Django: **no DB RLS** — enforce with **query scoping**, **view/service guards**, and **forms**.

---

## 1. Role × table permission matrix (target behavior)

Legend: **S** select · **I** insert · **U** update · **D** delete · **—** deny

| Table | Admin | Counselor | Student | Receptionist |
|---|---|---|---|---|
| **profiles** | S I U D (all) | S (self, counselors directory, assigned students) U (self) | S (self) U (self) | S (active students only) |
| **appointments** | S I U D (all) | S (assigned) U (assigned status only) | S (own) I (own booking) U (own cancel→status) | S (all read) I (book for student) |
| **case_notes** | S all · U? app blocks confidential read for non-author | S I U D (own authored) | S (**only is_confidential=False** via own appts) | — |
| **audit_logs** | S (all) | — | — | — |
| **chatbot_sessions** | S (all, optional) | — | S I U (own) | — |
| **student_mood_alerts** | S I U D (all) | S (where counselor=me) | S (own) I (own via mood flow) | — |
| **audit insert** | any authenticated / signals | same | same | same |

**App-layer write always re-checks role** (parity with original server actions), e.g.:
- Book / get slots → active **student** only
- Status update → active **counselor** + row `counselor_id == me`
- Case note save → active **counselor** + appointment assigned to me
- Admin user mgmt / reports / audit view → `requireAdmin`
- Receptionist actions → active **receptionist**

---

## 2. Django enforcement points

| Layer | Mechanism |
|---|---|
| URL/View | `@login_required` + `@role_required(...)` in `core/guards.py` |
| Query | Always filter by `request.user.profile` (own rows) or role-specific scope |
| Model | `PROTECT`/`CASCADE`/`SET_NULL` FKs; `unique_together`; `CheckConstraint` |
| Form/service | Business rules (status machine, clash, integrity) before `save()` |
| Template | Don’t pass confidential notes to student context |
| Admin site | Django admin restricted to superusers / admin role |

### Guard helpers (Phase 3)

```python
# core/guards.py (sketch)
def role_required(*roles):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            profile = get_profile_or_none(request.user)
            if not profile or not profile.is_active:
                logout(request)
                return redirect("/login/?error=deactivated")
            if profile.role not in roles:
                return redirect(role_home(profile.role))
            return view(request, *args, **kwargs)
        return wrapped
    return decorator

ROLE_HOME = {
    "admin": "/admin-panel/",
    "counselor": "/counselor/",
    "student": "/student/",
    "receptionist": "/receptionist/",
}
```

**`requireAdmin` parity:** helper used inside admin views (same redirect behavior as `lib/supabase/admin-guard.ts`).

---

## 3. Encryption (case notes)

| Item | Rule |
|---|---|
| Algorithm | AES-256-CBC; output `iv_hex + cipher_hex` (32 hex IV chars) |
| Legacy | payloads starting `gc:v1:` → AES-256-GCM base64url |
| Key | env `ENCRYPTION_KEY` (or `CASE_NOTES_ENCRYPTION_KEY`) = **64 hex chars** |
| Where | server-only `core/services/encryption.py` — never import in templates/JS |
| Scope | encrypt on save; decrypt only in authorized read path (Flow 12) |

Port of `../connectguidance1/lib/encryption.ts`.

---

## 4. Rate limits (chat)

| Limit | Default | Env |
|---|---|---|
| Chat POST | 24 / 15 min / user | `CHAT_RATE_LIMIT_MAX`, `CHAT_RATE_LIMIT_WINDOW_MS` |
| Session GET | 60 / 15 min / user | `CHAT_SESSION_GET_MAX`, `CHAT_SESSION_GET_WINDOW_MS` |

Implement in-memory first (parity with original Node memory limiter) — `core/services/` or cache framework.

---

## 5. Admin safety guards (from `app/admin/actions.ts`)

| Rule | Error |
|---|---|
| Cannot change own role away from admin | “You cannot demote your own admin account here.” |
| Cannot remove last admin (role change) | “Cannot remove the last admin account.” |
| Cannot deactivate self | “You cannot deactivate your own account.” |
| Cannot deactivate last **active** admin | “Cannot deactivate the last active admin.” |
| Missing service key equivalent | N/A — Django uses DB directly with admin guard only |

---

## 6. Authentication security

| Item | Implementation |
|---|---|
| Passwords | Django hashed validators (min 8, common/numeric checks already in settings) |
| Sessions | `django.contrib.sessions` DB or cache backend |
| CSRF | all POST views — `{% csrf_token %}` |
| Secrets | only `.env` (gitignored); never commit real URI/key |
| DEBUG | `False` in production; `ALLOWED_HOSTS` explicit |
| HTTPS | Supabase requires SSL (`sslmode=require`); app behind HTTPS in deploy |
| Registration | only students self-register (staff provisioned by admin/seed) — enforce in register form |

---

## 7. Confidentiality rules (case notes)

1. Student query: `CaseNote.objects.filter(is_confidential=False, appointment__student=me)`
2. Counselor: own authored notes only for write; read assigned appointment notes as needed
3. Admin: may list all; **decrypt path** only if `not is_confidential` (parity with `getCaseNote`)
4. `is_confidential` toggled only by author counselor on save

---

## 8. Audit integrity

- `log_action()` **never raises** (parity with `lib/audit.ts`)
- Invalid `record_id` → `NULL`
- Signals on Profile + CaseNote for INSERT/UPDATE/DELETE-style rows
- Audit viewer: admin SELECT only

---

## 9. Mapping table (original → Django)

| Supabase / Next.js | Django |
|---|---|
| `proxy.ts` edge redirects | guards + `role_required` |
| `requireAdmin()` | `role_required('admin')` / helper |
| `requireReceptionist()` | `role_required('receptionist')` |
| RLS policies | query scoping matrix §1 |
| `auth.users` + trigger profile | User + `post_save` Profile |
| Supabase Auth cookies | Django session |
| `lib/encryption.ts` | `services/encryption.ts` |
| `lib/audit.ts` | `services/audit.py` |
| `lib/rate-limit/chat.ts` | chat rate limiter service |
| Server actions Zod | Django forms / service validation |
| `ON DELETE RESTRICT` | `on_delete=PROTECT` |
| `ON DELETE SET NULL` | `on_delete=SET_NULL` |
| DB audit triggers | Django signals |

---

## 10. Security verification checklist

- [ ] Wrong-role URL → redirect ROLE_HOME (4 roles)
- [ ] Deactivated user cannot login or use session
- [ ] Student cannot open another student’s appointments/notes
- [ ] Confidential note hidden from student UI and decrypt path for non-author
- [ ] Counselor cannot update another counselor’s appointment
- [ ] Status transitions reject illegal paths + terminal states
- [ ] Receptionist-only routes blocked for others
- [ ] Admin routes blocked for non-admins
- [ ] Last-admin / self-deactivate guards work
- [ ] Chat rate limits return 429
- [ ] Case note `content` not plaintext in DB
- [ ] `.env` not in git; `check` clean with `DEBUG=False` eventually
- [ ] CSRF on all mutating forms
