"""
Root URL Configuration for ConnectGuidance.
Routes to accounts (Authentication & Profiles) and core (Guidance System).
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('core.urls')),
]
