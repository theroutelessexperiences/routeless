"""
Custom allauth adapter for The Routeless.

Routes account-related emails (email verification, password reset, etc.)
through the "support" sender address (support@therouteless.com) instead
of the global DEFAULT_FROM_EMAIL.
"""
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class RoutelessAccountAdapter(DefaultAccountAdapter):
    """Override the default allauth sender to use the support address."""

    def get_from_email(self):
        emails_map = getattr(settings, "ROUTELESS_EMAILS", {})
        return emails_map.get("support", settings.DEFAULT_FROM_EMAIL)
