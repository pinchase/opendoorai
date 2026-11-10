from django.urls import path

from accounts import views

app_name = "accounts"
urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("accounts/register/", views.register, name="register"),
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/cv/", views.download_cv, name="cv-download"),
    path("settings/", views.settings_view, name="settings"),
]
