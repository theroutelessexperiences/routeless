"""
Unit tests for invoice creation service.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from payments.invoice_service import (
    _get_financial_year,
    generate_invoice_number,
    create_invoice_for_booking,
    create_vendor_settlement,
)


TEST_TAX_CONFIG = {
    "GST_ENABLED": True,
    "DEFAULT_GST_RATE": Decimal("5.00"),
    "SUPPLIER_NAME": "Test Routeless Pvt. Ltd.",
    "SUPPLIER_GSTIN": "07TESTGS123N1Z5",
    "SUPPLIER_ADDRESS": "123 Test Street",
    "SUPPLIER_STATE": "Delhi",
    "SUPPLIER_STATE_CODE": "07",
    "DEFAULT_SAC_CODE": "998555",
    "INVOICE_PREFIX": "TST",
    "DEFAULT_CURRENCY": "INR",
    "PLATFORM_COMMISSION_RATE": Decimal("0.15"),
}


class FinancialYearTest(TestCase):
    def test_before_april(self):
        self.assertEqual(_get_financial_year(date(2026, 1, 15)), "25-26")
        self.assertEqual(_get_financial_year(date(2026, 3, 31)), "25-26")

    def test_after_april(self):
        self.assertEqual(_get_financial_year(date(2026, 4, 1)), "26-27")
        self.assertEqual(_get_financial_year(date(2026, 12, 31)), "26-27")

    def test_april_boundary(self):
        self.assertEqual(_get_financial_year(date(2025, 4, 1)), "25-26")
        self.assertEqual(_get_financial_year(date(2025, 3, 31)), "24-25")


@override_settings(ROUTELESS_TAX_CONFIG=TEST_TAX_CONFIG)
class InvoiceNumberTest(TestCase):
    def test_sequential_numbering(self):
        """Invoice numbers should be sequential within a financial year."""
        num1, fy1 = generate_invoice_number(date(2026, 5, 18))
        num2, fy2 = generate_invoice_number(date(2026, 5, 18))
        self.assertEqual(fy1, "26-27")
        self.assertEqual(fy2, "26-27")
        self.assertIn("TST/26-27/000001", num1)
        self.assertIn("TST/26-27/000002", num2)

    def test_format(self):
        """Invoice number format: PREFIX/YY-YY/NNNNNN."""
        num, fy = generate_invoice_number(date(2026, 5, 18))
        self.assertTrue(num.startswith("TST/"))
        parts = num.split("/")
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[2]), 6)  # zero-padded


@override_settings(ROUTELESS_TAX_CONFIG=TEST_TAX_CONFIG)
class InvoiceCreationTest(TestCase):
    def _make_mocks(self):
        """Create mock booking, payment and experience."""
        experience = MagicMock()
        experience.title = "Test Trek"
        experience.host = MagicMock()
        experience.host.id = 99
        experience.host.username = "testhost"

        booking = MagicMock()
        booking.id = 42
        booking.experience = experience
        booking.user = MagicMock()
        booking.user.get_full_name.return_value = "Test User"
        booking.user.username = "testuser"
        booking.user.email = "test@example.com"
        booking.traveler_name = "Test User"
        booking.traveler_email = "test@example.com"
        booking.check_in_date = date(2026, 6, 1)
        booking.check_out_date = date(2026, 6, 3)
        booking.guests_count = 2
        booking.total_price = Decimal("3000.00")

        payment = MagicMock()
        payment.taxable_amount = Decimal("3000.00")
        payment.gst_rate = Decimal("5.00")
        payment.cgst_amount = Decimal("75.00")
        payment.sgst_amount = Decimal("75.00")
        payment.igst_amount = Decimal("0.00")
        payment.total_tax_amount = Decimal("150.00")
        payment.total_payable_amount = Decimal("3150.00")
        payment.amount = Decimal("3150.00")
        payment.sac_code = "998555"
        payment.currency = "INR"
        payment.razorpay_order_id = "order_test123"
        payment.razorpay_payment_id = "pay_test456"
        payment.invoice_generated = False
        payment.save = MagicMock()

        return booking, payment

    @patch("payments.invoice_service.Invoice")
    def test_idempotent_creation(self, MockInvoice):
        """If an invoice already exists, return existing without creating."""
        booking, payment = self._make_mocks()
        existing = MagicMock()
        existing.invoice_number = "TST/26-27/000001"
        MockInvoice.objects.filter.return_value.first.return_value = existing

        result = create_invoice_for_booking(booking, payment)
        self.assertEqual(result.invoice_number, "TST/26-27/000001")
        MockInvoice.objects.create.assert_not_called()


@override_settings(ROUTELESS_TAX_CONFIG=TEST_TAX_CONFIG)
class VendorSettlementTest(TestCase):
    def _make_mocks(self):
        experience = MagicMock()
        experience.host = MagicMock()
        experience.host.id = 99
        experience.host.username = "testhost"

        booking = MagicMock()
        booking.id = 42
        booking.experience = experience

        payment = MagicMock()
        payment.taxable_amount = Decimal("3000.00")
        payment.total_tax_amount = Decimal("150.00")
        payment.total_payable_amount = Decimal("3150.00")
        payment.amount = Decimal("3150.00")

        return booking, payment

    @patch("payments.invoice_service.VendorSettlement")
    def test_idempotent_settlement(self, MockSettlement):
        """If a settlement already exists, return existing."""
        booking, payment = self._make_mocks()
        existing = MagicMock()
        MockSettlement.objects.filter.return_value.first.return_value = existing

        result = create_vendor_settlement(booking, payment)
        self.assertEqual(result, existing)
        MockSettlement.objects.create.assert_not_called()

    @patch("payments.invoice_service.VendorSettlement")
    def test_settlement_amounts(self, MockSettlement):
        """Commission and payout should be calculated correctly."""
        booking, payment = self._make_mocks()
        MockSettlement.objects.filter.return_value.first.return_value = None
        MockSettlement.objects.create.return_value = MagicMock()

        create_vendor_settlement(booking, payment)

        call_kwargs = MockSettlement.objects.create.call_args[1]
        # Commission = 3000 * 0.15 = 450
        self.assertEqual(call_kwargs["routeless_commission"], Decimal("450.00"))
        # Vendor payout = 3000 - 450 = 2550
        self.assertEqual(call_kwargs["vendor_payout_amount"], Decimal("2550.00"))
        self.assertEqual(call_kwargs["gst_amount_collected"], Decimal("150.00"))
