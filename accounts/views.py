from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.forms import EmailAuthenticationForm, ProfileForm, RegistrationForm
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
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data["email"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                )
                Profile.objects.create(user=user, full_name=form.cleaned_data["full_name"])
        except IntegrityError:
            form.add_error("email", "An account with this email already exists.")
        else:
            login(request, user)
            return redirect("accounts:dashboard")
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = EmailAuthenticationForm(request, data=request.POST or None)
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
        profile.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form, "profile": profile})


@login_required
def download_cv(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.cv:
        raise Http404("No CV has been uploaded.")
    return FileResponse(
        profile.cv.open("rb"),
        as_attachment=True,
        filename=profile.cv.name.rsplit("/", 1)[-1],
        content_type="application/octet-stream",
    )


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
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data["email"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                )
                Profile.objects.create(user=user, full_name=form.cleaned_data["full_name"])
        except IntegrityError:
            return JsonResponse({"email": ["An account with this email already exists."]}, status=400)
        login(request, user)
        return JsonResponse({"id": user.pk, "email": user.email}, status=201)


@method_decorator(csrf_protect, name="dispatch")
class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        form = EmailAuthenticationForm(request, data={
            "username": request.data.get("email", ""),
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
