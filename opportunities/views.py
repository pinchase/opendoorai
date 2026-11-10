from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from applications.models import Application, SavedOpportunity
from matching.ai import ExplanationServiceError, explain_eligibility
from matching.services import score_opportunity
from opportunities.forms import OpportunitySearchForm
from opportunities.models import Opportunity
from profiles.models import Profile


def opportunity_list(request):
    form = OpportunitySearchForm(request.GET or None)
    queryset = Opportunity.objects.filter(is_published=True)
    if form.is_valid():
        search = form.cleaned_data["q"].strip()
        category = form.cleaned_data["category"]
        location = form.cleaned_data["location"].strip()
        sort = form.cleaned_data["sort"]
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(organization__icontains=search)
                | Q(description__icontains=search)
            )
        if category:
            queryset = queryset.filter(category=category)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if sort == "deadline":
            queryset = queryset.order_by(F("application_deadline").asc(nulls_last=True), "-date_created")
    page = Paginator(queryset, 9).get_page(request.GET.get("page"))
    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(
            SavedOpportunity.objects.filter(user=request.user, opportunity__in=page.object_list)
            .values_list("opportunity_id", flat=True)
        )
    return render(request, "opportunities/list.html", {
        "form": form,
        "page": page,
        "saved_ids": saved_ids,
    })


def opportunity_detail(request, pk):
    opportunity = get_object_or_404(Opportunity, pk=pk, is_published=True)
    match = None
    explanation = None
    saved = False
    application = None
    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        match = score_opportunity(profile, opportunity)
        saved = SavedOpportunity.objects.filter(user=request.user, opportunity=opportunity).exists()
        application = Application.objects.filter(user=request.user, opportunity=opportunity).first()
        if request.method == "POST" and "explain" in request.POST:
            try:
                explanation = explain_eligibility(profile, opportunity)
            except ExplanationServiceError as error:
                messages.error(request, str(error))
    return render(request, "opportunities/detail.html", {
        "opportunity": opportunity,
        "match": match,
        "saved": saved,
        "application": application,
        "explanation": explanation,
    })


@login_required
@require_POST
def toggle_saved(request, pk):
    opportunity = get_object_or_404(Opportunity, pk=pk, is_published=True)
    saved, created = SavedOpportunity.objects.get_or_create(user=request.user, opportunity=opportunity)
    if created:
        messages.success(request, "Opportunity saved.")
    else:
        saved.delete()
        messages.success(request, "Opportunity removed from saved items.")
    if request.POST.get("next") == "saved":
        return redirect("saved")
    return redirect("opportunities:detail", pk=pk)


@login_required
@require_POST
def track_application(request, pk):
    opportunity = get_object_or_404(Opportunity, pk=pk, is_published=True)
    application, created = Application.objects.get_or_create(
        user=request.user, opportunity=opportunity, defaults={"status": "interested"}
    )
    if created:
        messages.success(request, "Added to your application tracker.")
    else:
        messages.info(request, "This opportunity is already in your tracker.")
    return redirect("applications")
