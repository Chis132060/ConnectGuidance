"""
Authentication views — login, user registration, logout, and password change.
Handles authentication workflows, session management, and role-based redirects.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db.models import Max
from core.models import Profile
from core.choices import ROLE_HOME
from core.guards import get_profile_or_none


def landing_view(request):
    """Public landing page."""
    if request.user.is_authenticated:
        profile = get_profile_or_none(request.user)
        if profile and profile.is_active:
            return redirect(ROLE_HOME.get(profile.role, "/"))
    return render(request, "public/landing.html")


def login_view(request):
    """Login page + POST handler."""
    if request.user.is_authenticated:
        profile = get_profile_or_none(request.user)
        if profile and profile.is_active:
            return redirect(ROLE_HOME.get(profile.role, "/"))

    error = request.GET.get("error", "")
    next_url = request.GET.get("next", "")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        # Try to find user by email (stored as username)
        user = authenticate(request, username=email, password=password)
        if user is None:
            # Also try with actual username field
            try:
                u = User.objects.get(email=email)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass

        if user is None:
            return render(request, "registration/login.html", {
                "error": "Invalid email or password.",
                "email": email,
            })

        profile = get_profile_or_none(user)
        if not profile:
            return render(request, "registration/login.html", {
                "error": "Account configuration error. Please contact support.",
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
        context["error"] = "Account configuration error. Please contact support."

    return render(request, "registration/login.html", context)


def register_view(request):
    """Student registration."""
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
            return render(request, "registration/register.html", {
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

        # Update the auto-created profile
        profile = user.profile
        profile.full_name = full_name
        profile.student_id = student_id or None
        profile.department = department or None
        profile.save()

        messages.success(request, "Welcome to GuidanceConnect! Your account has been created.")
        return redirect("login")

    return render(request, "registration/register.html")


def logout_view(request):
    """Logout and redirect to landing."""
    logout(request)
    return redirect("/")


@login_required
def password_change_view(request):
    """Password change form."""
    profile = get_profile_or_none(request.user)
    if not profile:
        logout(request)
        return redirect("/login/?error=no_profile")

    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            # Keep user logged in
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect(ROLE_HOME.get(profile.role, "/"))
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "registration/password_change.html", {
        "form": form,
        "profile": profile,
    })
