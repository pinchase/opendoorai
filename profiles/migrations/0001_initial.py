import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(blank=True, max_length=120)),
                ("education_level", models.CharField(blank=True, choices=[("", "Not specified"), ("secondary", "Secondary school"), ("vocational", "Vocational / certificate"), ("undergraduate", "Undergraduate"), ("graduate", "Graduate"), ("postgraduate", "Postgraduate")], max_length=20)),
                ("institution", models.CharField(blank=True, max_length=160)),
                ("field_of_study", models.CharField(blank=True, max_length=160)),
                ("graduation_year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("skills", models.TextField(blank=True, help_text="Separate skills with commas or new lines.")),
                ("interests", models.TextField(blank=True)),
                ("career_goals", models.TextField(blank=True)),
                ("preferred_categories", models.JSONField(blank=True, default=list)),
                ("preferred_location", models.CharField(blank=True, max_length=120)),
                ("experience_level", models.CharField(blank=True, choices=[("", "Not specified"), ("none", "No experience yet"), ("beginner", "Beginner"), ("intermediate", "Intermediate"), ("experienced", "Experienced")], max_length=20)),
                ("cv", models.FileField(blank=True, upload_to="cvs/", validators=[django.core.validators.FileExtensionValidator(["pdf", "doc", "docx"])])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
