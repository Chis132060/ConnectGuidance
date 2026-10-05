from accounts.views import (
    landing_view,
    login_view,
    register_view,
    logout_view,
    password_change_view,
    role_home_view,
)
from .student import (
    student_dashboard_view,
    student_appointments_list_view,
    student_slots_view,
    student_book_appointment_view,
    student_cancel_appointment_view,
    student_mood_checkin_view,
    student_profile_view,
    student_front_desk_view,
)
from .counselor import (
    counselor_workspace_view,
    counselor_appointments_view,
    counselor_case_notes_list_view,
    counselor_case_note_view,
    counselor_wellness_view,
    counselor_profile_view,
    counselor_status_update_view,
)
from .receptionist import (
    receptionist_dashboard_view,
    receptionist_walk_ins_view,
    receptionist_front_desk_view,
    receptionist_profile_view,
    receptionist_search_students_view,
    receptionist_book_view,
)
from .admin import (
    admin_overview_view,
    admin_reports_view,
    admin_users_view,
    admin_audit_logs_view,
    admin_appointments_view,
    admin_profile_view,
)
from .chat import (
    student_chatbot_page_view,
    chat_session_get_view,
    chat_stream_post_view,
)
