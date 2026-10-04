from .auth import landing_view, login_view, register_view, logout_view, password_change_view
from .student import (
    dashboard_view as student_dashboard_view,
    appointments_view as student_appointments_view,
    get_slots_api as student_get_slots_api,
    profile_view as student_profile_view,
    front_desk_view as student_front_desk_view,
    chatbot_page_view as student_chatbot_page_view,
    mood_checkin_view as student_mood_checkin_view,
    cancel_appointment_view as student_cancel_appointment_view,
)
from .counselor import (
    workspace_view as counselor_workspace_view,
    case_note_view as counselor_case_note_view,
    appointments_view as counselor_appointments_view,
    case_notes_list_view as counselor_case_notes_list_view,
    wellness_view as counselor_wellness_view,
    profile_view as counselor_profile_view,
)
from .receptionist import (
    dashboard_view as receptionist_dashboard_view,
    booking_view as receptionist_booking_view,
    front_desk_view as receptionist_front_desk_view,
    profile_view as receptionist_profile_view,
    receptionist_slots_api,
)
from .admin_views import (
    overview_view as admin_overview_view,
    users_view as admin_users_view,
    audit_logs_view as admin_audit_logs_view,
    reports_view as admin_reports_view,
    admin_profile_view,
)
from .chat import (
    chat_session_view,
    chat_stream_view,
    has_llm_api_key,
)
