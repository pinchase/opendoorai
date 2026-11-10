from django import forms

from opportunities.models import Opportunity


class OpportunitySearchForm(forms.Form):
    q = forms.CharField(required=False, label="Search opportunities")
    category = forms.ChoiceField(
        required=False,
        choices=[("", "All categories")] + Opportunity.CATEGORY_CHOICES,
    )
    location = forms.CharField(required=False)
    sort = forms.ChoiceField(
        required=False,
        choices=[("recent", "Recently added"), ("deadline", "Deadline: soonest")],
    )
