# FLOWS — GuidanceConnect Django Replica (24 flows)

Port of the original Next.js system behavior. Use with `PLAN.md` phases.  
Mermaid flowcharts — implement every branch and error path.

---

## 1. Route guards (replaces `proxy.ts` + page `requireAdmin` / role checks)

```mermaid
flowchart TD
    A[Incoming request] --> B{Public path? / /login /register}
    B -->|Yes| C{Authenticated?}
    C -->|No| D[Render public page]
    C -->|Yes| E{is_active?}
    E -->|No| F[Redirect login error=deactivated]
    E -->|Yes| G[Redirect ROLE_HOME]
    B -->|No| H{Login required path?}
    H -->|No| I[Next - static etc]
    H -->|Yes| J{Session authenticated?}
    J -->|No| K[Redirect /login next=path]
    J -->|Yes| L{is_active?}
    L -->|No| F
    L -->|Yes| M{role matches path?}
    M -->|No| G
    M -->|Yes| N[Allow view]

    ROLE_HOME["admin→/admin-panel · counselor→/counselor · student→/student · receptionist→/receptionist"]
```

**Django implementation:** `@login_required` + `role_required(*roles)` decorator on every view; inactive → logout + redirect. Admin pages also use a `requireAdmin`-equivalent helper.

---

## 2. Student registration

```mermaid
flowchart TD
    A[/register form] --> B[Zod-parity validation<br/>email password≥8 name student_id department]
    B -->|Fail| C[Field errors]
    C --> A
    B -->|Pass| D[Create User]
    D --> E[post_save → Profile role=student<br/>is_active=True user_no assigned]
    E --> F[Audit signal optional]
    F --> G[Auto login optional / redirect /login]
    G --> H[Login → ROLE_HOME /student]
    D -->|username/email exists| I[Error: already registered]
```

---

## 3. Sign-in

```mermary
flowchart TD
    A[Login form] --> B{Valid credentials?}
    B -->|No| C[Invalid email or password]
    B -->|Yes| D{Profile exists + valid role?}
    D -->|No| E[error=no_profile]
    D -->|Yes| F{is_active?}
    F -->|False| G[Logout + error=deactivated]
    F -->|True| H[Redirect ROLE_HOME]
```

---

## 4. Sign-out

```mermaid
flowchart TD
    A[Logout] --> B[django logout - flush session] --> C[Redirect /]
```

---

## 5. Password change

```mermaid
flowchart TD
    A[Profile form: current new confirm] --> B{new==confirm and length≥8?}
    B -->|No| C[Field errors]
    B -->|Yes| D[Django PasswordChangeView verifies old password]
    D -->|Wrong| E[Error: current password incorrect]
    D -->|OK| F[set new password] --> G[Success toast - stay signed in]
```

---

## 6. Role home redirect after login

```mermaid
flowchart TD
    A[After successful auth] --> B[Load profile.role]
    B --> C[admin → /admin-panel]
    B --> D[counselor → /counselor]
    B --> E[student → /student]
    B --> F[receptionist → /receptionist]
```

---

## 7. Student: available slots

```mermaid
flowchart TD
    A[Pick counselor + date + TZ] --> B{Valid uuid date TZ?}
    B -->|No| C[Invalid inputs]
    B -->|Yes| D{Signed in as active student?}
    D -->|No| E[Only active students]
    D -->|Yes| F[Day bounds in TZ]
    F --> G[Booked = appointments counselor in day status pending|confirmed]
    G --> H[Generate hourly slots 09:00-16:00]
    H --> I[Subtract taken minutes]
    I --> J[Return free ISO slots]
```

**Django:** `core/services/slots.py` — port `lib/appointment-slots.ts`.

---

## 8. Student: book appointment

```mermaid
flowchart TD
    A[Appointments form] --> B{Valid body?<br/>counselor uuid scheduled concern notes≤2000}
    B -->|No| C[Invalid booking details]
    B -->|Yes| D{Future datetime?}
    D -->|No| E[Choose future date and time]
    D -->|Yes| F{Active student?}
    F -->|No| G[Only active students can book]
    F -->|Yes| H{Counselor exists role=counselor?}
    H -->|No| I[That counselor is not available]
    H -->|Yes| J{Clash: same counselor same minute pending|confirmed?}
    J -->|Yes| K[That time was just taken]
    J -->|No| L[INSERT status=pending]
    L -->|DB error| M[Could not save appointment]
    L -->|OK| N[log_action APPOINTMENT_CREATED]
    N --> O[Redirect /appointments success]
```

---

## 9. Student: cancel appointment

```mermaid
flowchart TD
    A[Cancel click] --> B{Own appointment?}
    B -->|No| C[Not found - RLS/scoping]
    B -->|Yes| D{status in cancelled|completed?}
    D -->|Yes| E[Can no longer be cancelled]
    D -->|No| F[UPDATE status=cancelled]
    F --> G[log_action APPOINTMENT_CANCELLED_STUDENT]
    G --> H[Success]
```

---

## 10. Counselor: status update (state machine)

```mermaid
flowchart TD
    A[Confirm or Cancel or Complete] --> B{Assigned counselor and active?}
    B -->|No| C[Only counselors / not yours]
    B -->|Yes| D{Current status?}
    D -->|completed or cancelled| E[Terminal - cannot update]
    D -->|pending or confirmed| F{Requested next?}
    F -->|confirmed| G{current is pending?}
    G -->|No| H[Only pending can be confirmed]
    G -->|Yes| I[Allow]
    F -->|completed| J{current is confirmed?}
    J -->|No - pending| K[Confirm before completing]
    J -->|Yes| I
    F -->|cancelled| L{current terminal?}
    L -->|Yes| M[Invalid]
    L -->|No| I
    I --> N[UPDATE status]
    N --> O[log_action APPOINTMENT_STATUS_UPDATED]
    O --> P[Success refresh workspace]
```

**Allowed transitions only:** pending→confirmed/cancelled; confirmed→completed/cancelled; completed/cancelled = terminal.

---

## 11. Case note save (encrypt + upsert)

```mermaid
flowchart TD
    A[Editor content + confidential toggle] --> B{Valid?<br/>appointment uuid content 1-50000}
    B -->|No| C[Validation error]
    B -->|Yes| D{Active counselor?}
    D -->|No| E[Only active counselors]
    D -->|Yes| F{Appointment assigned to me?}
    F -->|No| G[Not found or not yours]
    F -->|Yes| H[ENCRYPT AES-256-CBC hex]
    H -->|Key missing| I[Encryption failed]
    H -->|OK| J[Upsert UNIQUE appointment+counselor]
    J -->|counselor mismatch| K[Integrity error]
    J -->|DB error| L[Return error]
    J -->|OK| M[updated_at auto]
    M --> N[Signal → AuditLog + log_action CASE_NOTE_UPSERT]
    N --> O[Success]
```

---

## 12. Case note read / decrypt

```mermaid
flowchart TD
    A[get note] --> B{Active user?}
    B -->|No| C[Forbidden]
    B -->|Yes| D[Fetch note - query scoped]
    D -->|Missing| E[Not found]
    D -->|Found| F{Viewer is author?}
    F -->|Yes| G[DECRYPT]
    F -->|No| H{admin AND not confidential?}
    H -->|Yes| G
    H -->|No| I[May not view]
    G --> J{payload gc:v1:?}
    J -->|Yes| K[Legacy GCM decrypt]
    J -->|No| L[CBC hex decrypt]
    K & L --> M[Return plaintext + is_confidential]
```

**Student visibility:** only `is_confidential=False` rows appear in student queries.

---

## 13. Student mood check-in

```mermaid
flowchart TD
    A[Mood widget good|okay|low + note≤500] --> B{Valid?}
    B -->|No| C[Invalid check-in]
    B -->|Yes| D{Active student?}
    D -->|No| E[Only active students]
    D -->|Yes| F{mood == low?}
    F -->|No good/okay| G[log_action STUDENT_MOOD_CHECKIN] --> H[ok notified=false]
    F -->|Yes| I[Latest appointment status != cancelled]
    I -->|None| J[Error: book a session first or front desk]
    I -->|Found| K{Counselor profile still counselor?}
    K -->|No| L[Counselor no longer available]
    K -->|Yes| M[INSERT StudentMoodAlert]
    M -->|Need existing pair - scoping| N[Error if no appointment pair]
    M -->|OK| O[log_action STUDENT_MOOD_ALERT]
    O --> P[ok notified=true counselorName]
    P --> Q[Counselor workspace feed shows alert]
```

---

## 14. Chat: restore session

```mermaid
flowchart TD
    A[Widget opens] --> B{Signed in active student?}
    B -->|No| C[401/403]
    B -->|Yes| D[Rate limit GET 60/15min]
    D -->|Exceeded| E[429]
    D -->|OK| F[Latest ChatbotSession by student]
    F --> G[Return sessionId + messages or empty]
    G --> H[Hydrate or empty state]
```

---

## 15. Chat: send message (stream + persist)

```mermaid
flowchart TD
    A[User sends draft] --> B[Append user message<br/>cap history 36 content≤24000]
    B --> C[POST /chat/]
    C --> D{GROQ or ANTHROPIC key set?}
    D -->|No| E[503 not configured]
    D -->|Yes| F{Valid body last role=user?}
    F -->|No| G[400]
    F -->|Yes| H{Active student owns session?}
    H -->|No| I[401/403/400]
    H -->|Yes| J[Rate limit POST 24/15min]
    J -->|Exceeded| K[429 Retry-After]
    J -->|OK| L[System prompt: counselor assistant + escalate]
    L --> M[Stream upstream SSE]
    M -->|Error| N[502/401 error JSON]
    M -->|OK| O[Pump text deltas to client]
    O --> P[Accumulate assistant bubble]
    P --> Q{sessionId exists?}
    Q -->|Yes| R[Update messages JSON]
    Q -->|No| S[Create ChatbotSession]
    R & S -->|Error| T[SSE error could not save]
    R & S -->|OK| U[log_action CHAT_SESSION_UPSERT]
    U --> V[SSE done + sessionId]
    V --> W[Client finalize + CTA detect]
    W --> X{crisis or book phrase?}
    X -->|Yes| Y[Show Book appointment CTA]
    X -->|No| Z[No CTA]
    O -.->|mid stream fail| AA[Client toast + rollback messages]
```

**Rate limits:** POST 24/15 min · GET session 60/15 min · history max 36 · content ≤ 24000.

**CTA patterns (port `lib/chat/cta.ts`):** talk to counselor, book appointment, struggling, suicide, self-harm, crisis, etc.

---

## 16. Receptionist: 4-step booking

```mermaid
flowchart TD
    A[Guard receptionist active] --> B[Step1 searchStudents<br/>name or student_id ILIKE limit 25]
    B --> C[Select active student]
    C --> D[Step2 listReceptionCounselors<br/>active alphabetical + Next Available]
    D --> E[Step3 slots for date - any counselor free or specific]
    E --> F[Step4 book for student]
    F --> G{Valid future datetime + guard?}
    G -->|No| H[Errors]
    G -->|Yes| I{Student active?}
    I -->|No| J[Student not found or inactive]
    I -->|Yes| K{Active counselors exist?}
    K -->|No| L[No active counselors]
    K -->|Yes| M{Specific counselor requested?}
    M -->|Yes| N{In roster and free at minute?}
    N -->|No| O[Clash or unavailable]
    N -->|Yes| P[chosen = requested]
    M -->|No| Q[Loop counselors A-Z first free]
    Q -->|None| R[No counselor free at that time]
    Q -->|Found| P
    P --> S[INSERT status=pending]
    S --> T[log_action APPOINTMENT_CREATED_RECEPTION]
    T --> U[Confirmation UI with counselor name]
```

---

## 17. Admin: change user role

```mermaid
flowchart TD
    A[Users table role change] --> B{requireAdmin?}
    B -->|No| C[Redirect login]
    B -->|Yes| D{Target exists?}
    D -->|No| E[User not found]
    D -->|Yes| F{Admin being demoted?}
    F -->|Yes| G[Count admins]
    G -->|≤1| H[Cannot remove last admin]
    G -->|OK| I{Self demote?}
    F -->|No| I
    I -->|Yes| J[Cannot demote self]
    I -->|No| K[UPDATE role]
    K --> L[Success refresh]
```

---

## 18. Admin: activate / deactivate user

```mermaid
flowchart TD
    A[Toggle + confirm] --> B{requireAdmin?}
    B -->|No| C[Redirect]
    B -->|Yes| D{Deactivating self?}
    D -->|Yes| E[Cannot deactivate self]
    D -->|No| F{Target admin and deactivating?}
    F -->|Yes| G{active admin count ≤ 1?}
    G -->|Yes| H[Cannot deactivate last active admin]
    G -->|No| I[OK]
    F -->|No| I
    I --> J[UPDATE is_active]
    J --> K[Success]
    K -.-> L[Deactivated user next request blocked<br/>login shows deactivated]
```

---

## 19. Admin: dashboard metrics

```mermaid
flowchart TD
    A[Admin overview] --> B[requireAdmin]
    B --> C[Counts: students counselors<br/>appointments this month]
    C --> D[Completion rate completed/total]
    C --> E[8-week series Monday start]
    C --> F[Concern breakdown top 8 + other]
    D & E & F --> G[KPI cards + bar + pie]
    C --> H[Recent AuditLogs → view all]
```

**Port:** `lib/admin-metrics.ts` → `core/services/metrics.py`.

---

## 20. Admin: reports + export

```mermaid
flowchart TD
    A[Filters dateFrom dateTo dept concern status] --> B[Generate]
    B --> C{requireAdmin + valid range?}
    C -->|No| D[Errors]
    C -->|Yes| E[Query appointments in range]
    E --> F[Batch load profile names]
    F --> G[Optional department filter]
    G --> H[Preview table + summary]
    H --> I[0 rows? empty state]
    H --> J[Export PDF reportlab]
    J --> K[log_action REPORT_EXPORT]
    H --> L[Export CSV]
```

---

## 21. Admin: audit log viewer

```mermaid
flowchart TD
    A[ /admin-panel/audit ] --> B[requireAdmin]
    B --> C[Filters user action table date]
    C --> D[Query AuditLog scoped admin]
    D --> E[Paginate]
    E --> F[Table + expandable metadata JSON]
    E --> G[CSV export]
    E --> H[Empty state]
```

---

## 22. Student dashboard load

```mermaid
flowchart TD
    A[GET /student] --> B{role student active?}
    B -->|No| C[Redirect guard]
    B -->|Yes| D[Profile greeting]
    D --> E[Upcoming appointments]
    D --> F[History past/cancelled]
    D --> G[Non-confidential case history]
    D --> H[Mood widget]
    D --> I[Chat widget hydrate]
    E & F & G --> J[Render dashboard]
```

---

## 23. Counselor workspace load

```mermaid
flowchart TD
    A[GET /counselor] --> B{role counselor active?}
    B -->|No| C[Redirect]
    B -->|Yes| D[Stat chips today upcoming past]
    D --> E[Mood alerts feed counselor=me]
    D --> F[Today sessions + status actions]
    D --> G[Upcoming and Past tables]
    E & F & G --> H[Render workspace]
    F -->|actions| I[Flow 10 status machine]
    F -->|open note| J[Flow 11-12 case note]
```

---

## 24. Audit dual-writer (app + signal)

```mermaid
flowchart LR
    subgraph Explicit service calls
        A1[APPOINTMENT_*]
        A2[CASE_NOTE_UPSERT]
        A3[STUDENT_MOOD_*]
        A4[CHAT_SESSION_UPSERT]
        A5[REPORT_EXPORT]
    end
    subgraph Signals
        S1[Profile post_save/post_delete]
        S2[CaseNote post_save/post_delete]
    end
    A1 & A2 & A3 & A4 & A5 & S1 & S2 --> L[log_action never raises]
    L --> M[AuditLog insert user action table record_id metadata]
```

**Port:** `lib/audit.ts` — swallow all errors; invalid UUID `record_id` → null; missing user → skip.

---

## Implementation mapping

| Flow # | Phase | Primary Django modules |
|---|---|---|
| 1, 6 | 3 | `core/guards.py`, middleware |
| 2–5 | 3 | auth views/forms |
| 7–10 | 4 | `services/slots.py`, `services/appointments.py`, views |
| 11–12 | 5 | `services/encryption.py`, `services/case_notes.py` |
| 13 | 6 | `services/mood.py` |
| 14–15 | 6 | `services/chat.py`, chat views + JS |
| 16 | 4 | `services/receptionist.py`, receptionist views |
| 17–21 | 8 | admin views + `services/reports.py`, `metrics.py`, `audit.py` |
| 22–23 | 7 | page views + templates |
| 24 | 8 | `services/audit.py` + signals |
