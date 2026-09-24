from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .choices import RoleChoices

ROLE_HOMES = {
    RoleChoices.ADMIN: '/admin-panel/',
    RoleChoices.COUNSELOR: '/counselor/',
    RoleChoices.STUDENT: '/student/',
    RoleChoices.RECEPTIONIST: '/receptionist/',
}


def get_role_home(role: str) -> str:
    """Return the designated landing URL for a given user role."""
    return ROLE_HOMES.get(role, '/student/')


def get_profile_or_none(user):
    """Safely return user's associated profile or None."""
    if not user or not user.is_authenticated:
        return None
    return getattr(user, 'profile', None)


def role_required(*allowed_roles):
    """
    View decorator enforcing authentication and role membership.
    If the user's profile is deactivated, immediately logs them out and redirects to /login/?error=deactivated.
    If the user has an unpermitted role, redirects them to their designated role home.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/login/?next={request.path}")

            profile = get_profile_or_none(request.user)
            if not profile:
                logout(request)
                return redirect("/login/?error=no_profile")

            if not profile.is_active:
                logout(request)
                return redirect("/login/?error=deactivated")

            if allowed_roles and profile.role not in allowed_roles:
                return redirect(get_role_home(profile.role))

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def require_admin(view_func):
    return role_required(RoleChoices.ADMIN)(view_func)


def require_counselor(view_func):
    return role_required(RoleChoices.COUNSELOR)(view_func)


def require_student(view_func):
    return role_required(RoleChoices.STUDENT)(view_func)


def require_receptionist(view_func):
    return role_required(RoleChoices.RECEPTIONIST)(view_func)
