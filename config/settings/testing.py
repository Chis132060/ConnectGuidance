"""
Testing settings for ConnectGuidance
"""

from .base import *

# Secret key for testing
SECRET_KEY = 'django-insecure-test-key-do-not-use-in-production'

# Debug mode
DEBUG = True

# Allowed hosts
ALLOWED_HOSTS = ['*']

# In-memory database for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations for tests (faster)
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
