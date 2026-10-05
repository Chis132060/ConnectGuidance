from django.urls import path
from accounts import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('home/', views.role_home_view, name='role_home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('password-change/', views.password_change_view, name='password_change'),
]
