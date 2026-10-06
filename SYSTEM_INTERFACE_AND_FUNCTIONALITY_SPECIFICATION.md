# ConnectGuidance — System Interface & Functionality Specification

This document provides a comprehensive, complete reference of every user interface, page, modal, button, form field, data model, and functional capability currently implemented in the **ConnectGuidance** Guidance & Counseling Management System at Father Saturnino Urios University (FSUU).

---

## 1. Architectural Overview & Role-Based Access Control (RBAC)

ConnectGuidance operates on **Django 4.x/5.x** with a clean architecture separating **accounts** (authentication and user profiles) and **core** (counseling domain, clinical notes, appointment scheduling, AI chatbot, and administrative auditing).

### 1.1 User Roles
The platform defines 4 authenticated user roles plus unauthenticated visitors:

| Role Code | Display Name | Primary Workspace / Landing | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| `*` *(Public)* | Public Visitor | `/` (Landing Page) | Learn about guidance services, register student account, log in. |
| `student` | University Student | `/student/` | Book appointments, track schedule, perform mood check-ins, chat with 24/7 AI counselor. |
| `counselor` | Licensed Counselor | `/counselor/` | Manage daily schedule, triage mood alerts, author AES-256 encrypted clinical case notes. |
| `receptionist`| Front Desk Staff | `/receptionist/dashboard/` | Manage student walk-in intake, triage desk queue, book appointments for walk-in students. |
| `admin` | System Administrator | `/admin-panel/` | Executive KPIs, appointment registry, user administration, CSV/PDF reports, audit logs. |

---

## 2. Global Shell & Navigation Elements

The authenticated shell is shared across all logged-in views via `templates/common/base.html`.

### 2.1 Collapsible Sidebar (`#appSidebar`)
* **Brand Logo & Title**: Displays the `✦ ConnectGuidance` brand link pointing to `/home/` (automatic role redirector).
* **Sidebar Toggle Button (`#sidebarToggle`)**: Minimizes or expands the sidebar on desktop and mobile viewports.
* **Role-Specific Sub-Navigation**: Automatically renders the active navigation links for the logged-in role:
  * **Student Subnav**: *Dashboard, Appointments, AI Assistant, Front Desk, My Profile*.
  * **Counselor Subnav**: *Dashboard, Appointments, Case Notes, Student / Wellness, Profile*.
  * **Receptionist Subnav**: *Dashboard, Appointments / Walk-ins, Front Desk, Profile*.
  * **Admin Subnav**: *Dashboard, Analytics & Reports, User Management, Audit Logs, Appointments, Profile*.
* **Sidebar Footer (User Chip)**:
  * User avatar badge containing the first initial of the user's full name.
  * User full name and role badge display.
  * **Sign Out Button**: Text/icon link invoking `/logout/`.

### 2.2 Topbar (`.app-topbar`)
* **Left Section**: Displays the active page title heading (`<h1>`).
* **Right Section**:
  * **Role Badge / Pill**: Visual badge indicating the active user's role (colored by role token).
  * **Sign Out Button (`.btn-secondary.btn-sm`)**: Direct link to `/logout/`.

### 2.3 Toast & Alert Notification System (`_messages.html`)
* Renders animated, dismissible alert banners for system messages:
  * **Success**: Green banner with checkmark icon for successful bookings, updates, and saves.
  * **Error / Danger**: Red banner with alert icon for validation errors or forbidden requests.
  * **Warning**: Amber banner for alerts and rate limit notices.
  * **Info**: Blue banner for informational notices.

---

## 3. Public & Authentication Portal

### 3.1 Public Landing Page (`/` — `landing_view`)
* **Template**: [templates/common/landing.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/common/landing.html)
* **Header**:
  * Brand mark `✦ ConnectGuidance` (links to `/`).
  * **Sign In Button**: Navigates to `/login/`.
  * **Get Started Button**: Navigates to `/register/`.
* **Hero Section**:
  * Eyebrow badge: `Father Saturnino Urios University • Guidance & Counseling`.
  * Headline: *"Your Mental Health, Supported Every Step"*.
  * Subtitle explaining unified support for students, counselors, and staff.
  * **CTA Buttons**:
    * **"Sign In to Your Portal" Button (`#hero-signin-btn`)**: Primary blue CTA linking to `/login/`.
    * **"Register as Student" Button (`#hero-register-btn`)**: Ghost button linking to `/register/`.
  * **Live Platform Stats**: 4 Role-Based Portals, 24/7 AI Wellness Support, AES-256 Encrypted Case Notes, 100% Confidential Sessions.
* **Role Overview Grid ("One Platform, Four Portals")**:
  * **Student Card (`#card-student`)**: Features listed — Book & manage appointments, AI wellness chatbot, Daily mood check-ins.
  * **Counselor Card (`#card-counselor`)**: Features listed — Clinical case notes, Appointment triage, Student wellness monitor.
  * **Receptionist Card (`#card-receptionist`)**: Features listed — Walk-in desk triage, Student intake, Rapid appointment scheduling.
  * **Admin Card (`#card-admin`)**: Features listed — Executive analytics, User management, Immutable audit trail.
* **Feature Highlights Grid**:
  * Automated Appointments & Slots, AES-256 Encrypted Case Notes, ConnectGuidance AI Assistant, Real-time Mood Tracking, Immutable Audit Logging, Role-Based Access Control.
* **Emergency Crisis Support Strip**:
  * Prominent contact information for the 988 Suicide & Crisis Lifeline, FSUU Campus Security, and Guidance Office Room 204.
* **Footer**:
  * University copyright, institutional links, and confidentiality disclosures.

### 3.2 Sign In Page (`/login/` — `login_view`)
* **Template**: [templates/authentication/login.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/authentication/login.html)
* **Inputs & Controls**:
  * **Username or Email Input (`#id_username`)**: Accepts student ID, staff username, or institutional email.
  * **Password Input (`#id_password`)**: Password field with an integrated toggle button to reveal or mask characters.
  * **Remember Me / Session Checkbox**: Keeps session authenticated across browser restarts.
  * **"Sign In" Button**: Submits POST request to authenticate credentials.
* **Links**:
  * *"Don't have an account? Register as Student"* link leading to `/register/`.

### 3.3 Student Registration Page (`/register/` — `register_view`)
* **Template**: [templates/authentication/register.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/authentication/register.html)
* **Inputs & Controls**:
  * **Full Name Input**: Student's complete legal name.
  * **Institutional Email Input**: University email address (validated format).
  * **Student ID Input**: Official FSUU student number (e.g. `2024-00123`).
  * **Department / College Dropdown / Input**: Academic program or department.
  * **Password & Password Confirmation Inputs**: Enforces minimum length and security standards.
  * **"Create Student Account" Button**: Registers account, automatically assigns the `student` role, generates unique `user_no`, and logs initial audit record.
* **Links**:
  * *"Already have an account? Sign In"* link leading to `/login/`.

### 3.4 Password Change (`/password-change/` — `password_change_view`)
* **Template**: [templates/authentication/password_change.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/authentication/password_change.html)
* **Inputs & Controls**:
  * Old password input.
  * New password and confirmation inputs.
  * **"Update Password" Button**: Validates current credentials and applies new hash.

---

## 4. Student Portal

### 4.1 Student Dashboard (`/student/` — `student_dashboard_view`)
* **Template**: [templates/student/dashboard.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/student/dashboard.html)
* **Welcome Header**:
  * Student avatar initial badge.
  * Greeting with Student Full Name, Student ID, and Department tag.
  * **"Book Session" Button (`.btn-primary`)**: Quick jump to `/appointments/book/`.
  * **"My Schedule" Button (`.btn-secondary`)**: Quick jump to `/appointments/`.
* **Stats KPI Grid (4 Cards)**:
  * **Upcoming Sessions**: Total pending/confirmed appointments scheduled in the future.
  * **Completed**: Total sessions attended and completed.
  * **Office Hours**: Display of standard office schedule (Mon–Fri 09:00 AM – 04:00 PM).
  * **AI Assistant**: 24/7 Availability badge with direct **"Launch Chatbot →"** text link to `/chatbot/`.
* **Next Consultation Card**:
  * Date Block (Month, Day, Time formatted).
  * Assigned Counselor Avatar, Full Name, and Department.
  * Badges: Status (`Confirmed` or `Pending`), Concern Type (Academic, Personal, Career, Crisis), Location (`Room 204`).
  * Student Notes preview (if provided).
  * **"View All Appointments →"** navigation link.
  * **"Cancel" Button**: Submits POST to `/appointments/<id>/cancel/` with a browser confirmation dialog.
  * *Empty State*: Displays friendly prompt with a **"Schedule Session"** CTA button if no upcoming appointment exists.
* **Daily Wellness Check-in Card (Confidential)**:
  * Radio card selection:
    * **Good** (Energetic & balanced, green smiley icon).
    * **Okay** (Getting through, blue neutral icon).
    * **Low** (Needing support, amber frown icon).
  * **Reflection Note Textarea (`#id_mood_note`)**: Optional reflection text (max 500 characters).
  * **Triage Notice**: Clear disclaimer stating that selecting **Low** alerts your counselor for discreet follow-up.
  * **"Submit" Button**: Submits check-in to `/student/mood/`, records audit log, and creates `StudentMoodAlert` if "low".
* **Counselor Shared Notes Section**:
  * Renders non-confidential follow-up notes shared by the student's counselor.
* **Right Sidebar Column**:
  * **Emergency & Crisis Assistance Card**: Contact cards for 988 Crisis Lifeline, Campus Security, Guidance Office Room 204.
  * **Quick Navigation Links**: Booking, Front Desk information, Profile.

### 4.2 Book Appointment Wizard (`/appointments/book/` — `student_book_appointment_view`)
* **Template**: [templates/student/book_appointment.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/student/book_appointment.html)
* **Header & Step Progress Bar (`#bkSteps`)**:
  * Visual progress indicator: Step 1 (Counselor) -> Step 2 (Date & Time) -> Step 3 (Details) -> Step 4 (Confirm).
  * **"Appointments" Back Link**: Returns to `/appointments/`.
* **Interactive Booking Form (`#bookingForm`)**:
  * **Counselor Select (`#id_counselor`)**: Dropdown of licensed guidance counselors.
  * **Appointment Date Input (`#id_date`)**: Date selection input with flatpickr integration.
  * **Dynamic Time Slots Section (`#bkSlotsSection`)**:
    * Dynamically queries `/appointments/slots/?counselor_id=X&date=YYYY-MM-DD` via AJAX.
    * Shows animated loading dots while fetching availability.
    * Renders clickable hourly slot buttons (e.g. `09:00 AM`, `10:00 AM`, `11:00 AM`, `01:00 PM`, `02:00 PM`, `03:00 PM`).
    * Slots that are already booked or in the past are automatically struck through and disabled.
    * Clicking an active slot applies the active gradient styling and populates `#id_time`.
  * **Primary Concern Select (`#id_concern_type`)**: Academic, Personal, Career, Crisis / Emergency.
  * **Session Notes Textarea (`#id_notes`)**: Optional details or questions for the counselor (max 2000 characters).
  * **"Confirm Appointment Booking" Submit Button (`.bk-submit`)**: Submits booking, triggers audit logging, and redirects to appointments schedule.

### 4.3 Student Appointments Schedule (`/appointments/` — `student_appointments_list_view`)
* **Template**: [templates/student/appointments.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/student/appointments.html)
* **Header**: Breadcrumbs, Title, and **"Book New Session" Button**.
* **Stats Strip**: Active Bookings count, Past Consultations count, 100% Confidential Service indicator.
* **Upcoming Sessions Section**:
  * Cards showing Date Block, Counselor details, Room 204 location badge, Concern tag, Status badge (`Pending` / `Confirmed`).
  * Student intake notes block.
  * **"Cancel Appointment" Button**: Submits cancellation request with confirm prompt.
* **Past Consultations Section**:
  * History list of prior sessions with statuses: `Completed`, `Cancelled`, `No-Show`.

### 4.4 Full-Page AI Guidance Assistant (`/chatbot/` — `student_chatbot_page_view`)
* **Template**: [templates/student/chatbot.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/student/chatbot.html)
* **Header**:
  * **"Dashboard" Back Link**: Returns to `/student/`.
  * Status Indicator: Pulsing green dot with *"Online · Warm, empathetic academic & wellness support"*.
* **Crisis Support Banner**: Red alert emphasizing that the assistant does not replace clinical therapy and provides the 988 hotline.
* **Dynamic Booking Recommendation Banner (`#cgCtaBanner`)**:
  * Automatically reveals when the AI detects that the student may benefit from speaking to a human counselor.
  * Contains a **"Book Session" Button** linking to `/appointments/book/`.
* **Chat Messages Container (`#cgMessages`)**:
  * Displays message bubbles for user (blue gradient, aligned right) and assistant (white border card, aligned left).
  * Formatted with `white-space: pre-wrap` to preserve structured line breaks and paragraphs.
  * Streams responses in real-time via Server-Sent Events (SSE).
* **Welcome Card (`#cgWelcome`)**: Friendly onboarding card shown when conversation history is empty.
* **Interactive Quick Suggestion Chips (`#cgChips`)**:
  * *"Feeling overwhelmed"* -> Sends "I'm feeling overwhelmed with my coursework".
  * *"Study tips"* -> Sends "Can you help me with study tips and time management?".
  * *"Exam stress"* -> Sends "How do I manage exam stress effectively?".
  * *"Campus resources"* -> Sends "What campus wellness resources are available?".
  * *"Work-life balance"* -> Sends "I need advice on balancing academics and social life".
* **Composer Input Area**:
  * **Textarea (`#cgInput`)**: Auto-resizing textarea (max 1200 characters), sends on Enter (Shift+Enter for new line).
  * **Send Button (`#cgSendBtn`)**: Submits message to `/chat/` streaming endpoint.
  * **Animated Thinking Indicator (`#cgThinking`)**: Displays 3 pulsing dots during model inference.
* **Session Persistence**: Automatically hydrates existing chat history from `/chat/session/`.

### 4.5 Student Front Desk Information (`/student/front-desk/` — `student_front_desk_view`)
* **Template**: [templates/student/front_desk.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/student/front_desk.html)
* **Office Location Card**: Student Center Building, 2nd Floor, Room 204 with *"Currently Accepting Walk-Ins"* indicator.
* **Office Hours Card**: Detailed schedule for weekdays (08:00 AM – 05:00 PM) and walk-in consultation hours.
* **Walk-in Consultation Guidelines**: Step-by-step instructions for queuing at the receptionist desk.
* **Emergency Crisis Numbers**: Direct contacts for campus emergency triage and psychological hotlines.

### 4.6 Student Profile (`/student/profile/` — `student_profile_view`)
* **Template**: [templates/student/profile.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/student/profile.html)
* **Student Record Card**: Displays Student ID, Full Name, Email, Department, System User Number, Account Creation Date.
* **Password Change Form**: Standard secure password update form.

---

## 5. Global Floating AI Chat Widget (`widgets/chatbot.html`)

Rendered on every student page via `templates/common/base.html`.

* **Floating Action Button (FAB) (`#cg-chat-fab`)**:
  * 58px circular floating sapphire button anchored at the bottom-right corner.
  * Toggles the overlay panel open and closed.
* **Floating Chat Panel (`#cg-chat-panel`)**:
  * 380px x 560px modal panel with dark sapphire styling and glassmorphism backdrop blur.
  * **Header Controls**:
    * Online status indicator dot.
    * Title: *"Guidance Assistant — Online & 24/7 Confidential Support"*.
    * **"New Conversation" Reset Button (`#cg-chat-reset`)**: Clears the conversation history and resets session.
    * **"Minimize" Close Button (`#cg-chat-close`)**: Closes the widget panel.
  * **Dismissible Crisis Alert (`#cg-crisis-banner`)**: Inline 988 banner with dismiss (X) button.
  * **Dynamic Booking Banner (`#cg-widget-cta`)**: Appears when counseling keywords are matched, offering a 1-click **"Book" Button**.
  * **Scrollable Message Box (`#cg-widget-messages`)**: Preserves formatting via `white-space: pre-wrap`.
  * **Composer Form (`#cg-widget-form`)**: Rounded input (`#cg-widget-input`) and circular gradient send button (`#cg-widget-send`).

---

## 6. Counselor Clinical Workspace

### 6.1 Counselor Workspace Dashboard (`/counselor/` — `counselor_workspace_view`)
* **Template**: [templates/counselor/workspace.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/counselor/workspace.html)
* **Header**: Provider Name, Department, and live Date display.
* **Stats KPI Grid (4 Cards)**:
  * **Today's Sessions**: Count of appointments scheduled for the current day.
  * **Pending Requests**: Unconfirmed appointments awaiting counselor action.
  * **Upcoming (Future)**: Total future bookings on the schedule.
  * **Total Completed**: Cumulative number of completed sessions.
* **Today's Schedule Section**:
  * Cards for each session today displaying Student Name, Student ID, Time, Concern Category, and Student Notes.
  * **Status Update Controls**: Quick buttons/dropdown to change status:
    * `Confirmed` -> Validates session.
    * `Completed` -> Marks session finished (unlocks case note authoring).
    * `Cancelled` -> Cancels session.
    * `No-Show` -> Records student absence.
  * **"Write Case Note" / "Edit Case Note" Button**: Navigates directly to the clinical note editor for that appointment (`/counselor/case-notes/<id>/`).
* **Recent Student Mood Alerts Box**:
  * Flags students with assigned appointments who reported **Low** mood check-ins, allowing timely clinical outreach.

### 6.2 Counselor Appointments Registry (`/counselor/appointments/` — `counselor_appointments_view`)
* **Template**: [templates/counselor/appointments.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/counselor/appointments.html)
* **Controls & Filters**:
  * Status tabs (`All`, `Pending`, `Confirmed`, `Completed`, `Cancelled`).
  * Date range and search filters.
* **Appointments Table / Cards**:
  * Lists scheduled appointments with full student metadata.
  * Status modification dropdown with immediate save.
  * Link to author/review clinical case note for each session.

### 6.3 Counselor Case Notes List (`/counselor/case-notes/` — `counselor_case_notes_list_view`)
* **Template**: [templates/counselor/case_notes_list.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/counselor/case_notes_list.html)
* **Directory Table**:
  * Displays all case notes authored by the logged-in counselor.
  * Columns: Student Name, Session Date, Concern Type, Confidentiality Flag, Last Updated.
  * **"Open Case Note" Button**: Opens the note editor.

### 6.4 Clinical Case Note Editor (`/counselor/case-notes/<id>/` — `counselor_case_note_view`)
* **Template**: [templates/case_notes/editor.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/case_notes/editor.html)
* **Security & Grounding Notice**: Explains AES-256 Fernet encryption at rest and author-only access control.
* **Appointment Summary Card**:
  * Student Name, ID, Department, Session Time, Concern Category, Appointment Status, and Note Save Status.
* **Case Note Editor Form**:
  * **Clinical Assessment & Session Notes Textarea (`form.content`)**: Decrypted in-memory for the author and displayed for editing.
  * **"Mark as Confidential (Author-Only)" Checkbox (`form.is_confidential`)**:
    * When checked, ensures that *only* the author counselor can view and decrypt the note. Students and administrators cannot read confidential notes.
  * **Action Buttons**:
    * **"Cancel" Button**: Returns to `/counselor/`.
    * **"Save Encrypted Note" Button**: Encrypts note with AES-256 before saving to the database, logs audit entry, and confirms save.

### 6.5 Student & Wellness Information (`/counselor/wellness/` — `counselor_wellness_view`)
* **Template**: [templates/counselor/wellness.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/counselor/wellness.html)
* **Header**: Breadcrumbs, Title, and **"Clinical Schedule" Button**.
* **KPI Stats**:
  * **Advised Students**: Count of unique students consulting with this counselor.
  * **Wellness Alerts Dispatched**: Total flagged "low" mood alerts assigned to this counselor.
* **Urgent Mood Alerts Table**:
  * Columns: Date & Time, Student Name & Email, Student ID, Reported Wellness Note, Actions (**"Book Follow-up"** / **"Review Profile"**).
* **Student Roster Table**:
  * Roster of past and active students with session totals and latest consultation dates.

### 6.6 Counselor Profile (`/counselor/profile/` — `counselor_profile_view`)
* **Template**: [templates/counselor/profile.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/counselor/profile.html)
* Provider profile information, department assignment, and password change utility.

---

## 7. Receptionist Front Desk Portal

### 7.1 Receptionist Dashboard (`/receptionist/dashboard/` — `receptionist_dashboard_view`)
* **Template**: [templates/receptionist/dashboard.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/receptionist/dashboard.html)
* **Header Buttons**:
  * **"Live Desk Queue" Button**: Links to `/receptionist/front-desk/`.
  * **"New Walk-in Booking" Button**: Links to `/receptionist/`.
* **4 KPI Stat Cards**:
  * **Today's Total Bookings**: Aggregate session volume for the current day.
  * **Confirmed & Ready**: Confirmed sessions ready for student arrival.
  * **Pending Approval**: Appointments awaiting counselor confirmation.
  * **Active Counselors On Duty**: Counselors available for immediate walk-in triage.
* **Today's Scheduled Consultations Table**:
  * Lists today's intake queue: Scheduled Time, Student Patient, Assigned Counselor, Concern Type, Status, Actions.
  * **"Add Walk-in" Button**: Direct shortcut to create an on-the-spot appointment.

### 7.2 Walk-in Booking Wizard (`/receptionist/` & `/receptionist/book/` — `receptionist_walk_ins_view` & `receptionist_book_view`)
* **Template**: [templates/receptionist/booking.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/receptionist/booking.html)
* **4-Step Walk-in Intake Wizard (`#rec-booking-form`)**:
  * **Step 1: Locate Student Record**:
    * Search input (`#student_search_input`) with live AJAX search query against `/receptionist/search-students/`.
    * **"Search" Button (`#search_student_btn`)**: Queries students by name, ID number, or email.
    * Dynamic dropdown results list (`#student_search_results`).
    * Selection sets hidden input `#rec_student_id` and renders `#selected_student_badge` with student summary.
  * **Step 2: Assign Counselor (`#rec_counselor_select`)**:
    * Dropdown with `★ Next Available (Earliest Free Counselor)` or specific counselors.
  * **Step 3: Appointment Date & Time (`#rec_scheduled_at`)**:
    * `datetime-local` input picker (constrained to 09:00 AM – 04:00 PM slots).
  * **Step 4: Primary Concern Dropdown (`concern_type`)**:
    * Academic, Personal, Career, Crisis / Emergency.
  * **Intake Notes Textarea (`notes`)**:
    * Front desk intake observations or immediate student requests.
  * **"Confirm & Reserve Appointment" Submit Button**:
    * Validates slot, prevents duplicate booking, saves appointment as confirmed/pending, logs audit record, and refreshes desk queue.
* **Right Side: Today's Desk Schedule**:
  * Live feed of walk-in appointments booked today.

### 7.3 Receptionist Front Desk Live Queue (`/receptionist/front-desk/` — `receptionist_front_desk_view`)
* **Template**: [templates/receptionist/front_desk.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/receptionist/front_desk.html)
* Front desk queue monitor displaying arriving students and counselor room availability.

### 7.4 Receptionist Profile (`/receptionist/profile/` — `receptionist_profile_view`)
* **Template**: [templates/receptionist/profile.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/receptionist/profile.html)
* Front desk staff account details and password change form.

---

## 8. Administrator Panel

### 8.1 Executive Overview (`/admin-panel/` — `admin_overview_view`)
* **Template**: [templates/analytics/overview.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/analytics/overview.html)
* **4 Executive KPI Cards**:
  * **Total Active Students**: Count of enrolled student accounts (`kpis.total_students`).
  * **Licensed Counselors**: Count of active counselors on staff (`kpis.total_counselors`).
  * **Monthly Sessions**: Appointment count over the rolling 30-day window (`kpis.monthly_appointments`).
  * **Completion Rate**: Percentage of scheduled appointments successfully completed (`kpis.completion_rate`%) with visual progress bar.
* **Interactive Chart.js Visualizations**:
  * **Appointment Volume (Past 8 Weeks) (`#weeklyTrendChart`)**: Line/bar chart plotting weekly session trends.
  * **Concern Distribution (`#concernDonutChart`)**: Donut chart showing breakdown across Academic, Personal, Career, and Crisis categories.
* **Recent System Audit Activity Table**:
  * Columns: Timestamp, User Actor, Action Badge, Resource/Table Name, Record #.
  * **"View All Logs" Button**: Navigates directly to `/admin-panel/audit/`.

### 8.2 Reports & Compliance Exports (`/admin-panel/reports/` — `admin_reports_view`)
* **Template**: [templates/analytics/reports.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/analytics/reports.html)
* **Export Action Buttons**:
  * **"Export CSV" Button**: Generates and downloads filtered appointment data as a CSV file (`?export=csv`).
  * **"Export PDF Report" Button**: Generates and streams a formal compliance PDF report (`?export=pdf`).
* **Report Filter Criteria Card**:
  * **Start Date Input**: Beginning date range.
  * **End Date Input**: Ending date range.
  * **Counselor Dropdown**: Filter by specific counselor or all counselors.
  * **Concern Category Dropdown**: Filter by Academic, Personal, Career, Crisis, or all.
  * **Status Dropdown**: Filter by Pending, Confirmed, Completed, Cancelled, No-Show.
  * **"Generate Report Preview" Button**: Applies filters and reloads preview.
  * **"Reset Filters" Button**: Clears query parameters.
* **Summary Strip & Data Preview Table**:
  * Total matching count indicator.
  * Paginated preview table showing ID, Scheduled Date, Student, Counselor, Concern, and Status.

### 8.3 User Management (`/admin-panel/users/` — `admin_users_view`)
* **Template**: [templates/users/users.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/users/users.html)
* **Top Header Button**:
  * **"+ Add New User" Button**: Toggles the collapsible user creation form.
* **Add New User Card (`#add-user-card`)**:
  * Inputs: Full Name, Institutional Email, Temporary Password, Account Role (Student, Counselor, Receptionist, Admin), Student ID (optional), Department (optional).
  * **"Save & Activate Account" Button**: Creates user, profile, auto-increments `user_no`, and logs audit entry.
  * **"Cancel" Button**: Hides the creation form.
* **Search & Filter Bar**:
  * Text search input `q` (matches full name, student ID, or email).
  * Role dropdown filter (`role`).
  * Account status filter (`status`: All, Active Only, Deactivated Only).
  * **"Filter" Button** and **"Clear" Link**.
* **Users Directory Table**:
  * Columns: User (Full name & email), User #, Student ID, Department, Role Badge, Status (`Active` / `Inactive`).
  * **Change Role Inline Form**: Dropdown and button to reassign roles on the fly.
  * **Deactivate / Activate Button**: Toggles user account active state with confirmation and audit logging.

### 8.4 System Audit Logs (`/admin-panel/audit/` — `admin_audit_logs_view`)
* **Template**: [templates/audit/logs.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/audit/logs.html)
* **Header Button**:
  * **"Export CSV" Button**: Exports filtered audit trail to CSV (`?export=true`).
* **Filter Bar**:
  * Action search input (e.g. `APPOINTMENT_CREATED`, `LOGIN_SUCCESS`).
  * Table name input (e.g. `core_appointment`, `core_profile`).
  * **"Filter" Button** and **"Clear" Link**.
* **Audit Trail Table**:
  * Columns: ID, Timestamp, Actor (User name and role, or "System Anonymous"), Action Badge, Table Name, Record ID, Metadata.
  * **Metadata Detail Disclosure (`<details>`)**: Expandable JSON viewer showing request IP, changes, or extra payload data.
* **Pagination Controls**:
  * **"← Previous" Button**, Page indicator (`Page X of Y`), and **"Next →" Button**.

### 8.5 Appointments Registry (`/admin-panel/appointments/` — `admin_appointments_view`)
* **Template**: [templates/admin/appointments.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/admin/appointments.html)
* **Header Action Buttons**:
  * **"Dashboard" Button**: Links to `/admin-panel/`.
  * **"Export Reports" Button**: Links to `/admin-panel/reports/`.
* **Dynamic Filter Tabs (With Live Counts)**:
  * **All (`#tab-all`)**: Shows all records with count badge.
  * **Pending (`#tab-pending`)**: Amber tab showing pending requests.
  * **Confirmed (`#tab-confirmed`)**: Blue tab showing confirmed sessions.
  * **Completed (`#tab-completed`)**: Green tab showing finished consultations.
  * **Cancelled (`#tab-cancelled`)**: Red tab showing cancelled sessions.
* **Search & Counselor Filter Bar**:
  * Search input `q` (student name, counselor name, or appointment ID).
  * Counselor select dropdown.
  * **"Filter" Button** and **"Clear" Link**.
* **System-Wide Appointments Table**:
  * Columns: Appt ID, Scheduled At, Student (with avatar and student ID), Counselor, Concern Type, Status Badge, Override Action.
  * **Status Override Dropdown & Button**: Allows administrator to update any appointment status directly.

### 8.6 Administrator Profile (`/admin-panel/profile/` — `admin_profile_view`)
* **Template**: [templates/users/profile.html](file:///c:/School%20works/4yr_firstsem/connect%20guidancefinal/ConnectGuidance/templates/users/profile.html)
* Account summary card and administrative password change utility.

---

## 9. AI Guidance Assistant & Backend Streaming API

ConnectGuidance features an integrated AI guidance chatbot powered by **Groq (LLaMA 3.3 70B Versatile)** or **Anthropic Claude Haiku**, augmented with an anti-hallucination grounded knowledge base (`GuidanceKnowledgeBase`).

### 9.1 Chat Service Architecture (`core/services/chat.py`)
* **Streaming Protocol**: Server-Sent Events (SSE) streaming through `chat_stream_post_view` at `/chat/`.
* **Session Hydration**: Student session history fetched via `/chat/session/`.
* **Guardrails & Constraints**:
  * **Rate Limiting**: Enforces max 24 POST requests and 60 GET session requests per 15-minute rolling window per student.
  * **Payload Caps**: Max 36 messages in history, max 24,000 characters total.
  * **Crisis Intervention Protocol**: Automatically intercepts keywords (`suicide`, `self harm`, `want to die`, etc.) and immediately outputs crisis hotline guidance (988 Lifeline and Campus Security).
  * **Dynamic CTA Triggering**: Automatically prompts the student to book a human counseling appointment when booking keywords or distress are detected.
  * **Formal Plain-Text Response Formatting**: Enforces a formal counselor tone and completely strips raw markdown symbols (`*`, `**`, `###`, `---`, `|`) so responses render cleanly.

---

## 10. Data Models & Database Schema

All domain models are managed through Django ORM and enforce integrity constraints:

### 10.1 `Profile` (`accounts.models.Profile` / Table: `core_profile`)
* Extends standard `django.contrib.auth.models.User`.
* **Fields**:
  * `user`: OneToOneField to `User`.
  * `role`: String choice (`student`, `counselor`, `receptionist`, `admin`).
  * `full_name`: Full personal name.
  * `student_id`: University ID string (nullable for non-students).
  * `department`: College or department affiliation.
  * `is_active`: Boolean active status flag.
  * `user_no`: Monotonically increasing unique integer identifier.
  * `created_at`: Creation timestamp.

### 10.2 `Appointment` (`core.models.Appointment`)
* Represents scheduled sessions between students and counselors.
* **Fields**:
  * `student`: ForeignKey to `Profile` (role `student`).
  * `counselor`: ForeignKey to `Profile` (role `counselor`, protected from accidental deletion).
  * `scheduled_at`: DateTime of consultation.
  * `status`: Choice (`pending`, `confirmed`, `completed`, `cancelled`, `no_show`).
  * `concern_type`: Choice (`academic`, `personal`, `career`, `crisis`).
  * `notes`: Optional intake notes (max 2000 characters).
  * `created_at`: Creation timestamp.

### 10.3 `CaseNote` (`core.models.CaseNote`)
* Secure session documentation authored by counselors.
* **Fields**:
  * `appointment`: ForeignKey to `Appointment`.
  * `counselor`: ForeignKey to `Profile` (must match appointment's counselor).
  * `content`: Encrypted ciphertext payload (AES-256 Fernet).
  * `is_confidential`: Boolean flag. If `True`, viewable only by author counselor.
  * `created_at`, `updated_at`: Timestamps.
  * **Constraint**: `uniq_case_note_appt_counselor` guarantees one note per appointment per counselor.

### 10.4 `StudentMoodAlert` (`core.models.StudentMoodAlert`)
* Dispatched when a student registers a "low" mood during daily wellness check-ins.
* **Fields**:
  * `student`: ForeignKey to student `Profile`.
  * `counselor`: ForeignKey to assigned counselor `Profile`.
  * `note`: Optional student reflection note (max 500 characters).
  * `created_at`: Alert timestamp.

### 10.5 `AuditLog` (`core.models.AuditLog`)
* Append-only security and operational audit log.
* **Fields**:
  * `user`: ForeignKey to actor `Profile` (null for anonymous/system).
  * `action`: Action string (e.g. `LOGIN_SUCCESS`, `APPOINTMENT_CREATED`, `CASE_NOTE_ENCRYPTED`).
  * `table_name`: Target database table.
  * `record_id`: UUID or record identifier.
  * `metadata`: JSONField containing contextual metadata (IP, changes, counts).
  * `created_at`: Immutable timestamp.

### 10.6 `ChatbotSession` (`core.models.ChatbotSession`)
* Persisted conversation history for student AI chats.
* **Fields**:
  * `student`: ForeignKey to `Profile`.
  * `messages`: JSONField array of `{role: "user"|"assistant", content: "..."}` (max 36 entries).
  * `created_at`: Session timestamp.

---

## 11. Complete URL Routing Reference

| URL Path | View Function | URL Name | Allowed Roles | Method | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | `landing_view` | `landing` | Public | GET | Marketing & info landing page |
| `/home/` | `role_home_view` | `role_home` | Authenticated | GET | Redirects user to their role's home view |
| `/login/` | `login_view` | `login` | Public | GET, POST | User authentication |
| `/register/` | `register_view` | `register` | Public | GET, POST | Student self-registration |
| `/logout/` | `logout_view` | `logout` | Authenticated | GET, POST | Ends session |
| `/password-change/`| `password_change_view` | `password_change` | Authenticated | GET, POST | Changes password |
| **Student** | | | | | |
| `/student/` | `student_dashboard_view` | `student_dashboard`| `student` | GET | Main student wellness hub |
| `/student/mood/` | `student_mood_checkin_view`| `student_mood_checkin`| `student`| POST | Submits daily mood check-in |
| `/student/profile/`| `student_profile_view` | `student_profile` | `student` | GET, POST | Student profile & password |
| `/student/front-desk/`| `student_front_desk_view`| `student_front_desk`| `student` | GET | Physical front desk info |
| `/appointments/` | `student_appointments_list_view`| `student_appointments`| `student`| GET | Student appointments schedule |
| `/appointments/slots/`| `student_slots_view` | `student_slots` | `student`, `receptionist`| GET | AJAX available time slots |
| `/appointments/book/`| `student_book_appointment_view`| `student_book_appointment`| `student`| GET, POST | Student booking wizard |
| `/appointments/<id>/cancel/`| `student_cancel_appointment_view`| `student_cancel_appointment`| `student`| POST | Student cancels appointment |
| `/chatbot/` | `student_chatbot_page_view`| `student_chatbot` | `student` | GET | Full-page AI counselor |
| `/chat/session/` | `chat_session_get_view` | `chat_session_get` | `student` | GET | Hydrates previous chat session |
| `/chat/` | `chat_stream_post_view` | `chat_stream_post` | `student` | POST | SSE streaming chat endpoint |
| **Counselor** | | | | | |
| `/counselor/` | `counselor_workspace_view` | `counselor_workspace`| `counselor` | GET | Clinical workspace hub |
| `/counselor/appointments/`| `counselor_appointments_view`| `counselor_appointments`| `counselor`| GET | Counselor appointments manager |
| `/counselor/case-notes/`| `counselor_case_notes_list_view`| `counselor_case_notes`| `counselor`| GET | Directory of authored case notes |
| `/counselor/case-notes/<id>/`| `counselor_case_note_view`| `counselor_case_note`| `counselor`| GET, POST | AES-256 encrypted note editor |
| `/case-notes/<id>/` | `counselor_case_note_view` | `case_note` | `counselor` | GET, POST | Alias for case note editor |
| `/counselor/wellness/`| `counselor_wellness_view`| `counselor_wellness`| `counselor`| GET | Student alerts & wellness monitor |
| `/counselor/profile/`| `counselor_profile_view` | `counselor_profile` | `counselor` | GET, POST | Counselor profile |
| `/counselor/appointments/<id>/status/`| `counselor_status_update_view`| `counselor_status_update`| `counselor`| POST | Updates appointment status |
| **Receptionist** | | | | | |
| `/receptionist/dashboard/`| `receptionist_dashboard_view`| `receptionist_dashboard`| `receptionist`| GET | Front desk intake dashboard |
| `/receptionist/` | `receptionist_walk_ins_view`| `receptionist_walk_ins`| `receptionist`| GET | Walk-in intake desk |
| `/receptionist/front-desk/`| `receptionist_front_desk_view`| `receptionist_front_desk`| `receptionist`| GET | Live desk queue |
| `/receptionist/profile/`| `receptionist_profile_view`| `receptionist_profile`| `receptionist`| GET, POST | Receptionist profile |
| `/receptionist/search-students/`| `receptionist_search_students_view`| `receptionist_search_students`| `receptionist`| GET | AJAX student search |
| `/receptionist/book/` | `receptionist_book_view` | `receptionist_book` | `receptionist`| POST | Submits walk-in reservation |
| **Administrator** | | | | | |
| `/admin-panel/` | `admin_overview_view` | `admin_overview` | `admin` | GET | Executive KPI dashboard & charts |
| `/admin-panel/reports/`| `admin_reports_view` | `admin_reports` | `admin` | GET | Filterable preview & CSV/PDF export |
| `/admin-panel/users/` | `admin_users_view` | `admin_users` | `admin` | GET, POST | User directory, creation, roles |
| `/admin-panel/audit/` | `admin_audit_logs_view` | `admin_audit` | `admin` | GET | Immutable audit log viewer & CSV |
| `/admin-panel/appointments/`| `admin_appointments_view`| `admin_appointments`| `admin`| GET, POST | All appointments registry & override |
| `/admin-panel/profile/`| `admin_profile_view` | `admin_profile` | `admin` | GET, POST | Admin profile & password change |
