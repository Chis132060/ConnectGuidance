# 🔧 Troubleshooting Guide - ConnectGuidance

## HTTP 300 (Multiple Choices) Error

HTTP 300 errors are rare and typically indicate:
- Multiple redirect options available
- Browser caching issues
- Middleware redirect loops
- Proxy/load balancer issues

### Quick Fixes for 300 Errors

#### 1. Clear Browser Cache
```
Chrome/Edge: Ctrl + Shift + Delete
Firefox: Ctrl + Shift + Delete
```
- Select "All time"
- Check "Cached images and files"
- Clear data
- Restart browser

#### 2. Hard Refresh the Page
```
Windows: Ctrl + F5 or Ctrl + Shift + R
Mac: Cmd + Shift + R
```

#### 3. Try Incognito/Private Mode
```
Chrome/Edge: Ctrl + Shift + N
Firefox: Ctrl + Shift + P
```

#### 4. Check Django Settings
Run the diagnostic script:
```powershell
python diagnose_urls.py
```

#### 5. Check for Redirect Loops
Look at browser developer console (F12):
- Check Network tab
- Look for repeated redirects
- Note the URL pattern

### Common Causes in Django

#### APPEND_SLASH Setting
Django automatically redirects URLs without trailing slashes.

Check `config/settings.py`:
```python
APPEND_SLASH = True  # Default Django behavior
```

If having issues, can temporarily disable:
```python
APPEND_SLASH = False
```

#### Middleware Order
Check `config/settings.py` MIDDLEWARE order:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',  # Handles APPEND_SLASH
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

#### Custom Redirects in Views
Check for redirect loops in views:

**Problem:**
```python
def my_view(request):
    if condition:
        return redirect('my_view')  # ❌ Redirects to itself!
```

**Solution:**
```python
def my_view(request):
    if condition:
        return redirect('other_view')  # ✅ Redirects elsewhere
```

### Diagnostic Steps

#### Step 1: Check Server Logs
Start server with verbose output:
```powershell
python manage.py runserver --verbosity 2
```

Look for repeated requests to same URL.

#### Step 2: Test with curl
```powershell
curl.exe -I http://127.0.0.1:8000/
```

Check response headers for:
- Location: header (redirect target)
- Status code

#### Step 3: Check Authentication Redirects
The app redirects based on user role:
```python
student → /student/
counselor → /counselor/
receptionist → /receptionist/
admin → /admin-panel/
```

If you're logged in and accessing wrong URL, it redirects to your role's home.

#### Step 4: Test URLs Directly
Try accessing specific URLs:
```
http://127.0.0.1:8000/              # Landing (public)
http://127.0.0.1:8000/login/        # Login page
http://127.0.0.1:8000/register/     # Register page
http://127.0.0.1:8000/student/      # Student dashboard (auth required)
```

### Known Working URL Patterns

✅ All URLs checked - no duplicates found
✅ No trailing slash conflicts detected
✅ Django configuration valid

### Database Issues

#### Check Database Connection
```powershell
python manage.py check --database default
```

#### Run Migrations
```powershell
python manage.py migrate
```

### Static Files Issues

#### Collect Static Files
```powershell
python manage.py collectstatic --clear
```

### Session Issues

#### Clear Session Data
```powershell
python manage.py clearsessions
```

Or delete session from database:
```python
python manage.py shell
>>> from django.contrib.sessions.models import Session
>>> Session.objects.all().delete()
>>> exit()
```

### Browser-Specific Issues

#### Chrome/Edge
1. Open DevTools (F12)
2. Go to Network tab
3. Check "Disable cache"
4. Reload page
5. Look for 3xx status codes

#### Firefox
1. Open Developer Tools (F12)
2. Go to Network tab
3. Clear browser cache
4. Reload page

### Environment Issues

#### Check .env File
Verify `.env` exists and has correct values:
```env
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

#### Check Virtual Environment
```powershell
# Verify you're in venv
where python
# Should show: C:\School works\4yr_firstsem\connectguidance_django\.venv\Scripts\python.exe

# Verify Django is installed
python -m django --version
```

### Port Conflicts

#### Try Different Port
```powershell
python manage.py runserver 8080
```

Then access: http://127.0.0.1:8080/

### Still Having Issues?

#### Create Debug View
Add to `accounts/views.py`:
```python
def debug_view(request):
    from django.http import JsonResponse
    return JsonResponse({
        'user': str(request.user),
        'authenticated': request.user.is_authenticated,
        'path': request.path,
        'method': request.method,
        'session_key': request.session.session_key,
    })
```

Add to `accounts/urls.py`:
```python
path('debug/', views.debug_view, name='debug'),
```

Access: http://127.0.0.1:8000/debug/

#### Check Django Version
```powershell
python -m django --version
```

Current project uses: Django 5.2.17

#### Reinstall Dependencies
```powershell
pip install --force-reinstall -r requirements.txt
```

---

## Common Error Codes

| Code | Meaning | Common Cause |
|------|---------|-------------|
| 200 | OK | Success |
| 301 | Moved Permanently | APPEND_SLASH redirect |
| 302 | Found (Temporary) | Django redirect() |
| 300 | Multiple Choices | Ambiguous redirect |
| 403 | Forbidden | CSRF or permissions |
| 404 | Not Found | URL doesn't exist |
| 500 | Server Error | Python exception |

---

## Need More Help?

1. Check server output in terminal
2. Check browser console (F12)
3. Run `python diagnose_urls.py`
4. Check `db.sqlite3` exists
5. Verify `.env` file is configured
6. Try different browser
7. Try incognito mode
8. Clear all browser data
9. Restart computer (rare, but helps sometimes)

---

## Report Issue

If problem persists, collect this info:

1. **Error Code:** (e.g., 300)
2. **URL:** (e.g., http://127.0.0.1:8000/student/)
3. **Browser:** (Chrome, Firefox, Edge, Safari)
4. **When:** (On login, specific page, all pages)
5. **Server Output:** (copy from terminal)
6. **Browser Console:** (F12 → Console tab)
7. **Network Tab:** (F12 → Network tab, screenshot)

---

**Generated:** 2026-10-01  
**Project:** ConnectGuidance Django Application
