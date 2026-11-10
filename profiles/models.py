from pathlib import PurePosixPath
from uuid import uuid4

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


def profile_cv_upload_to(instance, filename):
    safe_name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    extension = PurePosixPath(safe_name).suffix.lower()
    return f"cvs/{instance.user_id}/{uuid4().hex}{extension}"


class Profile(models.Model):
    EDUCATION_CHOICES = [
        ("", "Not specified"),
        ("secondary", "Secondary school"),
        ("vocational", "Vocational / certificate"),
        ("undergraduate", "Undergraduate"),
        ("graduate", "Graduate"),
        ("postgraduate", "Postgraduate"),
    ]
    EXPERIENCE_CHOICES = [
        ("", "Not specified"),
        ("none", "No experience yet"),
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("experienced", "Experienced"),
    ]
    CATEGORY_CHOICES = [
        ("scholarship", "Scholarship"),
        ("internship", "Internship"),
        ("job", "Job"),
        ("fellowship", "Fellowship"),
        ("training", "Training"),
        ("other", "Other"),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=120, blank=True)
    education_level = models.CharField(max_length=20, choices=EDUCATION_CHOICES, blank=True)
    institution = models.CharField(max_length=160, blank=True)
    field_of_study = models.CharField(max_length=160, blank=True)
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    skills = models.TextField(blank=True, help_text="Separate skills with commas or new lines.")
    interests = models.TextField(blank=True)
    career_goals = models.TextField(blank=True)
    preferred_categories = models.JSONField(default=list, blank=True)
    preferred_location = models.CharField(max_length=120, blank=True)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, blank=True)
    cv = models.FileField(
        upload_to=profile_cv_upload_to,
        blank=True,
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.email or self.user.get_username()

    @property
    def completion_percent(self):
        fields = [
            self.full_name,
            self.education_level,
            self.institution,
            self.field_of_study,
            self.graduation_year,
            self.skills,
            self.interests,
            self.career_goals,
            self.preferred_categories,
            self.preferred_location,
            self.experience_level,
        ]
        complete = sum(bool(value) for value in fields)
        return round(complete / len(fields) * 100)

    @property
    def normalized_skills(self):
        return {
            value.strip().casefold()
            for value in self.skills.replace("\n", ",").split(",")
            if value.strip()
        }

    @property
    def is_graduation_year_current_or_future(self):
        return bool(self.graduation_year and self.graduation_year >= timezone.now().year)
