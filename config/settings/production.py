"""
Production settings for ConnectGuidance
"""

import os
from dotenv import load_dotenv
import dj_database_url
from .base import *

load_dotenv()

# SECURITY WARNING: Secret key must be set in production
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('DJANGO_SECRET_KEY must be set in production')

# Debug MUST be False in production
DEBUG = False

# Allowed hosts (required in production)
raw_allowed_hosts = os.getenv('DJANGO_ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in raw_allowed_hosts.split(',') if h.strip()]
if not ALLOWED_HOSTS:
    raise ValueError('DJANGO_ALLOWED_HOSTS must be set in production')

# Database configuration: PostgreSQL required in production
db_url = os.getenv('DATABASE_URL', '').strip()
if not db_url or 'sqlite' in db_url.lower():
    raise ValueError('DATABASE_URL must be set to PostgreSQL in production')

parsed_db = dj_database_url.parse(
    db_url,
    conn_max_age=600,
    ssl_require='sslmode=require' in db_url,
)

DATABASES = {
    'default': parsed_db
}

# Security settings
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Production email
# Configure with your email backend (SMTP, SendGrid, etc.)
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
