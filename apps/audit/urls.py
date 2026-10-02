"""
apps/audit/urls.py — Audit log URL routing
"""

from django.urls import path
from . import views

urlpatterns = [
    path('admin-panel/audit/', views.admin_audit_logs_view, name='admin_audit'),
]
