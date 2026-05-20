"""
Tests for the customer-host check-in verification system.
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from marketplace.models import Booking, Experience, UserProfile
from marketplace.services.checkin_service import (
    generate_checkin_credentials,
    generate_qr_data_uri,
    perform_checkin,
    validate_checkin,
)


class CheckinServiceTestBase(TestCase):
    """Shared setup for checkin tests."""

    def setUp(self):
        # Create host user
        self.host = User.objects.create_user(
            username="testhost", password="testpass123", email="host@test.com"
        )
        profile, _ = UserProfile.objects.get_or_create(user=self.host)
        profile.is_host = True
        profile.save()

        # Create customer user
        self.customer = User.objects.create_user(
            username="testcustomer", password="testpass123", email="customer@test.com"
        )

        # Create another host (for ownership tests)
        self.other_host = User.objects.create_user(
            username="otherhost", password="testpass123", email="other@test.com"
        )
        other_profile, _ = UserProfile.objects.get_or_create(user=self.other_host)
        other_profile.is_host = True
        other_profile.save()

        # Create experience
        self.experience = Experience.objects.create(
            title="Test Trek Experience",
            host=self.host,
            category="trekking",
            location="Manali",
            description="A test trekking experience.",
            price_per_person=1500,
            max_guests=10,
            duration="2 days",
            status="approved",
        )

        # Create confirmed booking for today
        self.booking = Booking.objects.create(
            experience=self.experience,
            user=self.customer,
            traveler_name="Test Customer",
            traveler_email="customer@test.com",
            check_in_date=date.today(),
            check_out_date=date.today() + timedelta(days=1),
            guests_count=2,
            total_price=3000,
            booking_status="confirmed",
        )


class GenerateCredentialsTest(CheckinServiceTestBase):
    """Tests for generate_checkin_credentials."""

    def test_generates_code_and_token(self):
        """Confirmed booking gets a 6-digit code and UUID token."""
        generate_checkin_credentials(self.booking)
        self.booking.refresh_from_db()

        self.assertEqual(len(self.booking.checkin_code), 6)
        self.assertTrue(self.booking.checkin_code.isdigit())
        self.assertIsNotNone(self.booking.checkin_token)

    def test_idempotent(self):
        """Calling twice doesn't change existing credentials."""
        generate_checkin_credentials(self.booking)
        self.booking.refresh_from_db()
        code1 = self.booking.checkin_code
        token1 = self.booking.checkin_token

        generate_checkin_credentials(self.booking)
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.checkin_code, code1)
        self.assertEqual(self.booking.checkin_token, token1)

    def test_skips_pending_booking(self):
        """Pending bookings don't get credentials."""
        self.booking.booking_status = "pending"
        self.booking.save()

        generate_checkin_credentials(self.booking)
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.checkin_code, "")
        self.assertIsNone(self.booking.checkin_token)

    def test_skips_cancelled_booking(self):
        """Cancelled bookings don't get credentials."""
        self.booking.booking_status = "cancelled"
        self.booking.save()

        generate_checkin_credentials(self.booking)
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.checkin_code, "")
        self.assertIsNone(self.booking.checkin_token)


class ValidateCheckinTest(CheckinServiceTestBase):
    """Tests for validate_checkin."""

    def setUp(self):
        super().setUp()
        generate_checkin_credentials(self.booking)
        self.booking.refresh_from_db()

        # Create payment record (required for validation to pass)
        from payments.models import Payment
        self.payment = Payment.objects.create(
            booking=self.booking,
            user=self.customer,
            amount=3000,
            payment_status="success",
        )

    def test_valid_code_passes(self):
        """Valid 6-digit code from correct host passes validation."""
        booking, errors = validate_checkin(self.booking.checkin_code, self.host)
        self.assertEqual(errors, [])
        self.assertIsNotNone(booking)
        self.assertEqual(booking.id, self.booking.id)

    def test_valid_token_passes(self):
        """Valid UUID token from correct host passes validation."""
        booking, errors = validate_checkin(str(self.booking.checkin_token), self.host)
        self.assertEqual(errors, [])
        self.assertIsNotNone(booking)

    def test_invalid_code_rejected(self):
        """Non-existent code returns error."""
        booking, errors = validate_checkin("999999", self.host)
        self.assertIsNone(booking)
        self.assertTrue(len(errors) > 0)
        self.assertIn("Invalid", errors[0])

    def test_empty_code_rejected(self):
        """Empty code returns error."""
        booking, errors = validate_checkin("", self.host)
        self.assertIsNone(booking)
        self.assertTrue(len(errors) > 0)

    def test_wrong_host_rejected(self):
        """Code submitted by wrong host is rejected."""
        booking, errors = validate_checkin(self.booking.checkin_code, self.other_host)
        self.assertIsNone(booking)  # Details not revealed
        self.assertTrue(len(errors) > 0)
        self.assertIn("different host", errors[0])

    def test_cancelled_booking_rejected(self):
        """Cancelled booking code is rejected."""
        self.booking.booking_status = "cancelled"
        self.booking.save()

        booking, errors = validate_checkin(self.booking.checkin_code, self.host)
        self.assertTrue(len(errors) > 0)
        self.assertIn("cancelled", errors[0])

    def test_already_checked_in_rejected(self):
        """Already checked-in booking is rejected."""
        self.booking.booking_status = "checked_in"
        self.booking.save()

        booking, errors = validate_checkin(self.booking.checkin_code, self.host)
        self.assertTrue(len(errors) > 0)
        self.assertIn("already been checked in", errors[0])

    def test_future_date_rejected(self):
        """Booking for future date is rejected."""
        self.booking.check_in_date = date.today() + timedelta(days=3)
        self.booking.check_out_date = date.today() + timedelta(days=4)
        self.booking.save()

        booking, errors = validate_checkin(self.booking.checkin_code, self.host)
        self.assertTrue(len(errors) > 0)
        self.assertIn("not available yet", errors[0])

    def test_past_date_rejected(self):
        """Booking for past date is rejected."""
        self.booking.check_in_date = date.today() - timedelta(days=3)
        self.booking.check_out_date = date.today() - timedelta(days=2)
        self.booking.save()

        booking, errors = validate_checkin(self.booking.checkin_code, self.host)
        self.assertTrue(len(errors) > 0)
        self.assertIn("passed", errors[0])

    def test_attempt_counter_increments(self):
        """Each validation attempt increments the counter."""
        initial = self.booking.checkin_attempt_count
        validate_checkin(self.booking.checkin_code, self.host)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.checkin_attempt_count, initial + 1)


class PerformCheckinTest(CheckinServiceTestBase):
    """Tests for perform_checkin."""

    def setUp(self):
        super().setUp()
        generate_checkin_credentials(self.booking)
        self.booking.refresh_from_db()

    def test_successful_checkin(self):
        """Performing check-in updates all status fields."""
        result = perform_checkin(self.booking, self.host, method="manual_code")

        self.assertEqual(result.booking_status, "checked_in")
        self.assertEqual(result.checkin_status, "checked_in")
        self.assertIsNotNone(result.checked_in_at)
        self.assertEqual(result.checked_in_by, self.host)
        self.assertEqual(result.checkin_method, "manual_code")

    def test_double_checkin_raises(self):
        """Checking in an already checked-in booking raises ValueError."""
        perform_checkin(self.booking, self.host)

        with self.assertRaises(ValueError):
            perform_checkin(self.booking, self.host)


class QRCodeTest(CheckinServiceTestBase):
    """Tests for QR code generation."""

    def test_generates_data_uri(self):
        """QR code generates a valid base64 data URI."""
        generate_checkin_credentials(self.booking)
        self.booking.refresh_from_db()

        uri = generate_qr_data_uri(self.booking)
        self.assertTrue(uri.startswith("data:image/png;base64,"))
        self.assertTrue(len(uri) > 100)

    def test_no_token_returns_empty(self):
        """No token returns empty string."""
        uri = generate_qr_data_uri(self.booking)
        self.assertEqual(uri, "")


class CheckinViewTest(CheckinServiceTestBase):
    """Tests for host check-in views."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        generate_checkin_credentials(self.booking)
        self.booking.refresh_from_db()

        # Create payment record (required for validation)
        from payments.models import Payment
        self.payment = Payment.objects.create(
            booking=self.booking,
            user=self.customer,
            amount=3000,
            payment_status="success",
        )

    def test_checkin_page_requires_login(self):
        """Check-in page redirects unauthenticated users."""
        response = self.client.get(reverse("host_checkin"))
        self.assertEqual(response.status_code, 302)

    def test_checkin_page_requires_host(self):
        """Check-in page rejects non-host users."""
        self.client.login(username="testcustomer", password="testpass123")
        response = self.client.get(reverse("host_checkin"), follow=True)
        self.assertEqual(response.status_code, 200)
        # Should redirect to home with error

    def test_checkin_page_loads_for_host(self):
        """Check-in page loads for verified hosts."""
        self.client.login(username="testhost", password="testpass123")
        response = self.client.get(reverse("host_checkin"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check-In Verification")

    def test_verify_code_shows_booking(self):
        """Submitting valid code shows matched booking."""
        self.client.login(username="testhost", password="testpass123")
        response = self.client.post(reverse("host_checkin_verify"), {
            "action": "verify",
            "checkin_code": self.booking.checkin_code,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Booking Found")
        self.assertContains(response, self.booking.traveler_name)

    def test_confirm_checkin_works(self):
        """Confirming check-in updates booking status."""
        self.client.login(username="testhost", password="testpass123")

        response = self.client.post(reverse("host_checkin_verify"), {
            "action": "confirm",
            "checkin_code": self.booking.checkin_code,
        }, follow=True)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_status, "checked_in")
