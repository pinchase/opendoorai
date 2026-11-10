import django.core.validators
import profiles.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("profiles", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="profile",
            name="cv",
            field=models.FileField(
                blank=True,
                upload_to=profiles.models.profile_cv_upload_to,
                validators=[
                    django.core.validators.FileExtensionValidator(["pdf", "doc", "docx"])
                ],
            ),
        ),
    ]
