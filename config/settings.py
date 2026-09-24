"""
Django settings for config project.

GuidanceConnect — Django Replica Master Configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-connectguidance-replica-key-2026')

DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')

raw_allowed_hosts = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in raw_allowed_hosts.split(',') if h.strip()]
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database configuration: Supabase PostgreSQL with local SQLite fallback
db_url = os.getenv('DATABASE_URL', '').strip()
if not db_url or db_url.startswith('https://'):
    db_host = os.getenv('DB_HOST', '').strip()
    db_user = os.getenv('DB_USER', 'postgres').strip()
    db_pass = os.getenv('DB_PASSWORD', '').strip()
    db_name = os.getenv('DB_NAME', 'postgres').strip()
    db_port = os.getenv('DB_PORT', '5432').strip()
    if db_host and db_host != 'your-supabase-host' and db_pass and db_pass != 'your-password':
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


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'role_home'
LOGOUT_REDIRECT_URL = '/'

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Encryption key for case notes
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '')

# AI Chat Configurations
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama3-70b-8192')
CHAT_RATE_LIMIT_MAX = int(os.getenv('CHAT_RATE_LIMIT_MAX', 24))
CHAT_SESSION_GET_MAX = int(os.getenv('CHAT_SESSION_GET_MAX', 60))
CHAT_RATE_LIMIT_WINDOW_MS = int(os.getenv('CHAT_RATE_LIMIT_WINDOW_MS', 900000))
CHAT_SESSION_GET_WINDOW = int(os.getenv('CHAT_SESSION_GET_WINDOW_MS', 900000))
