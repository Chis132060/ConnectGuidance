"""
Core Application URL Configuration.
Maps all public, student, counselor, receptionist, and administrator routes and API endpoints.
"""
from django.urls import path
from core.views import auth, student, counselor, admin_views, receptionist, chat

urlpatterns = [
    # Public & Authentication
    path("", auth.landing_view, name="landing"),
    path("home/", auth.landing_view, name="role_home"),
    path("login/", auth.login_view, name="login"),
    path("register/", auth.register_view, name="register"),
    path("logout/", auth.logout_view, name="logout"),
    path("password-change/", auth.password_change_view, name="password_change"),

    # Student Portal
    path("student/", student.dashboard_view, name="student_dashboard"),
    path("appointments/", student.appointments_view, name="appointments"),
    path("appointments/registry/", student.appointments_view, name="student_appointments"),
    path("appointments/book/", student.appointments_view, name="student_book_appointment"),
    path("student/profile/", student.profile_view, name="student_profile"),
    path("student/front-desk/", student.front_desk_view, name="front_desk"),
    path("student/info/", student.front_desk_view, name="student_front_desk"),
    path("chatbot/", student.chatbot_page_view, name="chatbot"),
    path("student/chat/", student.chatbot_page_view, name="student_chatbot"),
    path("student/mood/", student.mood_checkin_view, name="mood_checkin"),
    path("student/mood/check-in/", student.mood_checkin_view, name="student_mood_checkin"),
    path("appointments/cancel/<int:appointment_id>/", student.cancel_appointment_view, name="student_cancel_appointment"),
    path("api/slots/", student.get_slots_api, name="api_slots"),

    # Counselor Portal
    path("counselor/", counselor.workspace_view, name="counselor_workspace"),
    path("counselor/appointments/", counselor.appointments_view, name="counselor_appointments"),
    path("counselor/case-notes/", counselor.case_notes_list_view, name="counselor_case_notes"),
    path("counselor/case-notes/<int:appointment_id>/", counselor.case_note_view, name="case_note"),
    path("counselor/wellness/", counselor.wellness_view, name="counselor_wellness"),
    path("counselor/profile/", counselor.profile_view, name="counselor_profile"),

    # Receptionist Desk
    path("receptionist/", receptionist.booking_view, name="receptionist_booking"),
    path("receptionist/book/", receptionist.booking_view, name="receptionist_book"),
    path("receptionist/walk-ins/", receptionist.booking_view, name="receptionist_walk_ins"),
    path("receptionist/dashboard/", receptionist.dashboard_view, name="receptionist_dashboard"),
    path("receptionist/front-desk/", receptionist.front_desk_view, name="receptionist_front_desk"),
    path("receptionist/profile/", receptionist.profile_view, name="receptionist_profile"),
    path("api/receptionist/slots/", receptionist.receptionist_slots_api, name="receptionist_slots_api"),

    # Admin Panel
    path("admin-panel/", admin_views.overview_view, name="admin_overview"),
    path("admin-panel/users/", admin_views.users_view, name="admin_users"),
    path("admin-panel/audit/", admin_views.audit_logs_view, name="admin_audit"),
    path("admin-panel/reports/", admin_views.reports_view, name="admin_reports"),
    path("admin-panel/appointments/", admin_views.reports_view, name="admin_appointments"),
    path("admin-panel/profile/", admin_views.admin_profile_view, name="admin_profile"),

    # Chatbot API Endpoints
    path("api/chat/session/", chat.chat_session_view, name="chat_session"),
    path("api/chat/stream/", chat.chat_stream_view, name="chat_stream"),
    path("chat/", chat.chat_stream_view, name="chat_stream_post"),
    path("chat/session/", chat.chat_session_view, name="chat_session_get"),
]
