"""
ConnectGuidance — Core Views Module.
Organized monolithic view controllers covering all system flows:
1. Public & Authentication Views
2. Student Portal Views
3. Counselor Workspace Views
4. Receptionist / Front Desk Views
5. Administrator Analytics & Audit Views
6. AI Wellness Chatbot Endpoints
"""
import io
import json
from datetime import datetime, timedelta, date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from core.models import Profile, Appointment, CaseNote, AuditLog, StudentMoodAlert, ChatbotSession
from core.choices import (
    ROLE_CHOICES,
    STATUS_CHOICES,
    CONCERN_CHOICES,
    ROLE_HOME,
    RoleChoices,
    AppointmentStatusChoices,
)
from core.guards import role_required, get_profile_or_none
from core.services.appointments import (
    book_appointment,
    cancel_appointment_student,
    update_appointment_status,
)
from core.services.slots import get_available_slots
from core.services.mood import process_mood_checkin
from core.services.case_notes import save_case_note, get_case_note_decrypted
from core.services.encryption import decrypt
from core.services.receptionist import (
    search_students,
    list_counselors,
    find_next_available,
    book_for_student,
)
from core.services.metrics import (
    get_kpis,
    get_weekly_series,
    get_concern_breakdown,
    get_recent_activity,
)
from core.services.admin_users import (
    create_user,
    change_role,
    toggle_active,
)
from core.services.reports import (
    generate_report,
    export_csv,
    export_pdf,
)
from core.services.audit import log_action
from core.services.chat import (
    check_chat_rate_limit,
    check_session_get_rate_limit,
    get_session,
    stream_chat,
)


# ==============================================================================
# 1. PUBLIC & AUTHENTICATION VIEWS
# ==============================================================================

def landing_view(request):
    """Public landing page with university guidance information and portal links."""
    if request.user.is_authenticated:
        profile = get_profile_or_none(request.user)
        if profile and profile.is_active:
            return redirect(ROLE_HOME.get(profile.role, "/"))
    return render(request, "common/landing.html")


def login_view(request):
    """User authentication view handling login forms and role-based redirects."""
    if request.user.is_authenticated:
        profile = get_profile_or_none(request.user)
        if profile and profile.is_active:
            return redirect(ROLE_HOME.get(profile.role, "/"))

    error = request.GET.get("error", "")
    next_url = request.GET.get("next", "")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        # Authenticate against Django User model
        user = authenticate(request, username=email, password=password)
        if user is None:
            try:
                u = User.objects.get(email=email)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass

        if user is None:
            return render(request, "authentication/login.html", {
                "error": "Invalid email or password.",
                "email": email,
            })

        profile = get_profile_or_none(user)
        if not profile:
            return render(request, "authentication/login.html", {
                "error": "Account profile not found. Please contact guidance office.",
                "email": email,
            })

        if not profile.is_active:
            return redirect("/login/?error=deactivated")

        login(request, user)
        if next_url:
            return redirect(next_url)
        return redirect(ROLE_HOME.get(profile.role, "/"))

    context = {"error": "", "email": ""}
    if error == "deactivated":
        context["error"] = "Your account has been deactivated. Please contact an administrator."
    elif error == "no_profile":
        context["error"] = "Account profile not found. Please contact guidance office."

    return render(request, "authentication/login.html", context)


def register_view(request):
    """Student self-registration view with validation."""
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        student_id = request.POST.get("student_id", "").strip()
        email = request.POST.get("email", "").strip()
        department = request.POST.get("department", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        errors = {}
        if not full_name:
            errors["full_name"] = "Full name is required."
        if not email:
            errors["email"] = "Email is required."
        if not password or len(password) < 8:
            errors["password"] = "Password must be at least 8 characters."
        if password != confirm:
            errors["confirm_password"] = "Passwords do not match."
        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            errors["email"] = "An account with this email already exists."

        if errors:
            return render(request, "authentication/register.html", {
                "errors": errors,
                "form_data": request.POST,
            })

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name.split()[0] if full_name else "",
            last_name=" ".join(full_name.split()[1:]) if " " in full_name else "",
        )

        profile = user.profile
        profile.full_name = full_name
        profile.student_id = student_id or None
        profile.department = department or None
        profile.save()

        messages.success(request, "Registration successful! You may now sign in.")
        return redirect("login")

    return render(request, "authentication/register.html")


def logout_view(request):
    """End session and redirect to landing screen."""
    logout(request)
    return redirect("/")


@login_required
def password_change_view(request):
    """User password change view."""
    profile = get_profile_or_none(request.user)
    if not profile:
        logout(request)
        return redirect("/login/?error=no_profile")

    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect(ROLE_HOME.get(profile.role, "/"))
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "registration/password_change.html", {
        "form": form,
        "profile": profile,
    })


# ==============================================================================
# 2. STUDENT PORTAL VIEWS
# ==============================================================================

@role_required("student")
def student_dashboard_view(request):
    """Student portal dashboard with upcoming schedule and wellness mood widget."""
    profile = request.profile

    upcoming = Appointment.objects.filter(
        student=profile,
        status__in=["pending", "confirmed"],
        scheduled_at__gte=timezone.now(),
    ).select_related("counselor").order_by("scheduled_at")[:5]

    history = Appointment.objects.filter(
        student=profile,
    ).exclude(
        status__in=["pending", "confirmed"],
    ).select_related("counselor").order_by("-scheduled_at")[:10]

    case_notes = CaseNote.objects.filter(
        appointment__student=profile,
        is_confidential=False,
    ).select_related("appointment", "counselor").order_by("-created_at")[:5]

    notes_data = []
    for note in case_notes:
        try:
            plain = decrypt(note.content)
            notes_data.append({
                "note": note,
                "preview": plain[:200] + "..." if len(plain) > 200 else plain,
            })
        except Exception:
            notes_data.append({"note": note, "preview": "[Confidential]"})

    return render(request, "student/dashboard.html", {
        "profile": profile,
        "upcoming": upcoming,
        "history": history,
        "case_notes": notes_data,
    })


@role_required("student")
def student_appointments_view(request):
    """Student appointment booking form and history tables."""
    profile = request.profile

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "book":
            counselor_id = request.POST.get("counselor_id")
            date_str = request.POST.get("scheduled_date")
            time_str = request.POST.get("scheduled_time")
            concern = request.POST.get("concern_type", "other")
            notes = request.POST.get("notes", "")

            try:
                scheduled_dt = timezone.make_aware(
                    datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"),
                    timezone.get_current_timezone(),
                )
            except (ValueError, TypeError):
                messages.error(request, "Invalid date or time format.")
                return redirect("/appointments/")

            try:
                book_appointment(
                    student=profile,
                    counselor=counselor_id,
                    scheduled_at=scheduled_dt,
                    concern_type=concern,
                    notes=notes,
                )
                messages.success(request, "Appointment booked successfully!")
            except Exception as e:
                msg = getattr(e, "message", str(e))
                messages.error(request, msg)
            return redirect("/appointments/")

        elif action == "cancel":
            appt_id = request.POST.get("appointment_id")
            try:
                cancel_appointment_student(appt_id, profile)
                messages.success(request, "Appointment cancelled.")
            except Exception as e:
                msg = getattr(e, "message", str(e))
                messages.error(request, msg)
            return redirect("/appointments/")

    counselors = Profile.objects.filter(role="counselor", is_active=True).order_by("full_name")
    upcoming = Appointment.objects.filter(
        student=profile,
        status__in=["pending", "confirmed"],
    ).select_related("counselor").order_by("scheduled_at")
    past = Appointment.objects.filter(
        student=profile,
    ).exclude(
        status__in=["pending", "confirmed"],
    ).select_related("counselor").order_by("-scheduled_at")

    return render(request, "student/appointments.html", {
        "profile": profile,
        "counselors": counselors,
        "upcoming": upcoming,
        "past": past,
    })


@role_required("student")
def student_get_slots_api(request):
    """JSON API returning available hourly slots for a chosen counselor and date."""
    counselor_id = request.GET.get("counselor_id")
    date_str = request.GET.get("date")

    if not counselor_id or not date_str:
        return JsonResponse({"slots": []})

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"slots": []})

    slots = get_available_slots(counselor_id, date_obj)
    return JsonResponse({
        "slots": [
            {"value": s.strftime("%H:%M"), "label": s.strftime("%I:%M %p")}
            for s in slots
        ]
    })


@role_required("student")
def student_profile_view(request):
    """Student profile information."""
    return render(request, "student/profile.html", {
        "profile": request.profile,
    })


@role_required("student")
def student_front_desk_view(request):
    """Guidance office front desk hours and walk-in consultation guidelines."""
    return render(request, "student/front_desk.html", {
        "profile": request.profile,
    })


@role_required("student")
def student_chatbot_page_view(request):
    """Student wellness chatbot interface."""
    return render(request, "student/chatbot.html", {
        "profile": request.profile,
    })


@role_required("student")
def student_mood_checkin_view(request):
    """Process student wellness mood submission."""
    if request.method != "POST":
        return redirect("/student/")

    mood = request.POST.get("mood", "").lower()
    note = request.POST.get("note", "")

    result = process_mood_checkin(request.profile, mood, note)
    if result.get("ok"):
        if result.get("notified"):
            messages.success(
                request,
                f"Your check-in was logged. Your counselor {result.get('counselor_name', '')} has been alerted."
            )
        else:
            messages.success(request, "Thank you for completing your wellness check-in!")
    else:
        messages.error(request, result.get("error", "Could not process check-in."))

    return redirect("/student/")


@role_required("student")
def student_cancel_appointment_view(request, appointment_id):
    """Endpoint for direct appointment cancellation."""
    if request.method == "POST":
        try:
            cancel_appointment_student(appointment_id, request.profile)
            messages.success(request, "Appointment cancelled.")
        except Exception as e:
            msg = getattr(e, "message", str(e))
            messages.error(request, msg)
    return redirect(request.META.get("HTTP_REFERER", "/appointments/"))


# ==============================================================================
# 3. COUNSELOR WORKSPACE VIEWS
# ==============================================================================

@role_required("counselor")
def counselor_workspace_view(request):
    """Counselor daily workspace dashboard, queue stats, and upcoming schedule."""
    profile = request.profile
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    if request.method == "POST":
        action = request.POST.get("action")
        appt_id = request.POST.get("appointment_id")

        if action in ("confirmed", "cancelled", "completed"):
            try:
                update_appointment_status(appt_id, action, profile)
                messages.success(request, f"Appointment status changed to {action}.")
            except Exception as e:
                msg = getattr(e, "message", str(e))
                messages.error(request, msg)
        return redirect("/counselor/")

    today_count = Appointment.objects.filter(
        counselor=profile,
        scheduled_at__gte=today_start,
        scheduled_at__lt=today_end,
    ).count()

    upcoming_count = Appointment.objects.filter(
        counselor=profile,
        status__in=["pending", "confirmed"],
        scheduled_at__gte=now,
    ).count()

    past_count = Appointment.objects.filter(
        counselor=profile,
        status__in=["completed", "cancelled"],
    ).count()

    mood_alerts = StudentMoodAlert.objects.filter(
        counselor=profile,
    ).select_related("student").order_by("-created_at")[:10]

    today_sessions = Appointment.objects.filter(
        counselor=profile,
        scheduled_at__gte=today_start,
        scheduled_at__lt=today_end,
    ).select_related("student").order_by("scheduled_at")

    upcoming = Appointment.objects.filter(
        counselor=profile,
        status__in=["pending", "confirmed"],
        scheduled_at__gte=now,
    ).exclude(
        scheduled_at__gte=today_start,
        scheduled_at__lt=today_end,
    ).select_related("student").order_by("scheduled_at")[:20]

    past = Appointment.objects.filter(
        counselor=profile,
        status__in=["completed", "cancelled"],
    ).select_related("student").order_by("-scheduled_at")[:20]

    return render(request, "counselor/workspace.html", {
        "profile": profile,
        "today_count": today_count,
        "upcoming_count": upcoming_count,
        "past_count": past_count,
        "mood_alerts": mood_alerts,
        "today_sessions": today_sessions,
        "upcoming": upcoming,
        "past": past,
    })


@role_required("counselor")
def counselor_case_note_view(request, appointment_id):
    """Counselor clinical case note editor with AES-256 encryption."""
    profile = request.profile
    appointment = get_object_or_404(
        Appointment.objects.select_related("student", "counselor"),
        pk=appointment_id,
        counselor=profile,
    )

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        is_confidential = request.POST.get("is_confidential") == "on"

        if not content:
            messages.error(request, "Note content cannot be empty.")
            return redirect(f"/counselor/case-notes/{appointment_id}/")

        note, error = save_case_note(profile, appointment_id, content, is_confidential)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Encrypted case note saved successfully.")
        return redirect(f"/counselor/case-notes/{appointment_id}/")

    plaintext = ""
    existing_note = None
    plaintext_data, note_obj, error = get_case_note_decrypted(profile, appointment_id)
    if note_obj:
        existing_note = note_obj
        plaintext = plaintext_data or ""

    return render(request, "case_notes/editor.html", {
        "profile": profile,
        "appointment": appointment,
        "plaintext": plaintext,
        "existing_note": existing_note,
    })


@role_required("counselor")
def counselor_appointments_view(request):
    """Counselor appointment registry with filtering."""
    profile = request.profile
    status_filter = request.GET.get("status", "all")

    qs = Appointment.objects.filter(counselor=profile).select_related("student").order_by("-scheduled_at")
    counts = {
        "all": qs.count(),
        "pending": qs.filter(status="pending").count(),
        "confirmed": qs.filter(status="confirmed").count(),
        "completed": qs.filter(status="completed").count(),
        "cancelled": qs.filter(status="cancelled").count(),
    }

    filtered_qs = qs.filter(status=status_filter) if status_filter != "all" and status_filter in counts else qs

    return render(request, "counselor/appointments.html", {
        "profile": profile,
        "appointments": filtered_qs,
        "counts": counts,
        "active_filter": status_filter,
    })


@role_required("counselor")
def counselor_case_notes_list_view(request):
    """Counselor repository of clinical case notes."""
    profile = request.profile
    notes_qs = CaseNote.objects.filter(counselor=profile).select_related("appointment__student").order_by("-created_at")

    notes_data = []
    for n in notes_qs:
        try:
            preview = decrypt(n.content)
        except Exception:
            preview = "[Encrypted Content]"
        notes_data.append({
            "note": n,
            "preview": preview[:150] + "..." if len(preview) > 150 else preview,
        })

    stats = {
        "total_notes": notes_qs.count(),
        "confidential_count": notes_qs.filter(is_confidential=True).count(),
        "standard_count": notes_qs.filter(is_confidential=False).count(),
    }

    return render(request, "counselor/case_notes_list.html", {
        "profile": profile,
        "notes": notes_data,
        "stats": stats,
    })


@role_required("counselor")
def counselor_wellness_view(request):
    """Counselor view for reviewing student mood alerts."""
    profile = request.profile
    alerts = StudentMoodAlert.objects.filter(counselor=profile).select_related("student").order_by("-created_at")
    stats = {
        "total_alerts": alerts.count(),
        "unique_students": alerts.values("student").distinct().count(),
    }

    return render(request, "counselor/wellness.html", {
        "profile": profile,
        "alerts": alerts,
        "stats": stats,
    })


@role_required("counselor")
def counselor_profile_view(request):
    """Counselor staff profile."""
    return render(request, "counselor/profile.html", {
        "profile": request.profile,
    })


# ==============================================================================
# 4. RECEPTIONIST / FRONT DESK VIEWS
# ==============================================================================

@role_required("receptionist")
def receptionist_dashboard_view(request):
    """Receptionist daily overview and desk statistics."""
    profile = request.profile
    today = timezone.now().date()

    today_appts = Appointment.objects.filter(
        scheduled_at__date=today
    ).select_related("student", "counselor").order_by("scheduled_at")
    counselors = Profile.objects.filter(role="counselor", is_active=True).order_by("full_name")

    stats = {
        "today_total": today_appts.count(),
        "today_pending": today_appts.filter(status="pending").count(),
        "today_confirmed": today_appts.filter(status="confirmed").count(),
        "today_completed": today_appts.filter(status="completed").count(),
    }

    return render(request, "receptionist/dashboard.html", {
        "profile": profile,
        "today_appointments": today_appts,
        "counselors": counselors,
        "stats": stats,
    })


@role_required("receptionist")
def receptionist_booking_view(request):
    """Receptionist walk-in appointment booking desk."""
    profile = request.profile

    if request.method == "POST":
        student_id = request.POST.get("student_id")
        counselor_id = request.POST.get("counselor_id")
        date_str = request.POST.get("scheduled_date")
        time_str = request.POST.get("scheduled_time")
        concern = request.POST.get("concern_type", "other")
        notes = request.POST.get("notes", "")

        try:
            student_profile = Profile.objects.get(pk=student_id, role="student", is_active=True)
        except Profile.DoesNotExist:
            messages.error(request, "Student not found or inactive.")
            return redirect("/receptionist/")

        try:
            scheduled_dt = timezone.make_aware(
                datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"),
                timezone.get_current_timezone(),
            )
        except (ValueError, TypeError):
            messages.error(request, "Invalid date or time.")
            return redirect("/receptionist/")

        try:
            appt = book_for_student(
                receptionist=profile,
                student=student_profile,
                scheduled_at=scheduled_dt,
                concern_type=concern,
                counselor=counselor_id,
                notes=notes,
            )
            messages.success(
                request,
                f"Appointment booked for {student_profile.full_name} with {appt.counselor.full_name}."
            )
        except Exception as e:
            msg = getattr(e, "message", str(e))
            messages.error(request, msg)
        return redirect("/receptionist/")

    search_query = request.GET.get("search", "")
    students = search_students(search_query) if search_query else []
    counselors = list_counselors()

    return render(request, "receptionist/booking.html", {
        "profile": profile,
        "students": students,
        "counselors": counselors,
        "search_query": search_query,
    })


@role_required("receptionist")
def receptionist_front_desk_view(request):
    """Receptionist office guidelines."""
    return render(request, "receptionist/front_desk.html", {
        "profile": request.profile,
    })


@role_required("receptionist")
def receptionist_profile_view(request):
    """Receptionist profile."""
    return render(request, "receptionist/profile.html", {
        "profile": request.profile,
    })


@role_required("receptionist")
def receptionist_slots_api(request):
    """JSON API for receptionist calendar slots."""
    counselor_id = request.GET.get("counselor_id")
    date_str = request.GET.get("date")

    if not counselor_id or not date_str:
        return JsonResponse({"slots": []})

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"slots": []})

    slots = get_available_slots(counselor_id, date_obj)
    return JsonResponse({
        "slots": [
            {"value": s.strftime("%H:%M"), "label": s.strftime("%I:%M %p")}
            for s in slots
        ]
    })


# ==============================================================================
# 5. ADMINISTRATOR PANEL VIEWS
# ==============================================================================

@role_required("admin")
def admin_overview_view(request):
    """Administrator metrics dashboard with weekly trends and concern breakdown."""
    kpis = get_kpis()
    weekly_series = get_weekly_series()
    concern_breakdown = get_concern_breakdown()
    recent_activity = get_recent_activity()

    return render(request, "analytics/overview.html", {
        "profile": request.profile,
        "kpis": kpis,
        "weekly_series_json": json.dumps(weekly_series),
        "concern_breakdown_json": json.dumps(concern_breakdown),
        "recent_activity": recent_activity,
    })


@role_required("admin")
def admin_users_view(request):
    """Administrator user management with safeguard protections."""
    profile = request.profile

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_user":
            full_name = request.POST.get("full_name", "").strip()
            email = request.POST.get("email", "").strip()
            password = request.POST.get("password", "")
            role = request.POST.get("role", "student")
            student_id = request.POST.get("student_id", "").strip() or None
            department = request.POST.get("department", "").strip() or None

            new_profile, error = create_user(full_name, email, password, role, student_id, department)
            if error:
                messages.error(request, error)
            else:
                messages.success(request, f"User account created for {full_name}.")

        elif action == "change_role":
            target_id = request.POST.get("target_id")
            new_role = request.POST.get("new_role")
            success, error = change_role(profile, target_id, new_role)
            if error:
                messages.error(request, error)
            else:
                messages.success(request, "Role updated successfully.")

        elif action == "toggle_active":
            target_id = request.POST.get("target_id")
            new_status, error = toggle_active(profile, target_id)
            if error:
                messages.error(request, error)
            else:
                status_str = "activated" if new_status else "deactivated"
                messages.success(request, f"User account {status_str}.")

        return redirect("/admin-panel/users/")

    search = request.GET.get("search", "")
    role_filter = request.GET.get("role", "")
    status_filter = request.GET.get("status", "")

    users_qs = Profile.objects.select_related("user").order_by("-created_at")
    if search:
        users_qs = users_qs.filter(
            Q(full_name__icontains=search) |
            Q(student_id__icontains=search) |
            Q(user__email__icontains=search)
        )
    if role_filter:
        users_qs = users_qs.filter(role=role_filter)
    if status_filter:
        users_qs = users_qs.filter(is_active=(status_filter == "active"))

    paginator = Paginator(users_qs, 20)
    users_page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "users/users.html", {
        "profile": profile,
        "users_page": users_page,
        "roles": ROLE_CHOICES,
        "search": search,
        "role_filter": role_filter,
        "status_filter": status_filter,
    })


@role_required("admin")
def admin_audit_logs_view(request):
    """System-wide audit trail inspector with filtering and CSV export."""
    qs = AuditLog.objects.select_related("user").order_by("-created_at")

    user_filter = request.GET.get("user", "")
    action_filter = request.GET.get("action", "")
    table_filter = request.GET.get("table", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if user_filter:
        qs = qs.filter(user__full_name__icontains=user_filter)
    if action_filter:
        qs = qs.filter(action__icontains=action_filter)
    if table_filter:
        qs = qs.filter(table_name__icontains=table_filter)
    if date_from:
        try:
            qs = qs.filter(created_at__gte=datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(created_at__lte=datetime.strptime(date_to, "%Y-%m-%d"))
        except ValueError:
            pass

    if request.GET.get("export") == "csv":
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "User", "Action", "Table", "Record ID", "Metadata"])
        for log in qs[:1000]:
            writer.writerow([
                log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                log.user.full_name if log.user else "System",
                log.action,
                log.table_name,
                str(log.record_id) if log.record_id else "",
                json.dumps(log.metadata),
            ])
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=audit_logs.csv"
        return response

    paginator = Paginator(qs, 25)
    logs_page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "audit/logs.html", {
        "profile": request.profile,
        "logs_page": logs_page,
        "user_filter": user_filter,
        "action_filter": action_filter,
        "table_filter": table_filter,
        "date_from": date_from,
        "date_to": date_to,
    })


@role_required("admin")
def admin_reports_view(request):
    """Administrative appointment report generation and CSV/PDF export."""
    profile = request.profile
    appointments = None
    summary = None

    filters = {
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
        "department": request.GET.get("department", ""),
        "concern_type": request.GET.get("concern_type", ""),
        "status": request.GET.get("status", ""),
        "counselor_id": request.GET.get("counselor_id", ""),
    }

    parsed_filters = {}
    for k, v in filters.items():
        if v and k in ("date_from", "date_to"):
            try:
                parsed_filters[k] = datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                pass
        elif v:
            parsed_filters[k] = v

    if request.GET.get("generate"):
        appointments = generate_report(parsed_filters, profile)
        summary = {
            "total": appointments.count(),
            "pending": appointments.filter(status="pending").count(),
            "confirmed": appointments.filter(status="confirmed").count(),
            "completed": appointments.filter(status="completed").count(),
            "cancelled": appointments.filter(status="cancelled").count(),
        }

    export_type = request.GET.get("export")
    if export_type and appointments is not None:
        if export_type == "csv":
            return export_csv(appointments, exported_by=profile)
        elif export_type == "pdf":
            return export_pdf(appointments, exported_by=profile)

    counselors = Profile.objects.filter(role="counselor").order_by("full_name")

    return render(request, "analytics/reports.html", {
        "profile": profile,
        "filters": filters,
        "appointments": appointments[:50] if appointments is not None else None,
        "summary": summary,
        "counselors": counselors,
        "concern_choices": CONCERN_CHOICES,
        "status_choices": STATUS_CHOICES,
    })


@role_required("admin")
def admin_profile_view(request):
    """Administrator profile."""
    return render(request, "users/profile.html", {
        "profile": request.profile,
    })


# ==============================================================================
# 6. AI WELLNESS CHATBOT ENDPOINTS
# ==============================================================================

def has_llm_api_key():
    """Check if AI API key is configured."""
    import os
    groq = getattr(settings, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
    anthropic = getattr(settings, "ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    return bool(groq or anthropic)


@role_required("student")
def chat_session_view(request):
    """GET: return latest chat session for the student."""
    if not check_session_get_rate_limit(request.profile.id):
        resp = JsonResponse({"error": "Too many requests", "retryAfter": 900}, status=429)
        resp["Retry-After"] = "900"
        return resp

    session = get_session(request.profile)
    if session:
        return JsonResponse({
            "sessionId": session.pk,
            "messages": session.messages,
        })
    return JsonResponse({"sessionId": None, "messages": []})


@csrf_exempt
@role_required("student")
def chat_stream_view(request):
    """POST: stream AI response via SSE."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    if not check_chat_rate_limit(request.profile.id):
        resp = JsonResponse({"error": "Too many requests", "retryAfter": 900}, status=429)
        resp["Retry-After"] = "900"
        return resp

    if not has_llm_api_key():
        return JsonResponse({"error": "AI service unavailable"}, status=503)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_messages = body.get("messages", [])
    session_id = body.get("sessionId")

    if not user_messages or not isinstance(user_messages, list):
        return JsonResponse({"error": "Messages must be a non-empty list"}, status=400)

    if user_messages[-1].get("role") != "user":
        return JsonResponse({"error": "Last message must be from user"}, status=400)

    total_content = sum(len(m.get("content", "")) for m in user_messages)
    if total_content > 24000:
        return JsonResponse({"error": "Content exceeds maximum length of 24,000 characters"}, status=400)

    if session_id:
        if not ChatbotSession.objects.filter(pk=session_id, student=request.profile).exists():
            return JsonResponse({"error": "Unauthorized session access"}, status=403)

    response = StreamingHttpResponse(
        stream_chat(request.profile, user_messages, session_id),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


# ==============================================================================
# Namespace Aliases for Modular Compatibility
# ==============================================================================
class _Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

auth = _Namespace(
    landing_view=landing_view,
    login_view=login_view,
    register_view=register_view,
    logout_view=logout_view,
    password_change_view=password_change_view,
)

student = _Namespace(
    dashboard_view=student_dashboard_view,
    appointments_view=student_appointments_view,
    get_slots_api=student_get_slots_api,
    profile_view=student_profile_view,
    front_desk_view=student_front_desk_view,
    chatbot_page_view=student_chatbot_page_view,
    mood_checkin_view=student_mood_checkin_view,
    cancel_appointment_view=student_cancel_appointment_view,
)

counselor = _Namespace(
    workspace_view=counselor_workspace_view,
    case_note_view=counselor_case_note_view,
    appointments_view=counselor_appointments_view,
    case_notes_list_view=counselor_case_notes_list_view,
    wellness_view=counselor_wellness_view,
    profile_view=counselor_profile_view,
)

receptionist = _Namespace(
    dashboard_view=receptionist_dashboard_view,
    booking_view=receptionist_booking_view,
    front_desk_view=receptionist_front_desk_view,
    profile_view=receptionist_profile_view,
    receptionist_slots_api=receptionist_slots_api,
)

admin_views = _Namespace(
    overview_view=admin_overview_view,
    users_view=admin_users_view,
    audit_logs_view=admin_audit_logs_view,
    reports_view=admin_reports_view,
    admin_profile_view=admin_profile_view,
)

chat = _Namespace(
    chat_session_view=chat_session_view,
    chat_stream_view=chat_stream_view,
    has_llm_api_key=has_llm_api_key,
)
