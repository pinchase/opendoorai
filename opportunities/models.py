from django.core.validators import URLValidator
from django.db import models
from django.db.models import Q


class Opportunity(models.Model):
    CATEGORY_CHOICES = [
        ("scholarship", "Scholarship"),
        ("internship", "Internship"),
        ("job", "Job"),
        ("fellowship", "Fellowship"),
        ("training", "Training"),
        ("other", "Other"),
    ]
    EXPERIENCE_CHOICES = [
        ("", "Not specified"),
        ("none", "No experience yet"),
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("experienced", "Experienced"),
    ]
    title = models.CharField(max_length=180)
    organization = models.CharField(max_length=180)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    location = models.CharField(max_length=160, blank=True, default="")
    eligibility_requirements = models.TextField(blank=True)
    required_skills = models.JSONField(default=list, blank=True)
    required_education = models.CharField(max_length=20, choices=[
        ("", "Not specified"),
        ("secondary", "Secondary school"),
        ("vocational", "Vocational / certificate"),
        ("undergraduate", "Undergraduate"),
        ("graduate", "Graduate"),
        ("postgraduate", "Postgraduate"),
    ], blank=True)
    required_field = models.CharField(max_length=160, blank=True)
    required_experience = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, blank=True)
    mandatory_requirements = models.JSONField(
        default=list,
        blank=True,
        help_text="Structured rules, e.g. [{\"profile_field\":\"education_level\",\"operator\":\"in\",\"values\":[\"undergraduate\"]}].",
    )
    application_deadline = models.DateField(null=True, blank=True)
    application_url = models.URLField(blank=True, validators=[URLValidator(schemes=["https", "http"])])
    opportunity_type = models.CharField(max_length=80, blank=True)
    source = models.CharField(max_length=200, blank=True)
    source_identifier = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True, validators=[URLValidator(schemes=["https"])])
    source_collected_at = models.DateTimeField(null=True, blank=True)
    source_managed = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False, help_text="Clearly identifies demonstration records.")
    is_published = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["application_deadline", "-date_created"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_identifier"],
                condition=~Q(source_identifier=""),
                name="unique_source_opportunity_identifier",
            )
        ]

    def __str__(self):
        return self.title
