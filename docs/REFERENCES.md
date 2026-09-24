# REFERENCES — Original Next.js source map

**Original project:** `C:\School works\4yr_firstsem\connectguidance1`  
Use when porting a phase — open the listed files for exact behavior.

---

## Master documents (original repo)

| Resource | Path |
|---|---|
| System analysis + SRS (1374 lines) | `../connectguidance1/SYSTEM_ANALYSIS_AND_SRS.md` |
| AGENTS / Next.js notes | `../connectguidance1/AGENTS.md` |
| Package manifest | `../connectguidance1/package.json` |

---

## Database (source of ERD)

| Resource | Path |
|---|---|
| All SQL migrations (18) | `../connectguidance1/supabase/migrations/*.sql` |
| Concat run-once script | `../connectguidance1/supabase/apply_all_migrations.sql` |
| Init (5 tables + RLS + triggers) | `.../20260401123000_init_guidanceconnect.sql` |
| Case note integrity trigger | `.../20260402200000_case_notes_integrity.sql` |
| Profile on signup trigger | `.../20260402220000_auth_user_profile_trigger.sql` |
| Receptionist role enum | `.../20260403120000_app_role_receptionist.sql` |
| user_no sequence | `.../20260403130000_profiles_user_no.sql` |
| Mood alerts table + RLS | `.../20260403170000_student_mood_alerts.sql` |
| Backfill utility | `../connectguidance1/supabase/backfill_profiles_from_auth.sql` |

**Django translation:** see `docs/ERD.md` + `docs/RLS_AND_SECURITY.md`.

---

## Server actions (business logic — Phase 4–6, 8)

| Feature | Path | Django target |
|---|---|---|
| Book / cancel / status / slots | `../connectguidance1/actions/appointments.ts` | `core/services/appointments.py`, `slots.py` |
| Case notes encrypt/upsert/read | `../connectguidance1/actions/caseNotes.ts` | `core/services/case_notes.py` |
| Mood check-in | `../connectguidance1/actions/student-mood.ts` | `core/services/mood.py` |
| Receptionist search/slots/book | `../connectguidance1/actions/receptionist.ts` | `core/services/receptionist.py` |
| Reports generate + export audit | `../connectguidance1/actions/reports.ts` | `core/services/reports.py` |
| Admin role + activate/deactivate + PDF rows | `../connectguidance1/app/admin/actions.ts` | admin views/services |
| Counselor status wrapper | `../connectguidance1/app/counselor/actions.ts` | appointments service |

---

## Libraries (Phase 4–8)

| Feature | Path | Django target |
|---|---|---|
| Hourly slots / day bounds / TZ | `../connectguidance1/lib/appointment-slots.ts` | `core/services/slots.py` |
| AES encryption | `../connectguidance1/lib/encryption.ts` | `core/services/encryption.py` |
| Audit logAction | `../connectguidance1/lib/audit.ts` | `core/services/audit.py` |
| Admin metrics/charts | `../connectguidance1/lib/admin-metrics.ts` | `core/services/metrics.py` |
| Concern presets | `../connectguidance1/lib/concerns.ts` | `core/choices.py` |
| Role homes + route prefixes | `../connectguidance1/lib/auth/routes.ts` | `core/guards.py` |
| Edge proxy role redirects | `../connectguidance1/lib/proxy-handler.ts` | guards/middleware |
| requireAdmin | `../connectguidance1/lib/supabase/admin-guard.ts` | `role_required('admin')` |
| requireReceptionist | `../connectguidance1/lib/supabase/receptionist-guard.ts` | `role_required('receptionist')` |
| Chat rate limits | `../connectguidance1/lib/rate-limit/chat.ts` | chat rate limiter |
| Chat CTA patterns | `../connectguidance1/lib/chat/cta.ts` | chat service |
| Chat system prompt | `../connectguidance1/lib/chat/constants.ts` | chat service |

---

## API routes (Phases 3, 6)

| Route | Path | Django target |
|---|---|---|
| Signup | `../connectguidance1/app/api/auth/signup/route.ts` | register view |
| Signin | `../connectguidance1/app/api/auth/signin/route.ts` | login view |
| Signout | `../connectguidance1/app/api/auth/signout/route.ts` | logout view |
| OAuth callback | `../connectguidance1/app/auth/callback/route.ts` | optional / skip (no Supabase OAuth) |
| Chat stream | `../connectguidance1/app/api/chat/route.ts` | streaming chat view |
| Chat session restore | `../connectguidance1/app/api/chat/session/route.ts` | session GET |

---

## Pages → templates (Phase 7)

| Original page | Django template |
|---|---|
| `app/page.tsx` | `public/landing.html` |
| `app/login/page.tsx` | `registration/login.html` |
| `app/register/page.tsx` + `register-form.tsx` | `registration/register.html` |
| `app/student/page.tsx` | `student/dashboard.html` |
| `app/appointments/page.tsx` | `student/appointments.html` |
| `app/chatbot/page.tsx` | `student/chatbot.html` |
| `app/student/profile/page.tsx` | `student/profile.html` |
| `app/student/front-desk/page.tsx` | `student/front_desk.html` |
| `app/counselor/page.tsx` | `counselor/workspace.html` |
| `app/counselor/case-notes/[id]/page.tsx` | `counselor/case_note.html` |
| `app/admin/page.tsx` | `admin/overview.html` |
| `app/admin/users/page.tsx` | `admin/users.html` |
| `app/admin/audit-logs/page.tsx` | `admin/audit_logs.html` |
| `app/admin/reports/page.tsx` | `admin/reports.html` |
| `app/admin/profile/page.tsx` | `admin/profile.html` |
| `app/receptionist/page.tsx` | `receptionist/booking.html` |
| `components/ChatbotWidget.tsx` | `widgets/chatbot.html` + JS |

---

## Components worth porting (UI behavior)

| Component | Path |
|---|---|
| Chat widget | `../connectguidance1/components/ChatbotWidget.tsx` |
| Password change form | `../connectguidance1/components/student/StudentChangePasswordForm.tsx` |
| Mood check-in | `../connectguidance1/components/student/StudentMoodCheckIn.tsx` |
| Receptionist booking form | `../connectguidance1/components/receptionist/ReceptionistBookingForm.tsx` |
| Role subnavs | `../connectguidance1/components/**` (`StudentSubnav`, `AdminSubnav`, …) |

---

## This Django repo docs

| Doc | Purpose |
|---|---|
| [PLAN.md](./PLAN.md) | Phases 1–8 master step list |
| [ERD.md](./ERD.md) | Models spec |
| [FLOWS.md](./FLOWS.md) | 24 flowcharts |
| [INTERFACES.md](./INTERFACES.md) | 16 screens + tokens |
| [RLS_AND_SECURITY.md](./RLS_AND_SECURITY.md) | Access control port |
