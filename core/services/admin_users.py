"""
Admin User Management Service.
Handles administrative user provisioning, role assignments, and account activation/deactivation
with safety rules (e.g. self-demotion and last-admin safeguards).
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from core.models import Profile
from core.choices import RoleChoices
from core.services.audit import log_action


def can_change_role(actor, target, new_role):
    """Check if actor is permitted to change target user's role."""
    if actor.pk == target.pk and new_role != RoleChoices.ADMIN:
        return False, "You cannot demote your own admin account."
    if target.role == RoleChoices.ADMIN and new_role != RoleChoices.ADMIN:
        admin_count = Profile.objects.filter(role=RoleChoices.ADMIN, is_active=True).count()
        if admin_count <= 1:
            return False, "Cannot remove the last admin account."
    return True, None


def update_user_role(actor, target, new_role):
    """Update target user role, enforcing admin safeguards."""
    allowed, msg = can_change_role(actor, target, new_role)
    if not allowed:
        raise ValidationError(msg)

    target.role = new_role
    target.save(update_fields=["role"])

    # Synchronize django user is_staff flag
    if hasattr(target, "user") and target.user:
        target.user.is_staff = (new_role == RoleChoices.ADMIN)
        target.user.save(update_fields=["is_staff"])

    log_action(
        user=actor,
        action="USER_ROLE_UPDATED",
        table_name="core_profile",
        record_id=target.pk,
        metadata={"new_role": new_role, "target_user_id": target.pk},
    )

    return target


def can_change_active_status(actor, target, new_status):
    """Check if actor is permitted to update target active status."""
    if actor.pk == target.pk and not new_status:
        return False, "You cannot deactivate your own account."
    if target.role == RoleChoices.ADMIN and not new_status:
        admin_count = Profile.objects.filter(role=RoleChoices.ADMIN, is_active=True).count()
        if admin_count <= 1:
            return False, "Cannot deactivate the last active admin."
    return True, None


def update_user_status(actor, target, new_status):
    """Update target user active status, enforcing safeguards."""
    allowed, msg = can_change_active_status(actor, target, new_status)
    if not allowed:
        raise ValidationError(msg)

    target.is_active = new_status
    target.save(update_fields=["is_active"])

    if hasattr(target, "user") and target.user:
        target.user.is_active = new_status
        target.user.save(update_fields=["is_active"])

    log_action(
        user=actor,
        action="USER_STATUS_UPDATED",
        table_name="core_profile",
        record_id=target.pk,
        metadata={"new_status": new_status, "target_user_id": target.pk},
    )

    return target


def change_role(admin_profile, target_profile_id, new_role):
    """Wrapper returning (success, error) for views."""
    try:
        target = Profile.objects.get(pk=target_profile_id)
    except Profile.DoesNotExist:
        return False, "User not found."
    try:
        update_user_role(admin_profile, target, new_role)
        return True, None
    except ValidationError as e:
        return False, str(e.message if hasattr(e, 'message') else e)


def toggle_active(admin_profile, target_profile_id):
    """Wrapper returning (new_status, error) for views."""
    try:
        target = Profile.objects.get(pk=target_profile_id)
    except Profile.DoesNotExist:
        return None, "User not found."
    new_status = not target.is_active
    try:
        updated = update_user_status(admin_profile, target, new_status)
        return updated.is_active, None
    except ValidationError as e:
        return None, str(e.message if hasattr(e, 'message') else e)


def create_user_by_admin(actor, email, password, full_name, role=RoleChoices.STUDENT, student_id=None, department=None):
    """Admin creates a new user profile."""
    if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
        raise ValidationError("A user with this email already exists.")

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=full_name.split()[0] if full_name else "",
        last_name=" ".join(full_name.split()[1:]) if full_name and " " in full_name else "",
        is_staff=(role == RoleChoices.ADMIN),
    )

    profile = user.profile
    profile.role = role
    profile.full_name = full_name
    profile.student_id = student_id
    profile.department = department
    profile.is_active = True
    profile.save()

    log_action(
        user=actor,
        action="USER_CREATED_ADMIN",
        table_name="core_profile",
        record_id=profile.pk,
        metadata={"email": email, "role": role},
    )

    return profile


def create_user(full_name, email, password, role=RoleChoices.STUDENT, student_id=None, department=None):
    """Helper for non-actor admin forms."""
    try:
        p = create_user_by_admin(None, email, password, full_name, role, student_id, department)
        return p, None
    except ValidationError as e:
        return None, str(e.message if hasattr(e, 'message') else e)
