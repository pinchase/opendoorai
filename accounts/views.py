from django.contrib import messages
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetView
from django.http import FileResponse, Http404, JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from smtplib import SMTPException

from accounts.emails import send_verification_email
from accounts.forms import EmailAuthenticationForm, ProfileForm, RegistrationForm, ResendVerificationForm
from accounts.rate_limits import allow_sensitive_action
from applications.models import Application, SavedOpportunity
from opportunities.models import Opportunity
from profiles.models import Profile

User = get_user_model()


@ensure_csrf_cookie
def home(request):
    recent_opportunities = Opportunity.objects.filter(is_published=True).order_by("-date_created")[:3]
    return render(request, "home.html", {"recent_opportunities": recent_opportunities})


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not allow_sensitive_action("registration", remote_addr=request.META.get("REMOTE_ADDR", "")):
            form.add_error(None, "Too many registration attempts. Please wait and try again.")
            return render(request, "accounts/register.html", {"form": form}, status=429)
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data["email"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                    is_active=not settings.EMAIL_ENABLED,
                )
                Profile.objects.create(user=user, full_name=form.cleaned_data["full_name"])
        except IntegrityError:
            form.add_error("email", "An account with this email already exists.")
        else:
            if settings.EMAIL_ENABLED:
                try:
                    send_verification_email(request, user)
                except (SMTPException, OSError):
                    messages.error(
                        request,
                        "Your account was created, but the verification email could not be sent. "
                        "Use the resend link to try again.",
                    )
                    return redirect("accounts:verification-sent")
                return redirect("accounts:verification-sent")
            login(request, user)
            return redirect("accounts:dashboard")
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = EmailAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and not allow_sensitive_action(
        "login",
        email=request.POST.get("username", ""),
        remote_addr=request.META.get("REMOTE_ADDR", ""),
    ):
        messages.error(request, "Too many sign-in attempts. Please wait and try again.")
        return render(request, "accounts/login.html", {"form": form}, status=429)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        destination = request.POST.get("next") or request.GET.get("next")
        if destination and url_has_allowed_host_and_scheme(
            destination,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(destination)
        return redirect("accounts:dashboard")
    return render(request, "accounts/login.html", {"form": form})


def verification_sent(request):
    return render(request, "accounts/verification_sent.html")


def verify_email(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    valid_token = bool(
        settings.EMAIL_ENABLED
        and user
        and not user.is_active
        and default_token_generator.check_token(user, token)
    )
    if valid_token:
        user.is_active = True
        user.save(update_fields=["is_active"])
    return render(request, "accounts/verify_email.html", {"verified": valid_token})


def resend_verification(request):
    form = ResendVerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        allowed = allow_sensitive_action(
            "verification-email",
            email=email,
            remote_addr=request.META.get("REMOTE_ADDR", ""),
        )
        if settings.EMAIL_ENABLED and allowed:
            user = User.objects.filter(email__iexact=email, is_active=False).first()
            if user:
                try:
                    send_verification_email(request, user)
                except (SMTPException, OSError):
                    messages.error(request, "The verification email could not be sent. Please try again later.")
                    return render(request, "accounts/resend_verification.html", {"form": form}, status=503)
        messages.success(
            request,
            "If the address belongs to an unverified account, a verification link will be sent.",
        )
        return redirect("accounts:verification-sent")
    return render(request, "accounts/resend_verification.html", {"form": form})


class RateLimitedPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        allowed = allow_sensitive_action(
            "password-reset",
            email=form.cleaned_data["email"],
            remote_addr=self.request.META.get("REMOTE_ADDR", ""),
        )
        if not settings.EMAIL_ENABLED or not allowed:
            return redirect(self.get_success_url())
        return super().form_valid(form)


@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:home")


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        profile = form.save(commit=False)
        profile.user = request.user
        if request.POST.get("remove_cv") == "on" and not request.FILES.get("cv"):
            profile.cv.delete(save=False)
            profile.cv = ""
        profile.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form, "profile": profile})


@login_required
def download_cv(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.cv:
        raise Http404("No CV has been uploaded.")
    response = FileResponse(
        profile.cv.open("rb"),
        as_attachment=True,
        filename=profile.cv.name.rsplit("/", 1)[-1],
        content_type="application/octet-stream",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def settings_view(request):
    return render(request, "accounts/settings.html")


@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    recent_opportunities = Opportunity.objects.filter(is_published=True).order_by("-date_created")[:4]
    saved = SavedOpportunity.objects.filter(user=request.user).select_related("opportunity")[:3]
    saved_count = SavedOpportunity.objects.filter(user=request.user).count()
    applications = Application.objects.filter(user=request.user).select_related("opportunity")
    upcoming = Opportunity.objects.filter(
        is_published=True,
        application_deadline__gte=timezone.localdate(),
    ).order_by("application_deadline")[:3]
    from matching.services import rank_opportunities

    recommended = rank_opportunities(
        profile, Opportunity.objects.filter(is_published=True)
    )[:3]
    return render(request, "accounts/dashboard.html", {
        "profile": profile,
        "recent_opportunities": recent_opportunities,
        "saved_opportunities": saved,
        "saved_count": saved_count,
        "applications": applications,
        "upcoming_deadlines": upcoming,
        "recommended": recommended,
    })


@method_decorator(csrf_protect, name="dispatch")
class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        form = RegistrationForm(request.data)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
        if not allow_sensitive_action(
            "registration", remote_addr=request.META.get("REMOTE_ADDR", "")
        ):
            return JsonResponse({"detail": "Too many registration attempts."}, status=429)
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data["email"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                    is_active=not settings.EMAIL_ENABLED,
                )
                Profile.objects.create(user=user, full_name=form.cleaned_data["full_name"])
        except IntegrityError:
            return JsonResponse({"email": ["An account with this email already exists."]}, status=400)
        if settings.EMAIL_ENABLED:
            try:
                send_verification_email(request, user)
            except (SMTPException, OSError):
                return JsonResponse(
                    {"detail": "Account created, but the verification email could not be sent. Try resending."},
                    status=503,
                )
            return JsonResponse({"detail": "Check your email to verify your account."}, status=202)
        login(request, user)
        return JsonResponse({"id": user.pk, "email": user.email}, status=201)


@method_decorator(csrf_protect, name="dispatch")
class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get("email", "")
        if not allow_sensitive_action(
            "login",
            email=email if isinstance(email, str) else "",
            remote_addr=request.META.get("REMOTE_ADDR", ""),
        ):
            return JsonResponse({"detail": "Too many sign-in attempts."}, status=429)
        form = EmailAuthenticationForm(request, data={
            "username": email,
            "password": request.data.get("password", ""),
        })
        if not form.is_valid():
            return JsonResponse({"detail": "Invalid email or password."}, status=400)
        login(request, form.get_user())
        return JsonResponse({"id": form.get_user().pk, "email": form.get_user().email})


class LogoutAPIView(APIView):
    def post(self, request):
        logout(request)
        return JsonResponse({"detail": "Logged out."})
