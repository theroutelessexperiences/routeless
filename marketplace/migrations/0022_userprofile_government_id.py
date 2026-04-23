"""
Add government_id field to UserProfile for traveler ID uploads during booking.
"""
from django.db import migrations, models
import marketplace.models


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0021_fix_site_domain"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="government_id",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="govt_ids/",
                validators=[marketplace.models.validate_image_file],
            ),
        ),
    ]
