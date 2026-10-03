"""
core/urls.py — Application URL routing for GuidanceConnect Django replica.

Organized by domain/phase:
- Student: Dashboard, Appointments, AI Assistant, Front Desk, Profile (Phases 4, 6, 7)
- Counselor: Dashboard, Appointments, Case Notes, Wellness, Profile (Phases 4 & 5)
- Receptionist: Dashboard, Appointments/Walk-ins, Front Desk, Profile (Phase 4)
- Admin: Dashboard, Analytics & Reports, User Management, Audit Logs, Appointments, Profile (Phases 7 & 8)
- AI Chatbot (Phase 6)

Note: Auth & Public routes → apps.authentication.urls
      Analytics, Users, Audit → their respective app urls files
"""

from django.urls import path

# Phase 4, 6, 7: Student Views
from core.views.student import (
    student_dashboard_view,
    student_appointments_list_view,
    student_slots_view,
    student_book_appointment_view,
    student_cancel_appointment_view,
    student_mood_checkin_view,
    student_profile_view,
    student_front_desk_view,
)

# Phase 4 & 5: Counselor Views
from core.views.counselor import (
    counselor_workspace_view,
    counselor_appointments_view,
    counselor_case_notes_list_view,
    counselor_wellness_view,
    counselor_profile_view,
    counselor_status_update_view,
)

# Phase 4: Receptionist Views
from core.views.receptionist import (
    receptionist_dashboard_view,
    receptionist_walk_ins_view,
    receptionist_front_desk_view,
    receptionist_profile_view,
    receptionist_search_students_view,
    receptionist_book_view,
)

# Phase 6: AI Chatbot
from core.views.chat import (
    student_chatbot_page_view,
    chat_session_get_view,
    chat_stream_post_view,
)

# Phase 7 & 8: Admin views (appointments)
from core.views.admin import admin_appointments_view

urlpatterns = [
    # ── Student (Dashboard, Appointments, AI Assistant, Front Desk, Profile) ──
    path('student/', student_dashboard_view, name='student_dashboard'),
    path('student/mood/', student_mood_checkin_view, name='student_mood_checkin'),
    path('student/profile/', student_profile_view, name='student_profile'),
    path('student/front-desk/', student_front_desk_view, name='student_front_desk'),
    path('appointments/', student_appointments_list_view, name='student_appointments'),
    path('appointments/slots/', student_slots_view, name='student_slots'),
    path('appointments/book/', student_book_appointment_view, name='student_book_appointment'),
    path('appointments/<int:pk>/cancel/', student_cancel_appointment_view, name='student_cancel_appointment'),
    path('chatbot/', student_chatbot_page_view, name='student_chatbot'),

    # ── Counselor (Dashboard, Appointments, Case Notes, Wellness, Profile) ───
    path('counselor/', counselor_workspace_view, name='counselor_workspace'),
    path('counselor/appointments/', counselor_appointments_view, name='counselor_appointments'),
    path('counselor/case-notes/', counselor_case_notes_list_view, name='counselor_case_notes'),
    path('counselor/wellness/', counselor_wellness_view, name='counselor_wellness'),
    path('counselor/profile/', counselor_profile_view, name='counselor_profile'),
    path('counselor/appointments/<int:pk>/status/', counselor_status_update_view, name='counselor_status_update'),

    # ── Receptionist (Dashboard, Walk-ins, Front Desk, Profile) ─────────────
    path('receptionist/', receptionist_dashboard_view, name='receptionist_dashboard'),
    path('receptionist/walk-ins/', receptionist_walk_ins_view, name='receptionist_walk_ins'),
    path('receptionist/front-desk/', receptionist_front_desk_view, name='receptionist_front_desk'),
    path('receptionist/profile/', receptionist_profile_view, name='receptionist_profile'),
    path('receptionist/search-students/', receptionist_search_students_view, name='receptionist_search_students'),
    path('receptionist/book/', receptionist_book_view, name='receptionist_book'),

    # ── Admin Appointments (supplemental, under core) ─────────────────────
    path('admin-panel/appointments/', admin_appointments_view, name='admin_appointments'),

    # ── AI Chatbot Endpoints ────────────────────────────────────────────────
    path('chat/session/', chat_session_get_view, name='chat_session_get'),
    path('chat/', chat_stream_post_view, name='chat_stream_post'),
]
