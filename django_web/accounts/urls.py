from django.urls import path

from . import views


urlpatterns = [
    path("", views.language_select, name="language_select"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("password-reset/", views.password_reset_by_name, name="password_reset"),
]
