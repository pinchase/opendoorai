from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("opportunities", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Application",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("interested", "Interested"), ("preparing", "Preparing"), ("applied", "Applied"), ("interview", "Interview"), ("accepted", "Accepted"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn")], default="interested", max_length=16)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("opportunity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="applications", to="opportunities.opportunity")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="applications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="SavedOpportunity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("opportunity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_by", to="opportunities.opportunity")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_opportunities", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="application",
            constraint=models.UniqueConstraint(fields=("user", "opportunity"), name="unique_application_per_user"),
        ),
        migrations.AddConstraint(
            model_name="savedopportunity",
            constraint=models.UniqueConstraint(fields=("user", "opportunity"), name="unique_saved_opportunity_per_user"),
        ),
    ]
