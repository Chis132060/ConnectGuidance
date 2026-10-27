from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Max

from accounts.forms import StudentRegistrationForm
from accounts.decorators import get_profile_or_none, get_role_home
from accounts.models import Profile
from accounts.choices import RoleChoices


def landing_view(request):
    """
    Public landing page.
    Redirects authenticated users to their designated role dashboard.
    """
    if request.user.is_authenticated:
        profile = get_profile_or_none(request.user)
        if profile and not profile.is_active:
            auth_logout(request)
            return redirect('/login/?error=deactivated')
        if profile:
            return redirect(get_role_home(profile.role))
        auth_logout(request)
        return redirect('/login/?error=no_profile')

    return render(request, 'common/landing.html')


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    User Sign-in.
    Accepts either email address or username with password.
    Redirects to respective role portal upon successful verification.
    """
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
            lookup_user = (
                User.objects.filter(email__iexact=email).first() or
                User.objects.filter(username__iexact=email).first()
            )
            username_to_auth = lookup_user.username if lookup_user else email
            user = authenticate(request, username=username_to_auth, password=password)

            if user is None:
                form_error = 'Invalid email or password.'
            else:
                profile = get_profile_or_none(user)
                if not profile:
                    return redirect('/login/?error=no_profile')

                if not profile.is_active:
                    return redirect('/login/?error=deactivated')

                login(request, user)
                messages.success(request, "Login successful!")

                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect(get_role_home(profile.role))

    context = {
        'error': error,
        'form_error': form_error,
        'next': next_url,
    }
    return render(request, 'authentication/login.html', context)


def logout_view(request):
    """Sign out the current user session and redirect to landing page."""
    auth_logout(request)
    messages.success(request, "You have been signed out successfully.")
    return redirect('landing')


@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    Student self-registration.
    Creates a new User and an active Student Profile with auto-assigned user_no.
    """
    if request.user.is_authenticated:
        profile = get_profile_or_none(request.user)
        if profile:
            return redirect(get_role_home(profile.role))

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            full_name = form.cleaned_data['full_name']
            student_id = form.cleaned_data.get('student_id', '')
            department = form.cleaned_data.get('department', '')

            # Create User with email as username
            username = email.lower().strip()

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name.split()[0] if full_name else '',
                last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
            )

            # Create or update Student Profile
            max_no = Profile.objects.aggregate(m=Max('user_no'))['m'] or 0
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = RoleChoices.STUDENT
            profile.full_name = full_name
            profile.student_id = student_id or None
            profile.department = department or None
            profile.user_no = max_no + 1
            profile.is_active = True
            profile.save()

            messages.success(request, "Registration successful! You may now sign in.")
            return redirect('login')
    else:
        form = StudentRegistrationForm()

    return render(request, 'authentication/register.html', {'form': form})


@login_required
def password_change_view(request):
    """Standard password change for authenticated users."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password updated successfully.")
            profile = get_profile_or_none(request.user)
            return redirect(get_role_home(profile.role) if profile else 'landing')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'authentication/password_change.html', {'form': form})


@login_required
def role_home_view(request):
    """Dispatch logged-in user to their proper dashboard."""
    profile = get_profile_or_none(request.user)
    if profile:
        return redirect(get_role_home(profile.role))
    return redirect('landing')
