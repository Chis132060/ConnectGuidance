"""
core/urls.py — Guidance System & Business Module URL Routing
"""

from django.urls import path

# Core Domain Views
from core.views import (
    # Student Views
    student_dashboard_view,
    student_appointments_list_view,
    student_slots_view,
    student_book_appointment_view,
    student_cancel_appointment_view,
    student_mood_checkin_view,
    student_profile_view,
    student_front_desk_view,
    # Counselor Views
    counselor_workspace_view,
    counselor_appointments_view,
    counselor_case_notes_list_view,
    counselor_case_note_view,
    counselor_wellness_view,
    counselor_profile_view,
    counselor_status_update_view,
    # Receptionist Views
    receptionist_dashboard_view,
    receptionist_walk_ins_view,
    receptionist_front_desk_view,
    receptionist_profile_view,
    receptionist_search_students_view,
    receptionist_book_view,
    # Admin Portal Views
    admin_overview_view,
    admin_reports_view,
    admin_users_view,
    admin_audit_logs_view,
    admin_appointments_view,
    admin_profile_view,
    # AI Chatbot Endpoints
    student_chatbot_page_view,
    chat_session_get_view,
    chat_stream_post_view,
)

urlpatterns = [
    # ── Student Portal ────────────────────────────────────────────────────
    path('student/', student_dashboard_view, name='student_dashboard'),
    path('student/mood/', student_mood_checkin_view, name='student_mood_checkin'),
    path('student/profile/', student_profile_view, name='student_profile'),
    path('student/front-desk/', student_front_desk_view, name='student_front_desk'),
    path('appointments/', student_appointments_list_view, name='student_appointments'),
    path('appointments/slots/', student_slots_view, name='student_slots'),
    path('appointments/book/', student_book_appointment_view, name='student_book_appointment'),
    path('appointments/<int:pk>/cancel/', student_cancel_appointment_view, name='student_cancel_appointment'),
    path('chatbot/', student_chatbot_page_view, name='student_chatbot'),

    # ── Counselor Workspace ───────────────────────────────────────────────
    path('counselor/', counselor_workspace_view, name='counselor_workspace'),
    path('counselor/appointments/', counselor_appointments_view, name='counselor_appointments'),
    path('counselor/case-notes/', counselor_case_notes_list_view, name='counselor_case_notes'),
    path('counselor/case-notes/<int:appointment_id>/', counselor_case_note_view, name='counselor_case_note'),
    path('case-notes/<int:appointment_id>/', counselor_case_note_view, name='case_note'),
    path('counselor/wellness/', counselor_wellness_view, name='counselor_wellness'),
    path('counselor/profile/', counselor_profile_view, name='counselor_profile'),
    path('counselor/appointments/<int:pk>/status/', counselor_status_update_view, name='counselor_status_update'),

    # ── Receptionist Desk ─────────────────────────────────────────────────
    path('receptionist/', receptionist_walk_ins_view, name='receptionist_walk_ins'),
    path('receptionist/dashboard/', receptionist_dashboard_view, name='receptionist_dashboard'),
    path('receptionist/front-desk/', receptionist_front_desk_view, name='receptionist_front_desk'),
    path('receptionist/profile/', receptionist_profile_view, name='receptionist_profile'),
    path('receptionist/search-students/', receptionist_search_students_view, name='receptionist_search_students'),
    path('receptionist/book/', receptionist_book_view, name='receptionist_book'),

    # ── Administrator Panel ───────────────────────────────────────────────
    path('admin-panel/', admin_overview_view, name='admin_overview'),
    path('admin-panel/reports/', admin_reports_view, name='admin_reports'),
    path('admin-panel/users/', admin_users_view, name='admin_users'),
    path('admin-panel/audit/', admin_audit_logs_view, name='admin_audit'),
    path('admin-panel/appointments/', admin_appointments_view, name='admin_appointments'),
    path('admin-panel/profile/', admin_profile_view, name='admin_profile'),

    # ── AI Chatbot API Endpoints ──────────────────────────────────────────
    path('chat/session/', chat_session_get_view, name='chat_session_get'),
    path('chat/', chat_stream_post_view, name='chat_stream_post'),
]
