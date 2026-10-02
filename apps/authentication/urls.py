"""
apps/authentication/urls.py — Authentication URL routing
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('password_change/', views.password_change_view, name='password_change'),
    path('role-home/', views.role_home_view, name='role_home'),
]
