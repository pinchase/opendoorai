from django.contrib import admin

from opportunities.models import Opportunity


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "category", "location", "application_deadline", "source", "is_verified", "is_demo", "is_published")
    list_filter = ("category", "is_published", "is_verified", "is_demo", "source_managed")
    search_fields = ("title", "organization", "description", "location")
    readonly_fields = ("date_created", "date_updated", "source_collected_at")
