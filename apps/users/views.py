"""
apps/users/views.py — User management views for GuidanceConnect.

Implements FLOWS §17-18:
- /admin-panel/users/ — User management, role transitions, status toggling, and user creation
- /admin-panel/profile/ — Administrator profile and password modification
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from apps.authentication.guards import require_admin
from core.models import Profile
from apps.common.choices import RoleChoices
from apps.users.services.management import (
    update_user_role,
    update_user_status,
    create_user_by_admin,
)


@require_admin
@require_http_methods(["GET", "POST"])
def admin_users_view(request):
    """
    INTERFACES #12 / FLOWS §17-18: User Management.
    Supports user search, role/status filtering, inline role modifications,
    account activation/deactivation, and manual staff account creation.
    """
    admin_profile = request.user.profile

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_user':
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '')
            full_name = request.POST.get('full_name', '').strip()
            role = request.POST.get('role', RoleChoices.STUDENT)
            student_id = request.POST.get('student_id', '').strip()
            department = request.POST.get('department', '').strip()

            try:
                create_user_by_admin(
                    actor=admin_profile,
                    email=email,
                    password=password,
                    full_name=full_name,
                    role=role,
                    student_id=student_id,
                    department=department
                )
                messages.success(request, f"User account for {full_name} ({email}) created successfully.")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))
            except Exception as e:
                messages.error(request, f"Error creating user: {e}")

        elif action == 'change_role':
            target_id = request.POST.get('target_id')
            new_role = request.POST.get('new_role')
            target = get_object_or_404(Profile, id=target_id)
            try:
                update_user_role(admin_profile, target, new_role)
                messages.success(request, f"Role for {target.full_name} updated to {new_role}.")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))

        elif action == 'toggle_status':
            target_id = request.POST.get('target_id')
            new_status_str = request.POST.get('new_is_active', 'false').lower()
            new_is_active = (new_status_str == 'true')
            target = get_object_or_404(Profile, id=target_id)
            try:
                update_user_status(admin_profile, target, new_is_active)
                status_text = "activated" if new_is_active else "deactivated"
                messages.success(request, f"User {target.full_name} has been {status_text}.")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))

        return redirect('admin_users')

    # GET Filter & Search
    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    profiles_qs = Profile.objects.select_related('user').all().order_by('-user_no', 'full_name')

    if q:
        profiles_qs = profiles_qs.filter(
            Q(full_name__icontains=q) |
            Q(student_id__icontains=q) |
            Q(user__email__icontains=q)
        )
    if role_filter:
        profiles_qs = profiles_qs.filter(role=role_filter)
    if status_filter == 'active':
        profiles_qs = profiles_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        profiles_qs = profiles_qs.filter(is_active=False)

    paginator = Paginator(profiles_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile': admin_profile,
        'page_obj': page_obj,
        'q': q,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': RoleChoices.choices,
    }
    return render(request, 'users/users.html', context)


@require_admin
@require_http_methods(["GET", "POST"])
def admin_profile_view(request):
    """
    INTERFACES #15: Admin profile and password modification.
    """
    admin_profile = request.user.profile

    if request.method == 'POST':
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect('admin_profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        password_form = PasswordChangeForm(user=request.user)

    context = {
        'profile': admin_profile,
        'user': request.user,
        'password_form': password_form,
    }
    return render(request, 'users/profile.html', context)
