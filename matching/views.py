from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from matching.services import rank_opportunities
from opportunities.models import Opportunity
from profiles.models import Profile


@login_required
def matches(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    results = rank_opportunities(
        profile,
        Opportunity.objects.filter(is_published=True).order_by("-date_created"),
    )
    return render(request, "matching/list.html", {"results": results})
