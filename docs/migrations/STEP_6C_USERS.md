# STEP 6C — Users Feature Migration

**Date:** 2026-10-02  
**Status:** ✅ COMPLETE  
**Test Results:** 77/77 → 81/81 (+4 new tests, all passing)

## Overview
Extracted user management functionality from core/ into dedicated `apps/users/` feature app.

## What Was Migrated

### Services (1 file)
- `core/services/admin_users.py` → `apps/users/services/management.py`
  - `can_change_role()` - RBAC safeguards for role changes
  - `can_change_active_status()` - RBAC safeguards for status changes
  - `update_user_role()` - Safe role updates with audit logging
  - `update_user_status()` - Safe status updates with audit logging
  - `create_user_by_admin()` - Admin user creation

### Views (2 functions)
Extracted from `core/views/admin_views.py` → `apps/users/views.py`:
- `admin_users_view()` - User management with search, filtering, role/status changes
- `admin_profile_view()` - Administrator profile and password modification

### Templates (2 files)
- `templates/admin/users.html` → `apps/users/templates/users/users.html`
- `templates/admin/profile.html` → `apps/users/templates/users/profile.html`

### Tests (4 new tests)
Created `apps/users/tests/test_views.py`:
- `test_admin_users_requires_admin_role()`
- `test_admin_users_accessible_by_admin()`
- `test_admin_profile_requires_admin_role()`
- `test_admin_profile_accessible_by_admin()`

## Import Updates (3 files)
Fixed import paths in:
1. `tests/test_admin_safeguards.py` - user management service imports
2. `tests/test_views_http.py` - template path assertions (2 tests)
3. `config/settings/base.py` - added apps.users to INSTALLED_APPS

## URL Changes
- **config/urls.py:** Added `path('admin-panel/', include('apps.users.urls'))`
- **core/urls.py:** Removed admin_users and admin_profile routes
- **apps/users/urls.py:** Created new URL patterns for user management views

## Files Created
```
apps/users/
├── __init__.py
├── apps.py
├── services/
│   ├── __init__.py
│   └── management.py
├── templates/
│   └── users/
│       ├── users.html
│       └── profile.html
├── tests/
│   ├── __init__.py
│   └── test_views.py
├── urls.py
└── views.py
```

## Files Deleted
- `core/services/admin_users.py`
- `core/views/admin_views.py` (completely migrated, now empty)
- `templates/admin/users.html`
- `templates/admin/profile.html`

## RBAC Safeguards Preserved
All admin safety rules maintained:
1. **Cannot demote self** - Admins cannot change their own role away from admin
2. **Cannot deactivate self** - Admins cannot deactivate their own account
3. **Cannot remove last admin** - Cannot demote the last active admin
4. **Cannot deactivate last admin** - Cannot deactivate the last active admin

## Dependencies
Users depends on:
- `apps.authentication.guards` - @require_admin decorator
- `apps.audit.services.logging` - log_action() for all user changes
- `apps.common.choices` - RoleChoices enum
- `core.models` - Profile, User models

## Verification Checklist
- [x] Django check passes (0 issues)
- [x] Makemigrations shows no changes (models untouched)
- [x] All 81 tests pass (77 + 4 new)
- [x] URLs properly routed (/admin-panel/users/, /admin-panel/profile/)
- [x] Templates render correctly (users/users.html, users/profile.html)
- [x] RBAC safeguards work (self-demotion, last-admin protection)
- [x] Audit logging works for all user changes
- [x] Old files cleaned up

## Notes
- Models remain in `core/models.py` (database safety)
- User management views maintain original functionality
- Pagination set to 20 users per page
- Search supports full_name, student_id, and email
- Password change uses Django's PasswordChangeForm
- All admin safeguards thoroughly tested (18 test cases in test_admin_safeguards.py)
