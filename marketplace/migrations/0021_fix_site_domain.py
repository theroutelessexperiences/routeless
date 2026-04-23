"""
Data migration to ensure the Django Sites framework entry for SITE_ID=1
uses the production domain 'therouteless.com' rather than 'localhost'.
This fixes password-reset emails containing localhost URLs.
"""
from django.db import migrations


def set_site_domain(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    site, created = Site.objects.get_or_create(
        id=1,
        defaults={"domain": "therouteless.com", "name": "The Routeless"},
    )
    if not created:
        site.domain = "therouteless.com"
        site.name = "The Routeless"
        site.save()


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0020_alter_conversation_options_alter_message_options_and_more"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(set_site_domain, migrations.RunPython.noop),
    ]
