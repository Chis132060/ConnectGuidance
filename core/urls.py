"""
core/urls.py — Application URL routing for GuidanceConnect Django replica.

Organized by domain/phase:
- Auth & Public (Phase 3)
- Student Appointments, Dashboard, Profile & Front Desk (Phases 4, 6, 7)
- Counselor Workspace & Case Notes (Phases 4 & 5)
- Receptionist Desk & Walk-in Booking (Phase 4)
- AI Chatbot (Phase 6)
- Administrator Overview, Users, Audit, Reports & Profile (Phases 7 & 8)
"""

from django.urls import path

# Phase 3: Auth & Public
from core.views.auth import (
    landing_view,
    login_view,
    logout_view,
    register_view,
    password_change_view,
    role_home_view,
)

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
    counselor_status_update_view,
    counselor_case_note_view,
)

# Phase 4: Receptionist Desk
from core.views.receptionist import (
    receptionist_dashboard_view,
    receptionist_search_students_view,
    receptionist_book_view,
)

# Phase 6: AI Chatbot
from core.views.chat import (
    student_chatbot_page_view,
    chat_session_get_view,
    chat_stream_post_view,
)

# Phase 7 & 8: Administrator Views
from core.views.admin_views import (
    admin_overview_view,
    admin_users_view,
    admin_audit_logs_view,
    admin_reports_view,
    admin_profile_view,
)

urlpatterns = [
    # --- Phase 3: Auth + Public ---
    path('', landing_view, name='landing'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('password_change/', password_change_view, name='password_change'),
    path('role-home/', role_home_view, name='role_home'),

    # --- Student Views (16 screens checklist #4, #5, #6, #7, #8) ---
    path('student/', student_dashboard_view, name='student_dashboard'),
    path('student/mood/', student_mood_checkin_view, name='student_mood_checkin'),
    path('student/profile/', student_profile_view, name='student_profile'),
    path('student/front-desk/', student_front_desk_view, name='student_front_desk'),
    path('appointments/', student_appointments_list_view, name='student_appointments'),
    path('appointments/slots/', student_slots_view, name='student_slots'),
    path('appointments/book/', student_book_appointment_view, name='student_book_appointment'),
    path('appointments/<int:pk>/cancel/', student_cancel_appointment_view, name='student_cancel_appointment'),
    path('chatbot/', student_chatbot_page_view, name='student_chatbot'),

    # --- Counselor Views (16 screens checklist #9, #10) ---
    path('counselor/', counselor_workspace_view, name='counselor_workspace'),
    path('counselor/appointments/<int:pk>/status/', counselor_status_update_view, name='counselor_status_update'),
    path('counselor/case-notes/<int:appointment_id>/', counselor_case_note_view, name='case_note'),

    # --- Receptionist Views (16 screens checklist #16) ---
    path('receptionist/', receptionist_dashboard_view, name='receptionist_dashboard'),
    path('receptionist/search-students/', receptionist_search_students_view, name='receptionist_search_students'),
    path('receptionist/book/', receptionist_book_view, name='receptionist_book'),

    # --- AI Chatbot Endpoints ---
    path('chat/session/', chat_session_get_view, name='chat_session_get'),
    path('chat/', chat_stream_post_view, name='chat_stream_post'),

    # --- Administrator Views (16 screens checklist #11, #12, #13, #14, #15) ---
    path('admin-panel/', admin_overview_view, name='admin_overview'),
    path('admin-panel/users/', admin_users_view, name='admin_users'),
    path('admin-panel/audit/', admin_audit_logs_view, name='admin_audit'),
    path('admin-panel/reports/', admin_reports_view, name='admin_reports'),
    path('admin-panel/profile/', admin_profile_view, name='admin_profile'),
]
