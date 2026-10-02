"""
apps/users/urls.py — URL routing for user management features.
"""

from django.urls import path
from apps.users import views

urlpatterns = [
    path('users/', views.admin_users_view, name='admin_users'),
    path('profile/', views.admin_profile_view, name='admin_profile'),
]
