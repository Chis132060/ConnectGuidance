# INTERFACES — 16 Screens + 1 Overlay (Django Templates)

Stitch design target from the original Next.js app. Phase 7 builds these as Django templates.

---

## Counts

| Section | Count | Routes |
|---|---:|---|
| Public | 3 | `/`, `/login/`, `/register/` |
| Student | 5 | `/student/`, `/appointments/`, `/chatbot/`, `/student/profile/`, `/student/front-desk/` |
| Counselor | 2 | `/counselor/`, `/counselor/case-notes/<uuid>/` (dynamic) |
| Admin | 5 | `/admin-panel/`, `/admin-panel/users/`, `/admin-panel/audit/`, `/admin-panel/reports/`, `/admin-panel/profile/` |
| Receptionist | 1 | `/receptionist/` |
| **Total pages** | **16** | |
| Overlay | +1 | Floating chat widget (on student dashboard + chatbot page) |

> Original also keeps Django built-in admin at `/admin/` optionally (ops only) — not counted in the 16.

---

## Design tokens (Stitch)

| Token | Value |
|---|---|
| Primary | `#2563EB` |
| Accent | `#0D9488` |
| Background | `#F8FAFC` |
| Cards | white, radius **12px**, subtle shadow |
| Buttons | radius **8px**, height 40px — primary blue / secondary white border / danger red / success green |
| Sidebar | `#0F172A` dark navy |
| Font | Inter / Poppins |
| Table header | `#F1F5F9`, row height 48px, hover `#F8FAFC` |
| Badges | 12px, rounded-full |
| Status colors | pending=amber, confirmed=blue, completed=green, cancelled=red |
| Role colors | Admin=red, Counselor=teal, Student=blue, Receptionist=violet |
| Concern colors | Academic=blue, Mental Health=purple, Career=orange, Personal=pink, Other=gray |
| Layout | desktop **1440px** |
| Spacing scale | 4 / 8 / 12 / 16 / 24 / 32 |

**Shared chrome:** fixed left sidebar (logo, role sub-nav, user chip) + top bar (title, notifications, avatar). One `base.html` with role blocks/includes.

**Every page needs:** empty state · loading (skeleton/JS) · error · success toast (`django.contrib.messages`).

---

## Screen specs

### 1. Landing `/` — `public/landing.html`
- Hero: “Guidance made accessible” + CTAs Register / Sign in
- Value props: Confidential, Convenient, Caring
- “Who it is for”: 3 cards — Student, Counselor, Program Lead
- Footer

### 2. Login `/login/` — `registration/login.html`
- Centered card, email + password, submit, link to register
- Query errors: `deactivated`, `no_profile`, `next` preserved

### 3. Register `/register/` — `registration/register.html`
- Fields: full name, student ID, school email, department, password ≥ 8
- Client + server validation parity with original Zod schema

### 4. Student dashboard `/student/` — `student/dashboard.html`
- Greeting, mood check-in widget (Good / Okay / Low + optional note)
- Upcoming appointment cards, case history list
- Floating chat button/widget

### 5. Appointments `/appointments/` — `student/appointments.html`
- Booking form: counselor select, date, slots 9AM–4PM, concern pills, notes ≤ 2000
- Tables: upcoming (+ Cancel), past & cancelled
- Status badges per token colors

### 6. Chatbot page `/chatbot/` — `student/chatbot.html`
- Info cards about AI assistant, crisis disclaimer banner
- Embedded chat widget

### 7. Student profile `/student/profile/` — `student/profile.html`
- Read-only: name, user_no, email, student_id, department
- Change password form

### 8. Front desk info `/student/front-desk/` — `student/front_desk.html`
- Static: how to book in person, what to bring

### 9. Counselor workspace `/counselor/` — `counselor/workspace.html`
- Stat chips: Today / Upcoming / Past
- Mood alert feed (red left border, note clamp 2 lines)
- Today’s sessions: time, student, concern badge, status badge
- Actions per state machine: Confirm (blue), Cancel (red outline), Complete (green); terminal → View note
- Tabbed table Upcoming / Past + pagination

### 10. Case note editor `/counselor/case-notes/<uuid>/` — `counselor/case_note.html`
- **Left sticky:** student summary card + appointment sub-card + confidentiality legend + back link
- **Right:** textarea (min 320px), encrypt helper text + lock, char counter
- Confidentiality switch, one-note-per-appointment info alert
- Sticky actions: Cancel · Save Note (spinner) · success toast · validation errors
- States: loading skeleton · new empty · existing upsert

### 11. Admin overview `/admin-panel/` — `admin/overview.html`
- KPI cards ×4: Total Students, Counselors, Monthly Appointments, Completion % (+ progress bar)
- Charts: weekly bar (8 weeks), concern donut (Chart.js or similar)
- Recent activity list → audit link

### 12. Users `/admin-panel/users/` — `admin/users.html`
- + Add user (modal/form), search, role filter, status filter, sort
- Table: avatar+name, user_no, student_id, department, role badge, status dot, joined, actions
- Inline role select + activate/deactivate toggle with confirm dialog
- Guards: cannot demote/deactivate self; cannot remove last admin

### 13. Audit logs `/admin-panel/audit/` — `admin/audit_logs.html`
- Filters: user, action, table, date range; Export CSV
- Table: timestamp, user, action badge, table, record_id (copy), metadata chip → expand JSON
- Pagination + empty state

### 14. Reports `/admin-panel/reports/` — `admin/reports.html`
- Filters: date range, department, concern, status, counselor
- Generate → summary strip + preview table (first 50 note)
- Export PDF (`reportlab`) + CSV + print
- Generating skeleton · empty results

### 15. Admin profile `/admin-panel/profile/` — `admin/profile.html`
- Account info card (read-only) + change password card (strength meter optional)

### 16. Receptionist `/receptionist/` — `receptionist/booking.html`
- **Step 1** Find student (search, results, selected chip)
- **Step 2** Counselor picker + **Next Available** highlight
- **Step 3** Date chips + hourly slot grid 9–16 (available/hover/selected/booked) + concern + notes
- **Step 4** Summary + Book → green confirmation (“Appointment booked”, status Pending, Book another)
- Error: slot just taken

### 17. Overlay — `widgets/chatbot.html`
- FAB bottom-right amber (`#B45309`-like as original) → panel 380×560, radius 16px
- Header: bot name, Online, New conversation, minimize
- Crisis banner dismissible
- User bubbles right blue; assistant left white; streaming three-dot
- CTA card “Book an appointment” when `should_suggest` matches
- Composer: rounded input, send disabled if empty
- States: empty starters · loading skeleton · error retry · new conversation reset
- Rate/limit notes as needed

---

## Template route checklist (Phase 7 verify)

| # | Route | Template file |
|---:|---|---|
| 1 | `/` | `public/landing.html` |
| 2 | `/login/` | `registration/login.html` |
| 3 | `/register/` | `registration/register.html` |
| 4 | `/student/` | `student/dashboard.html` |
| 5 | `/appointments/` | `student/appointments.html` |
| 6 | `/chatbot/` | `student/chatbot.html` |
| 7 | `/student/profile/` | `student/profile.html` |
| 8 | `/student/front-desk/` | `student/front_desk.html` |
| 9 | `/counselor/` | `counselor/workspace.html` |
| 10 | `/counselor/case-notes/<uuid>/` | `counselor/case_note.html` |
| 11 | `/admin-panel/` | `admin/overview.html` |
| 12 | `/admin-panel/users/` | `admin/users.html` |
| 13 | `/admin-panel/audit/` | `admin/audit_logs.html` |
| 14 | `/admin-panel/reports/` | `admin/reports.html` |
| 15 | `/admin-panel/profile/` | `admin/profile.html` |
| 16 | `/receptionist/` | `receptionist/booking.html` |
| + | include | `widgets/chatbot.html` |

**Sub-navs:** StudentSubnav · CounselorSubnav · AdminSubnav · ReceptionistSubnav (partial templates).

---

## CSS/JS approach (keep simple)

- Phase 7a: one `static/css/app.css` implementing tokens (no Tailwind build required)
- Charts: Chart.js via CDN for admin overview
- Chat: vanilla JS `fetch` + `ReadableStream`/SSE against Django streaming response
- Optional later: htmx for loading states

Do **not** need pixel-perfect Tailwind port — match structure, tokens, and states.
