# Password Change Functionality Guide

## 1. Purpose

This feature lets an authenticated ConnectGuidance user replace the password used to sign in. It verifies the current password, validates the new password against Django's security rules, stores a secure password hash, and gives the user success or validation feedback.

It changes only the login password. It does not change the user's name, email, role, active status, appointments, or other profile data.

## 2. Current Role Coverage

The source code currently defines these roles in `accounts/choices.py`:

| Role | Password page |
|---|---|
| Admin | `/admin-panel/profile/` |
| Counselor | `/counselor/profile/` |
| Student | `/student/profile/` |
| Receptionist | `/receptionist/profile/` |

Supervisor, Salesman, and Buyer are not defined in this project. Consequently, there are no password-change pages or role guards for those roles yet.

## 3. Data Model and Storage

The application uses Django's built-in `User` model and the project's one-to-one `Profile` model.

- `auth_user.password` stores the salted password hash.
- `core_profile` stores the user's role, full name, active status, user number, and related profile information.
- The raw password is not stored in `core_profile` or in plain text in `auth_user`.

The profile determines which protected page the user can open. The password is owned by the Django user account.

## 4. Main Implementation Components

### Authentication and views

- `accounts/views.py` contains the shared `password_change_view`.
- `accounts/urls.py` exposes `/password-change/`.
- `core/views.py` contains the Admin, Counselor, Student, and Receptionist profile handlers.
- `core/urls.py` exposes the four role-specific profile URLs.

### Templates

- `templates/authentication/password_change.html`
- `templates/student/profile.html`
- `templates/counselor/profile.html`
- `templates/receptionist/profile.html`
- `templates/users/profile.html` for Admin

### Configuration and models

- `accounts/choices.py` defines the current roles.
- `accounts/models.py` defines `Profile`.
- `config/settings.py` defines middleware, password validators, session behavior, and database configuration.
- `core/signals.py` handles profile creation and profile audit behavior.

## 5. Password Form

Every password-change handler uses Django's built-in `PasswordChangeForm`:

```python
PasswordChangeForm(user=request.user, data=request.POST)
```

The form has three fields:

1. `old_password` — the current password.
2. `new_password1` — the proposed replacement password.
3. `new_password2` — confirmation of the replacement password.

Each role template includes a CSRF token:

```django
{% csrf_token %}
```

This protects the password-changing POST request against cross-site request forgery.

## 6. Available Endpoints

| Role | URL | URL name | View | Template | Guard |
|---|---|---|---|---|---|
| Student | `/student/profile/` | `student_profile` | `student_profile_view` | `student/profile.html` | `@require_student` |
| Counselor | `/counselor/profile/` | `counselor_profile` | `counselor_profile_view` | `counselor/profile.html` | `@require_counselor` |
| Receptionist | `/receptionist/profile/` | `receptionist_profile` | `receptionist_profile_view` | `receptionist/profile.html` | `@require_receptionist` |
| Admin | `/admin-panel/profile/` | `admin_profile` | `admin_profile_view` | `users/profile.html` | `@require_admin` |

There is also a shared endpoint:

```text
/password-change/
```

It uses `@login_required` and `templates/authentication/password_change.html`, so any authenticated user can access it. The role-specific profile pages are the primary user-facing flows.

## 7. Complete User Journey

1. The user signs in through `/login/`.
2. Django authenticates the submitted email/username and password.
3. The user is redirected to the dashboard for the role in `Profile.role`.
4. The user opens the relevant profile page.
5. The page displays the password form.
6. The user enters the current password, a new password, and the confirmation.
7. The browser submits a POST request with the form data and CSRF token.
8. The role guard checks authentication, profile existence, active status, and role membership.
9. The view builds `PasswordChangeForm` with `request.user` and `request.POST`.
10. Django validates the current password and new-password rules.
11. If invalid, the same page renders with field errors and nothing is changed.
12. If valid, `password_form.save()` hashes and saves the new password.
13. The role-specific view calls `update_session_auth_hash()` so the session remains valid.
14. The user is redirected back to the profile page and receives a success message.
15. The new password is required on the next login; the old password no longer works.

## 8. Request Journey in Technical Detail

### GET request

For example:

```text
GET /student/profile/
```

The role decorator first checks:

- The user is authenticated.
- The user has a `Profile`.
- The profile is active.
- The profile has the required role.

If the checks pass, the view creates an empty `PasswordChangeForm` and passes it to the template.

### POST request

For example:

```text
POST /student/profile/
```

The request contains:

```text
old_password
new_password1
new_password2
csrfmiddlewaretoken
```

The view validates the form. A valid form calls:

```python
password_form.save()
update_session_auth_hash(request, password_form.user)
```

`save()` updates the Django password hash in `auth_user`; it does not save the raw password. The session update prevents an otherwise unnecessary logout after the password hash changes.

## 9. Password Validation Rules

`config/settings.py` configures these validators:

1. `UserAttributeSimilarityValidator` rejects passwords too similar to user attributes.
2. `MinimumLengthValidator` requires at least 8 characters.
3. `CommonPasswordValidator` rejects common passwords.
4. `NumericPasswordValidator` rejects passwords containing only numbers.

The two new-password fields must also match, and the current password must be correct.

## 10. Result Behavior

### Success

- `auth_user.password` is replaced with a new secure hash.
- The role-specific session remains authenticated.
- A success message is shown.
- The old password fails future login attempts.
- The new password succeeds future login attempts.

### Incorrect current password

- No database change occurs.
- The old-password field displays an error.

### Mismatched confirmation

- No database change occurs.
- The confirmation field displays an error.

### Weak or invalid new password

- No database change occurs.
- Django displays the relevant password-validator message.

### Unauthenticated user

- The user is redirected to login.

### Inactive user

- The role guard logs the user out and redirects to login with a deactivated-account indication.

### Wrong role

- The user is redirected to their own role home and cannot use another role's profile page as a bypass.

## 11. Security Controls

The feature is protected by:

- Django authentication middleware.
- Role-specific access decorators.
- Active-profile checks.
- CSRF middleware and template tokens.
- Current-password verification.
- Django password-strength validators.
- Hashed password storage.
- Session hash refresh after successful role-profile changes.

## 12. Commands for Setup and Verification

Run these from the project root:

```powershell
cd "C:\School works\4yr_firstsem\connectguidance_django"
```

### Create and activate an environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`dj-database-url` is required because `config/settings.py` imports `dj_database_url`.

### Apply migrations

```powershell
python manage.py migrate
```

This creates or updates `auth_user`, sessions, `core_profile`, and other project tables.

### Run Django checks

```powershell
python manage.py check
```

### Seed sample accounts and records

```powershell
python manage.py seed_roles
```

Review `core/management/commands/seed_roles.py` before using seeded accounts outside local development.

### Run all tests

```powershell
python manage.py test --verbosity 1
```

### Run authentication tests

```powershell
python manage.py test tests.test_auth_guards --verbosity 2
```

### Run profile/page tests

```powershell
python manage.py test tests.test_views_http --verbosity 2
```

### Start the development server

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/` after the server starts.

## 13. Manual Test Procedure

Use a temporary test account or record the original password before testing.

For each current role:

1. Start the server.
2. Open `/login/`.
3. Sign in.
4. Open the role profile URL.
5. Enter the current password.
6. Enter a valid new password, such as `NewPassword456!`.
7. Confirm the same new password.
8. Submit the form.
9. Confirm the success message.
10. Confirm the user remains signed in.
11. Log out.
12. Confirm the old password fails.
13. Confirm the new password succeeds.

Test these URLs:

```text
/admin-panel/profile/
/counselor/profile/
/student/profile/
/receptionist/profile/
```

Also test wrong current password, mismatched confirmation, short password, common password, numeric-only password, unauthenticated access, wrong-role access, and inactive-user access.

## 14. Recommended Automated Test

The current tests cover authentication guards, role redirects, and profile-page availability, but there is no dedicated password-change POST test for all four roles.

A complete automated test should:

1. Create an active user for each role.
2. Assign its `Profile.role`.
3. Force-login the user.
4. POST the three password fields to the correct profile URL.
5. Assert a redirect to that profile page.
6. Refresh the user from the database.
7. Assert the old password fails.
8. Assert the new password succeeds.
9. Assert the client session remains authenticated.

Example POST data:

```python
{
    "old_password": "CurrentPassword123!",
    "new_password1": "NewPassword456!",
    "new_password2": "NewPassword456!",
}
```

The test configuration uses in-memory SQLite and a faster password hasher when running under `manage.py test`.

## 15. Known Implementation Detail

The shared `/password-change/` view in `accounts/views.py` calls `form.save()` but does not currently call `update_session_auth_hash()` afterward.

The four role-specific profile views do call `update_session_auth_hash()`, so the normal Admin, Counselor, Student, and Receptionist profile flows preserve the session correctly.

If `/password-change/` is used directly, the password can still be saved, but the session may be invalidated on a later request because its authentication hash is not refreshed. If this shared endpoint is intended to be primary, add the same session-hash update used by the role-specific views.

## 16. Functional Verdict

| Role | Form | Handler | Saves password | Preserves session | Current status |
|---|---:|---:|---:|---:|---|
| Admin | Yes | Yes | Yes | Yes | Implemented |
| Counselor | Yes | Yes | Yes | Yes | Implemented |
| Student | Yes | Yes | Yes | Yes | Implemented |
| Receptionist | Yes | Yes | Yes | Yes | Implemented |
| Supervisor | No | No | No | No | Not implemented |
| Salesman | No | No | No | No | Not implemented |
| Buyer | No | No | No | No | Not implemented |

The source code indicates that password changing is implemented for all four roles currently supported by the application. Runtime testing requires the dependencies in `requirements.txt`; the previous environment was blocked by a missing `dj_database_url` package and a broken `.venv` Python launcher.

## 17. Troubleshooting

### Missing `dj_database_url`

```powershell
python -m pip install -r requirements.txt
```

### Broken `.venv` Python executable

After confirming `.venv` is only the project environment, recreate it:

```powershell
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Redirected to login

Check that the user is authenticated, has a `Profile`, has `is_active=True`, and that sessions and authentication middleware are enabled.

### Current password rejected

Use the password currently assigned to that account. A seeded password may no longer be correct if the account was previously changed.

### New password rejected

Check the eight-character minimum, user-attribute similarity, common-password, numeric-only, and confirmation rules.

### Password changes but the user is logged out

Use the role-specific profile URL. If this occurs through `/password-change/`, add `update_session_auth_hash()` to the shared view.

## 18. Summary

The password-change feature is a protected Django workflow: authenticate the user, verify the old password, validate the new password, securely hash and save it, refresh the session, and report the result. It currently covers Admin, Counselor, Student, and Receptionist. Supervisor, Salesman, and Buyer require additional role and page implementation before they can use this functionality.
