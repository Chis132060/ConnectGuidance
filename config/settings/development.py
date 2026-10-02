"""
Development settings for ConnectGuidance
"""

import os
from dotenv import load_dotenv
import dj_database_url
from .base import *

load_dotenv()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-connectguidance-replica-key-2026')

# Debug mode
DEBUG = True

# Allowed hosts
raw_allowed_hosts = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in raw_allowed_hosts.split(',') if h.strip()]
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['*']

# Database configuration: Supabase PostgreSQL with local SQLite fallback
db_url = os.getenv('DATABASE_URL', '').strip()
has_placeholder_pass = any(p in db_url for p in ('your-password', '[YOUR-PASSWORD]', '<YOUR-PASSWORD>'))
if not db_url or db_url.startswith('https://') or has_placeholder_pass:
    db_host = os.getenv('DB_HOST', '').strip()
    db_user = os.getenv('DB_USER', 'postgres').strip()
    db_pass = os.getenv('DB_PASSWORD', '').strip()
    db_name = os.getenv('DB_NAME', 'postgres').strip()
    db_port = os.getenv('DB_PORT', '5432').strip()
    if db_host and db_host != 'your-supabase-host' and db_pass and db_pass not in ('your-password', '[YOUR-PASSWORD]', '<YOUR-PASSWORD>', ''):
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?sslmode=require"
    else:
        db_url = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"

parsed_db = dj_database_url.parse(
    db_url,
    conn_max_age=600 if not db_url.startswith('sqlite') else 0,
    ssl_require='sslmode=require' in db_url,
)

DATABASES = {
    'default': parsed_db
}

# Development email (console output)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
