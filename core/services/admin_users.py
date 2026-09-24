"""
core/services/admin_users.py — Admin user management and RBAC safeguards for GuidanceConnect.

Implements RLS §5 and FLOWS §17-18:
- Safeguards preventing self-demotion, last-admin removal, self-deactivation, and last active admin deactivation.
- Admin user creation and role modifications.
"""

from typing import Tuple, Optional
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.models import User

from core.models import Profile, AuditLog
from core.choices import RoleChoices
from core.services.audit import log_action


def can_change_role(actor: Profile, target: Profile, new_role: str) -> Tuple[bool, str]:
    """
    FLOWS §17: Verify whether actor may change target's role.
    Safeguards:
    1. Cannot demote self: actor cannot change their own role away from admin.
    2. Cannot remove last admin: if target is admin and total active admins <= 1, demotion is forbidden.
    """
    if target.id == actor.id and new_role != RoleChoices.ADMIN:
        return False, "You cannot demote your own admin account here."

    if target.role == RoleChoices.ADMIN and new_role != RoleChoices.ADMIN:
        active_admin_count = Profile.objects.filter(
            role=RoleChoices.ADMIN,
            is_active=True
        ).count()
        if active_admin_count <= 1:
            return False, "Cannot remove the last admin account."

    return True, ""


def can_change_active_status(actor: Profile, target: Profile, new_is_active: bool) -> Tuple[bool, str]:
    """
    FLOWS §18: Verify whether actor may change target's active status.
    Safeguards:
    1. Cannot deactivate self: actor cannot deactivate their own account.
    2. Cannot deactivate last active admin: if target is admin and total active admins <= 1, deactivation is forbidden.
    """
    if target.id == actor.id and not new_is_active:
        return False, "You cannot deactivate your own account."

    if target.role == RoleChoices.ADMIN and not new_is_active:
        active_admin_count = Profile.objects.filter(
            role=RoleChoices.ADMIN,
            is_active=True
        ).count()
        if active_admin_count <= 1:
            return False, "Cannot deactivate the last active admin."

    return True, ""


@transaction.atomic
def update_user_role(actor: Profile, target: Profile, new_role: str) -> Profile:
    """Safely updates target profile role enforcing admin safeguards and audit dual-write."""
    allowed, reason = can_change_role(actor, target, new_role)
    if not allowed:
        raise ValidationError(reason)

    old_role = target.role
    target.role = new_role
    target.save(update_fields=['role'])

    if hasattr(target, 'user') and target.user:
        target.user.is_staff = (new_role == RoleChoices.ADMIN)
        target.user.save(update_fields=['is_staff'])

    log_action(
        user=actor,
        action="USER_ROLE_UPDATED",
        table_name="core_profile",
        record_id=target.id,
        metadata={
            "old_role": old_role,
            "new_role": new_role,
            "target_user_id": target.user_id
        }
    )
    return target


@transaction.atomic
def update_user_status(actor: Profile, target: Profile, new_is_active: bool) -> Profile:
    """Safely toggles active status enforcing admin safeguards and audit dual-write."""
    allowed, reason = can_change_active_status(actor, target, new_is_active)
    if not allowed:
        raise ValidationError(reason)

    old_status = target.is_active
    target.is_active = new_is_active
    target.save(update_fields=['is_active'])

    if hasattr(target, 'user') and target.user:
        target.user.is_active = new_is_active
        target.user.save(update_fields=['is_active'])

    action = "USER_ACTIVATED" if new_is_active else "USER_DEACTIVATED"
    log_action(
        user=actor,
        action=action,
        table_name="core_profile",
        record_id=target.id,
        metadata={
            "old_status": old_status,
            "new_status": new_is_active,
            "target_user_id": target.user_id
        }
    )
    return target


@transaction.atomic
def create_user_by_admin(
    actor: Profile,
    email: str,
    password: str,
    full_name: str,
    role: str,
    student_id: Optional[str] = None,
    department: Optional[str] = None
) -> Profile:
    """Allows an administrator to manually create an active user with any specified role."""
    email_clean = email.strip().lower()
    if User.objects.filter(username=email_clean).exists() or User.objects.filter(email=email_clean).exists():
        raise ValidationError("A user with this email address already exists.")

    user = User.objects.create_user(
        username=email_clean,
        email=email_clean,
        password=password,
        first_name=full_name.split(' ')[0] if full_name else '',
        last_name=' '.join(full_name.split(' ')[1:]) if ' ' in full_name else '',
        is_staff=(role == RoleChoices.ADMIN)
    )

    profile = user.profile
    profile.full_name = full_name
    profile.role = role
    profile.student_id = student_id or None
    profile.department = department or None
    profile.is_active = True
    profile.save()

    log_action(
        user=actor,
        action="USER_CREATED_ADMIN",
        table_name="core_profile",
        record_id=profile.id,
        metadata={
            "role": role,
            "email": email_clean,
            "full_name": full_name
        }
    )
    return profile
