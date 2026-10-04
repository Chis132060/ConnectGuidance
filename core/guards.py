"""
Role-Based Access Control (RBAC) Decorators.
Enforces role permissions and active account verification for protected views.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth import logout
from .choices import ROLE_HOME


def get_profile_or_none(user):
    """Return the User Profile if authenticated and exists, otherwise None."""
    if not user.is_authenticated:
        return None
    try:
        return user.profile
    except Exception:
        return None


def role_home(role):
    """Return the default dashboard landing URL for a given role."""
    return ROLE_HOME.get(role, "/")


def role_required(*roles):
    """
    Decorator: ensures the user is authenticated and has an active profile matching one of the required roles.
    - Unauthenticated: redirects to /login/?next=...
    - Inactive profile: logs out and redirects to /login/?error=deactivated
    - Missing profile: logs out and redirects to /login/?error=no_profile
    - Wrong role: redirects to the user's role home dashboard
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/login/?next={request.path}")

            profile = get_profile_or_none(request.user)
            if not profile:
                logout(request)
                return redirect("/login/?error=no_profile")

            if not profile.is_active:
                logout(request)
                return redirect("/login/?error=deactivated")

            if profile.role not in roles:
                return redirect(role_home(profile.role))

            request.profile = profile
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_student(view_func):
    return role_required("student")(view_func)


def require_counselor(view_func):
    return role_required("counselor")(view_func)


def require_admin(view_func):
    return role_required("admin")(view_func)


def require_receptionist(view_func):
    return role_required("receptionist")(view_func)


get_role_home = role_home

