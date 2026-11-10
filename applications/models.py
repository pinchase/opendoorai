from django.conf import settings
from django.db import models

from opportunities.models import Opportunity


class SavedOpportunity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_opportunities")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "opportunity"], name="unique_saved_opportunity_per_user")
        ]
        ordering = ["-created_at"]


class Application(models.Model):
    STATUS_CHOICES = [
        ("interested", "Interested"),
        ("preparing", "Preparing"),
        ("applied", "Applied"),
        ("interview", "Interview"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="interested")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "opportunity"], name="unique_application_per_user")
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} - {self.opportunity} ({self.get_status_display()})"
