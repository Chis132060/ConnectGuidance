"""
Django settings initialization - loads appropriate settings based on environment
"""

import os

# Determine which settings to load based on DJANGO_ENV
env = os.getenv('DJANGO_ENV', 'development').lower()

if env == 'production':
    from .production import *
elif env == 'testing':
    from .testing import *
else:
    from .development import *
