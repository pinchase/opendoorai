from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from accounts import views

app_name = "accounts"
urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("accounts/register/", views.register, name="register"),
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("accounts/verify/<uidb64>/<token>/", views.verify_email, name="verify-email"),
    path("accounts/verification-sent/", views.verification_sent, name="verification-sent"),
    path("accounts/resend-verification/", views.resend_verification, name="resend-verification"),
    path(
        "accounts/password-reset/",
        views.RateLimitedPasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.txt",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password-reset-done"),
        ),
        name="password-reset",
    ),
    path(
        "accounts/password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html",
        ),
        name="password-reset-done",
    ),
    path(
        "accounts/password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password-reset-complete"),
        ),
        name="password-reset-confirm",
    ),
    path(
        "accounts/password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html",
        ),
        name="password-reset-complete",
    ),
    path("profile/", views.profile_view, name="profile"),
    path("profile/cv/", views.download_cv, name="cv-download"),
    path("settings/", views.settings_view, name="settings"),
]
