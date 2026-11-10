from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Opportunity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("organization", models.CharField(max_length=180)),
                ("description", models.TextField()),
                ("category", models.CharField(choices=[("scholarship", "Scholarship"), ("internship", "Internship"), ("job", "Job"), ("fellowship", "Fellowship"), ("training", "Training"), ("other", "Other")], max_length=20)),
                ("location", models.CharField(blank=True, default="", max_length=160)),
                ("eligibility_requirements", models.TextField(blank=True)),
                ("required_skills", models.JSONField(blank=True, default=list)),
                ("required_education", models.CharField(blank=True, choices=[("", "Not specified"), ("secondary", "Secondary school"), ("vocational", "Vocational / certificate"), ("undergraduate", "Undergraduate"), ("graduate", "Graduate"), ("postgraduate", "Postgraduate")], max_length=20)),
                ("required_field", models.CharField(blank=True, max_length=160)),
                ("required_experience", models.CharField(blank=True, choices=[("", "Not specified"), ("none", "No experience yet"), ("beginner", "Beginner"), ("intermediate", "Intermediate"), ("experienced", "Experienced")], max_length=20)),
                ("mandatory_requirements", models.JSONField(blank=True, default=list, help_text='Structured rules, e.g. [{"profile_field":"education_level","operator":"in","values":["undergraduate"]}].')),
                ("application_deadline", models.DateField(blank=True, null=True)),
                ("application_url", models.URLField(blank=True, validators=[django.core.validators.URLValidator(schemes=["https", "http"])])),
                ("opportunity_type", models.CharField(blank=True, max_length=80)),
                ("source", models.CharField(blank=True, max_length=200)),
                ("is_demo", models.BooleanField(default=False, help_text="Clearly identifies demonstration records.")),
                ("is_published", models.BooleanField(default=False)),
                ("date_created", models.DateTimeField(auto_now_add=True)),
                ("date_updated", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["application_deadline", "-date_created"]},
        ),
    ]
