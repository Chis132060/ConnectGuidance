"""
core/views/auth.py — Authentication views for GuidanceConnect Django replica.

Implements FLOWS §1-6: landing, login, logout, register, password_change, role_home.
All business logic delegates to existing services/forms/guards.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from core.forms import StudentRegistrationForm
from core.guards import get_profile_or_none, get_role_home


# ---------------------------------------------------------------------------
# Landing page (public)
# ---------------------------------------------------------------------------

def landing_view(request):
    """
    FLOWS §1: Public path.
    - Authenticated + active → redirect ROLE_HOME
    - Authenticated + inactive → logout + /login/?error=deactivated
    - Unauthenticated → render landing page
    """
    if request.user.is_authenticated:
        profile = get_profile_or_none(request.user)
        if profile and not profile.is_active:
            auth_logout(request)
            return redirect('/login/?error=deactivated')
        if profile:
            return redirect(get_role_home(profile.role))
        # No profile — force logout
        auth_logout(request)
        return redirect('/login/?error=no_profile')

    return render(request, 'public/landing.html')


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    FLOWS §3: Sign-in.
    - Authenticated + active → redirect ROLE_HOME (skip login page)
    - Authenticated + inactive → logout + ?error=deactivated
    - POST: email + password → authenticate → check profile → check active → ROLE_HOME
    - Errors: invalid creds, no_profile, deactivated (via query param)
    """
    # Already authenticated? Redirect away.
    if request.user.is_authenticated:
        profile = get_profile_or_none(request.user)
        if profile and not profile.is_active:
            auth_logout(request)
            return redirect('/login/?error=deactivated')
        if profile:
            return redirect(get_role_home(profile.role))
        auth_logout(request)
        return redirect('/login/?error=no_profile')

    error = request.GET.get('error', '')
    next_url = request.GET.get('next', '')
    form_error = ''

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        if not email or not password:
            form_error = 'Please enter your email and password.'
        else:
            # Django authenticates by username — we store username=email
            user = authenticate(request, username=email, password=password)

            if user is None:
                # Could be wrong password or user doesn't exist
                form_error = 'Invalid email or password.'
            else:
                # Check profile exists
                profile = get_profile_or_none(user)
                if not profile:
                    return redirect('/login/?error=no_profile')

                # Check active status
                if not profile.is_active:
                    return redirect('/login/?error=deactivated')

                # Success — login and redirect
                login(request, user)
                redirect_to = request.POST.get('next', next_url)
                if redirect_to:
                    return redirect(redirect_to)
                return redirect(get_role_home(profile.role))

    context = {
        'error': error,
        'form_error': form_error,
        'next': next_url,
    }
    return render(request, 'registration/login.html', context)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    FLOWS §4: Sign-out.
    POST preferred; GET also allowed for parity.
    Flush session → redirect '/'
    """
    auth_logout(request)
    return redirect('/')


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    FLOWS §2: Student registration.
    - Authenticated + active → redirect ROLE_HOME (don't show register page)
    - POST: validate form → create User (username=email) → signal creates Profile(student)
    - On success: redirect to login with success message
    - On error: re-render with field errors
    """
    if request.user.is_authenticated:
        profile = get_profile_or_none(request.user)
        if profile and not profile.is_active:
            auth_logout(request)
            return redirect('/login/?error=deactivated')
        if profile:
            return redirect(get_role_home(profile.role))
        auth_logout(request)

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            full_name = form.cleaned_data['full_name']
            student_id = form.cleaned_data.get('student_id', '')
            department = form.cleaned_data.get('department', '')

            # Create User with username=email (parity with original signin)
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=full_name.split(' ')[0] if full_name else '',
                last_name=' '.join(full_name.split(' ')[1:]) if ' ' in full_name else '',
            )

            # Signal auto-creates Profile with role=student.
            # Update the profile with additional fields.
            profile = user.profile
            profile.full_name = full_name
            profile.student_id = student_id or None
            profile.department = department or None
            profile.save()

            messages.success(request, 'Registration successful! Please sign in.')
            return redirect('login')
    else:
        form = StudentRegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
def password_change_view(request):
    """
    FLOWS §5: Password change.
    Uses Django's built-in PasswordChangeForm.
    Stays signed in after success (update_session_auth_hash handled by the form).
    """
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # update_session_auth_hash keeps user logged in after password change
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Your password has been changed successfully.')
            # Redirect to role home
            profile = get_profile_or_none(request.user)
            if profile:
                return redirect(get_role_home(profile.role))
            return redirect('role_home')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'registration/password_change.html', {'form': form})


# ---------------------------------------------------------------------------
# Role home redirect
# ---------------------------------------------------------------------------

@login_required
def role_home_view(request):
    """
    FLOWS §6: Role home redirect.
    Reads profile.role → redirects to the appropriate dashboard.
    This is the target of settings.LOGIN_REDIRECT_URL.
    """
    profile = get_profile_or_none(request.user)
    if not profile:
        auth_logout(request)
        return redirect('/login/?error=no_profile')

    if not profile.is_active:
        auth_logout(request)
        return redirect('/login/?error=deactivated')

    return redirect(get_role_home(profile.role))
