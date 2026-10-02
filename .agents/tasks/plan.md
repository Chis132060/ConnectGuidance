# Implementation Plan: Minimal Design Redesign

## Overview
Redesign all user-facing pages in ConnectGuidance with a minimal, clean aesthetic. Remove visual complexity (gradients, animations, glassmorphism, shadows), maximize whitespace, simplify color palette to 2 colors, and create a cohesive minimal design system.

## Design System Specifications

### Color Palette (2 colors + neutrals)
- **Primary:** `#2563EB` (blue-600) — buttons, links, focus states
- **Text:** `#0F172A` (slate-900) — body text, headings
- **Muted:** `#64748B` (slate-500) — secondary text, labels
- **Background:** `#F8FAFC` (slate-50) — page background
- **Surface:** `#FFFFFF` — cards, forms, panels
- **Border:** `#E2E8F0` (slate-200) — dividers, input borders

### Typography
- **Font Stack:** `'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif`
- **Headings:** 600-700 weight, -0.01em letter-spacing
- **Body:** 400 weight, 1.6 line-height
- **Remove:** Poppins display font, multiple font weights

### Spacing Scale
- **xs:** 0.5rem (8px)
- **sm:** 1rem (16px)
- **md:** 1.5rem (24px)
- **lg:** 2rem (32px)
- **xl:** 3rem (48px)
- **Section gaps:** 1.5-2rem throughout

### Component Styles
- **Cards:** White background, 1px solid border, 8px border-radius, 1.5rem padding, no shadows
- **Buttons:** Flat design, 1px border, primary color fill or outline, no gradients/shadows, hover: opacity 0.9
- **Form Inputs:** 1px border, 8px border-radius, focus: primary color border only (no shadow)
- **Alerts:** Flat colored backgrounds, simple text, no icons
- **Navigation:** Flat hover states, no gradients, simple underline or background change

### What to Remove
- All gradients (linear-gradient, radial-gradient)
- All shadows (box-shadow) except focus states
- All animations (@keyframes, transition on transform/opacity)
- Glassmorphism (backdrop-filter, semi-transparent backgrounds)
- Animated orbs, pulse effects, glow effects
- Complex hover effects (transform, scale, translateY)
- Multiple color accent schemes per role

## Implementation Order

### Phase 1: Create Minimal Design System
**Files:** `static/css/minimal.css` (new), `templates/base.html` (update <link> tag)

**Steps:**
1. Create `static/css/minimal.css` with:
   - CSS reset and base styles
   - Design tokens (CSS custom properties in :root)
   - Typography styles
   - Component classes: .btn-minimal, .card-minimal, .form-input-minimal, .alert-minimal, .table-minimal
   - Layout utilities: .container-minimal, .grid-minimal-2, .grid-minimal-3, .grid-minimal-4
   - Responsive breakpoints (collapse grids at mobile)
2. Update `templates/base.html`: Change `<link rel="stylesheet" href="{% static 'css/app.css' %}">` to `<link rel="stylesheet" href="{% static 'css/minimal.css' %}">`
3. Simplify base.html sidebar: remove gradient brand icon, flat navigation, remove collapse animation

**Verify:** `python manage.py check` → 0 issues. Run dev server, visit any page, confirm minimal.css loads in browser DevTools.

### Phase 2: Redesign Public & Auth Pages
**Files:** `templates/public/landing.html`, `templates/registration/login.html`, `templates/registration/register.html`, `templates/registration/password_change.html`

**Landing Page (landing.html):**
1. Remove gradient background from .landing-hero, use solid white
2. Remove .landing-eyebrow gradient badge, simplify to flat text
3. Simplify .landing-title: remove gradient highlight, use solid primary color for "Guidance"
4. Reduce padding in hero section, increase whitespace between elements
5. Simplify .landing-card: remove hover transform, use .card-minimal class, flat borders
6. Remove all box-shadow rules

**Login Page (login.html):**
1. Remove gradient background from .auth-page, use solid white
2. Simplify .auth-card: apply .card-minimal, remove shadow
3. Remove .auth-logo-mark gradient, use solid primary background
4. Apply .form-input-minimal to email and password inputs
5. Apply .btn-minimal to submit button
6. Preserve all Django template tags, CSRF token, form field names

**Register Page (register.html):**
1. Same simplifications as login.html
2. Apply .form-input-minimal to all form inputs
3. Preserve Django form widgets and error display

**Password Change (password_change.html):**
1. Same simplifications as login/register
2. Preserve Django form structure

**Verify:** Run dev server. Test:
- Landing page loads, clean minimal design
- Login form submits correctly
- Register form submits correctly
- Password change form works
- All pages responsive at 375px, 768px, 1440px

### Phase 3: Redesign Student Pages (Remove Dark Themes)
**Files:** `templates/student/dashboard.html`, `templates/student/profile.html`, `templates/student/appointments.html`, `templates/student/book_appointment.html`, `templates/student/chatbot.html`, `templates/student/front_desk.html`

**Dashboard (dashboard.html):**
1. **REMOVE entire `<style>` block** (609 lines of sd-shell, orbs, glassmorphism, gradients, animations)
2. Restructure page with clean white background layout:
   - Wrap content in `<div class="container-minimal">`
   - Hero: `<div class="card-minimal">` with student name, basic info, no gradient avatar
   - Stats: `<div class="grid-minimal-4">` with flat stat cards (no gradients, no glow effects)
   - Appointments: Clean bordered sections with .card-minimal
   - Mood check-in: Simple radio buttons with labels, no animated icons
   - Quick links: Flat list with icon + text, no gradient backgrounds
3. Remove all animated orbs (sd-orb-1, sd-orb-2, sd-orb-3)
4. Simplify avatar: basic circle with initials, solid primary background, no animated ring
5. **Preserve all Django template logic:** {% if %}, {% for %}, {{ variables }}, {% url %}, {% csrf_token %}

**Profile (profile.html):**
1. **REMOVE entire `<style>` block** (pf-shell dark theme, orbs, glassmorphism)
2. Restructure to clean white background:
   - Container: `<div class="container-minimal">`
   - Header: flat card with avatar (circle, solid background, no animated ring)
   - Info card: `<div class="card-minimal">` with info grid
   - Password form: clean vertical layout with .form-input-minimal inputs
3. Remove all orbs, gradients, pulse animations
4. **Preserve Django password form widgets:** {{ password_form.old_password }}, etc.

**Other Student Pages:**
- appointments.html: Clean table with .table-minimal, remove inline styles
- book_appointment.html: Simplified booking form with .form-input-minimal
- chatbot.html: Clean chat interface, white background, remove dark theme
- front_desk.html: Simplified info layout with .card-minimal

**Verify:** Run dev server, login as student. Test:
- Dashboard displays data correctly
- Profile page loads, password form works
- Appointments page displays table
- Booking form works
- Chatbot opens and streams messages
- All functionality preserved

### Phase 4: Redesign Counselor Pages
**Files:** `templates/counselor/workspace.html`, `templates/counselor/case_note.html`

**Workspace (workspace.html):**
1. Remove all inline `style="..."` attributes
2. Convert sections to .card-minimal
3. Simplify stats cards: flat design, no gradients
4. Clean table layout with .table-minimal for appointments
5. Apply .btn-minimal to action buttons (Confirm, Complete, Cancel)
6. Preserve all Django forms and POST actions

**Case Note (case_note.html):**
1. Remove inline styles
2. Apply .card-minimal to note form
3. Apply .form-input-minimal to textarea
4. Preserve encrypted case note functionality

**Verify:** Run dev server, login as counselor. Test:
- Workspace displays appointments
- Status update buttons work
- Case note form submits correctly
- All functionality preserved

### Phase 5: Redesign Receptionist Pages
**Files:** `templates/receptionist/dashboard.html`, `templates/receptionist/booking.html`

**Dashboard (dashboard.html):**
1. Remove all inline `style="..."` attributes
2. Simplify 4-step booking form: clean vertical layout with .form-input-minimal
3. Convert main sections to .card-minimal
4. Clean student search results display
5. Preserve all JavaScript functionality for student search

**Booking (booking.html):**
1. Same simplifications as dashboard
2. Preserve walk-in booking workflow

**Verify:** Run dev server, login as receptionist. Test:
- Dashboard loads
- Student search works
- Booking form submits correctly
- Today's appointments display

### Phase 6: Redesign Admin Pages
**Files:** `templates/admin/overview.html`, `templates/admin/users.html`, `templates/admin/audit_logs.html`, `templates/admin/reports.html`, `templates/admin/profile.html`

**Overview (overview.html):**
1. Remove all inline `style="..."` attributes
2. Convert KPI cards to .grid-minimal-4 with .card-minimal
3. Simplify chart containers: clean white cards
4. Clean table layout with .table-minimal for audit activity
5. Preserve Chart.js integration

**Users (users.html):**
1. Remove inline styles
2. Apply .table-minimal to user table
3. Apply .btn-minimal to action buttons
4. Preserve user management functionality

**Audit Logs, Reports, Profile:**
1. Same pattern: remove inline styles, apply minimal classes
2. Preserve all functionality

**Verify:** Run dev server, login as admin. Test:
- Overview displays KPIs and charts
- User management works
- Audit logs display
- Report generation works
- Profile page loads

### Phase 7: Redesign Widgets & Partials
**Files:** `templates/widgets/chatbot.html`, `templates/partials/_messages.html`, `templates/partials/*_subnav.html`

**Chatbot Widget (chatbot.html):**
1. Simplify floating button: flat circle, no gradient, solid primary background
2. Clean chat panel: white background, simple 1px border, no glassmorphism
3. Preserve SSE streaming functionality and all JavaScript

**Messages Partial (_messages.html):**
1. Apply .alert-minimal classes
2. Remove complex alert styling

**Subnav Partials:**
1. Simplify navigation links: flat hover states (no gradients)
2. Clean icon + text layout
3. Remove active state gradients

**Verify:** Test chatbot widget opens on student pages, messages display correctly, navigation works

### Phase 8: Final Cleanup & Verification
**Files:** All templates

**Steps:**
1. Search all template files for remaining inline `style="..."` attributes
2. Search for remaining `<style>` blocks embedded in templates
3. Convert to minimal classes or remove decorative styling
4. Ensure no template has gradients, animations, or complex visual effects
5. Verify all forms, links, buttons remain functional
6. Test responsive design at all breakpoints
7. Verify WCAG contrast ratios
8. Test keyboard navigation

**Verify:**
- Run `python manage.py check` → 0 issues
- Run `python manage.py test` → all tests pass
- Manual testing: browse all 16 pages as each role
- Responsive testing: resize browser to 375px, 768px, 1440px
- WCAG testing: check contrast ratios (blue #2563EB on white = 4.63:1 passes AA)
- Keyboard testing: Tab through all forms and links

## Files Modified

### Created
- `static/css/minimal.css` — complete minimal design system

### Modified
- `templates/base.html` — load minimal.css, simplify sidebar
- `templates/public/landing.html` — minimal landing page
- `templates/registration/login.html` — minimal login form
- `templates/registration/register.html` — minimal register form
- `templates/registration/password_change.html` — minimal password form
- `templates/student/dashboard.html` — remove dark theme, minimal redesign
- `templates/student/profile.html` — remove dark theme, minimal redesign
- `templates/student/appointments.html` — minimal table layout
- `templates/student/book_appointment.html` — minimal booking form
- `templates/student/chatbot.html` — minimal chat interface
- `templates/student/front_desk.html` — minimal info layout
- `templates/counselor/workspace.html` — minimal workspace
- `templates/counselor/case_note.html` — minimal note form
- `templates/receptionist/dashboard.html` — minimal dashboard
- `templates/receptionist/booking.html` — minimal booking workflow
- `templates/admin/overview.html` — minimal admin overview
- `templates/admin/users.html` — minimal user management
- `templates/admin/audit_logs.html` — minimal audit log display
- `templates/admin/reports.html` — minimal reports page
- `templates/admin/profile.html` — minimal admin profile
- `templates/widgets/chatbot.html` — minimal chatbot widget
- `templates/partials/_messages.html` — minimal alerts
- `templates/partials/student_subnav.html` — minimal navigation
- `templates/partials/counselor_subnav.html` — minimal navigation
- `templates/partials/admin_subnav.html` — minimal navigation
- `templates/partials/receptionist_subnav.html` — minimal navigation

## Constraints

### Must Preserve
- All Django template inheritance ({% extends "base.html" %})
- All Django template blocks ({% block content %}, {% block title %}, etc.)
- All Django template logic ({% if %}, {% for %}, {% url %})
- All CSRF tokens ({% csrf_token %})
- All form field names and Django form widgets
- All form validations and security features
- All RBAC and authentication guards
- All links, buttons, and navigation
- All data display (template variables like {{ profile.full_name }})
- All JavaScript functionality (student search, chatbot streaming, Chart.js)

### Must Remove
- All `linear-gradient()` and `radial-gradient()`
- All `box-shadow` (except focus states: `0 0 0 3px` ring)
- All `@keyframes` animations
- All `backdrop-filter` glassmorphism
- All animated orbs, pulse effects, glow effects
- All complex hover effects (`transform: translateY`, `scale`)
- All embedded `<style>` blocks in templates (move to minimal.css or remove)
- All inline `style="..."` attributes (convert to classes)

## Success Criteria

- [ ] All 16 templates redesigned with minimal aesthetic
- [ ] Color palette limited to 2 colors: primary blue and neutral slate
- [ ] Single font family: Inter sans-serif
- [ ] Generous whitespace: 1.5-2rem spacing between sections
- [ ] All gradients removed
- [ ] All shadows removed (except focus)
- [ ] All animations removed
- [ ] All glassmorphism removed
- [ ] All inline styles and `<style>` blocks removed
- [ ] All functionality preserved: forms, links, RBAC, data display
- [ ] Responsive design works at 375px, 768px, 1440px
- [ ] WCAG AA contrast ratios pass
- [ ] Keyboard navigation works
- [ ] `python manage.py check` → 0 issues
- [ ] `python manage.py test` → all tests pass
- [ ] Manual testing: all pages load and function correctly

---

**Note:** This plan is the fallback implementation guide. If FEAT decomposition succeeds, the workflow will execute via per-FEAT coder steps instead of this monolithic plan.
