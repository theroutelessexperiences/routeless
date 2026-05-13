"""
Tests for the purpose-based email sender routing system.

Validates that get_sender_email() and send_routeless_email() correctly
resolve sender addresses and construct emails.
"""
from django.test import TestCase, override_settings
from django.core import mail

from marketplace.services.emails import get_sender_email, send_routeless_email


TEST_ROUTELESS_EMAILS = {
    "marketing": "explore@therouteless.com",
    "booking": "tribe@therouteless.com",
    "admin": "admin@therouteless.com",
    "general": "hello@therouteless.com",
    "partners": "partners@therouteless.com",
    "support": "support@therouteless.com",
    "ankit": "ankitsharma@therouteless.com",
    "harshit": "harshitsachan@therouteless.com",
}


@override_settings(
    ROUTELESS_EMAILS=TEST_ROUTELESS_EMAILS,
    DEFAULT_FROM_EMAIL="hello@therouteless.com",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class GetSenderEmailTests(TestCase):
    """Test that get_sender_email() returns the correct address for each purpose."""

    def test_booking_sender(self):
        self.assertEqual(get_sender_email("booking"), "tribe@therouteless.com")

    def test_support_sender(self):
        self.assertEqual(get_sender_email("support"), "support@therouteless.com")

    def test_partners_sender(self):
        self.assertEqual(get_sender_email("partners"), "partners@therouteless.com")

    def test_general_sender(self):
        self.assertEqual(get_sender_email("general"), "hello@therouteless.com")

    def test_marketing_sender(self):
        self.assertEqual(get_sender_email("marketing"), "explore@therouteless.com")

    def test_admin_sender(self):
        self.assertEqual(get_sender_email("admin"), "admin@therouteless.com")

    def test_ankit_sender(self):
        self.assertEqual(get_sender_email("ankit"), "ankitsharma@therouteless.com")

    def test_harshit_sender(self):
        self.assertEqual(get_sender_email("harshit"), "harshitsachan@therouteless.com")

    def test_unknown_purpose_fallback(self):
        """Unknown purposes should fall back to DEFAULT_FROM_EMAIL."""
        self.assertEqual(get_sender_email("unknown_purpose"), "hello@therouteless.com")

    def test_empty_purpose_fallback(self):
        self.assertEqual(get_sender_email(""), "hello@therouteless.com")


@override_settings(
    ROUTELESS_EMAILS=TEST_ROUTELESS_EMAILS,
    DEFAULT_FROM_EMAIL="hello@therouteless.com",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class SendRoutelessEmailTests(TestCase):
    """Test that send_routeless_email() constructs emails with correct senders."""

    def test_booking_email_uses_tribe_sender(self):
        send_routeless_email(
            purpose="booking",
            subject="Test Booking",
            to=["traveler@example.com"],
            plain_body="Your booking is confirmed.",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "tribe@therouteless.com")
        self.assertEqual(mail.outbox[0].subject, "Test Booking")

    def test_support_email_uses_support_sender(self):
        send_routeless_email(
            purpose="support",
            subject="OTP Code",
            to=["user@example.com"],
            plain_body="Your OTP is 123456.",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "support@therouteless.com")

    def test_marketing_email_uses_explore_sender(self):
        send_routeless_email(
            purpose="marketing",
            subject="New Adventures",
            to=["subscriber@example.com"],
            plain_body="Check out our new listings!",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "explore@therouteless.com")

    def test_partners_email_uses_partners_sender(self):
        send_routeless_email(
            purpose="partners",
            subject="Partnership Opportunity",
            to=["vendor@example.com"],
            plain_body="Let's partner up!",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "partners@therouteless.com")

    def test_general_email_uses_hello_sender(self):
        send_routeless_email(
            purpose="general",
            subject="Welcome",
            to=["guest@example.com"],
            plain_body="Welcome to The Routeless.",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "hello@therouteless.com")

    def test_unknown_purpose_uses_default_sender(self):
        send_routeless_email(
            purpose="nonexistent",
            subject="Fallback Test",
            to=["test@example.com"],
            plain_body="Testing fallback.",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "hello@therouteless.com")

    def test_reply_to_defaults_to_sender(self):
        send_routeless_email(
            purpose="booking",
            subject="Reply-To Test",
            to=["traveler@example.com"],
            plain_body="Test reply-to.",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].reply_to, ["tribe@therouteless.com"])

    def test_custom_reply_to(self):
        send_routeless_email(
            purpose="booking",
            subject="Custom Reply-To",
            to=["traveler@example.com"],
            plain_body="Test custom reply-to.",
            reply_to=["support@therouteless.com"],
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].reply_to, ["support@therouteless.com"])

    def test_html_template_email(self):
        """HTML template emails should have both text and HTML parts."""
        send_routeless_email(
            purpose="booking",
            subject="HTML Test",
            to=["traveler@example.com"],
            template_name="emails/booking_confirmation.html",
            context={
                "traveler_name": "Test User",
                "experience": type("Exp", (), {"title": "Test Experience"})(),
                "booking": type("Bk", (), {
                    "check_in_date": "2026-06-01",
                    "check_out_date": "2026-06-03",
                    "guests_count": 2,
                    "total_price": 5000,
                })(),
            },
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "tribe@therouteless.com")
        # Should have HTML alternative attached
        self.assertTrue(len(mail.outbox[0].alternatives) > 0)
        self.assertEqual(mail.outbox[0].alternatives[0][1], "text/html")
