"""
apps/analytics/urls.py — URL routing for analytics and reporting features.
"""

from django.urls import path
from apps.analytics import views

urlpatterns = [
    path('', views.admin_overview_view, name='admin_overview'),
    path('reports/', views.admin_reports_view, name='admin_reports'),
]
