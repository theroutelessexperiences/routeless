"""
Unit tests for the GST / tax calculation service.
"""
from decimal import Decimal
from django.test import TestCase, override_settings

from payments.tax_service import calculate_booking_tax, TaxBreakup


TEST_TAX_CONFIG = {
    "GST_ENABLED": True,
    "DEFAULT_GST_RATE": Decimal("5.00"),
    "SUPPLIER_NAME": "Test Supplier",
    "SUPPLIER_GSTIN": "",
    "SUPPLIER_ADDRESS": "",
    "SUPPLIER_STATE": "",
    "SUPPLIER_STATE_CODE": "",
    "DEFAULT_SAC_CODE": "998555",
    "INVOICE_PREFIX": "TST",
    "DEFAULT_CURRENCY": "INR",
    "PLATFORM_COMMISSION_RATE": Decimal("0.15"),
}


@override_settings(ROUTELESS_TAX_CONFIG=TEST_TAX_CONFIG)
class TaxServiceTestCase(TestCase):

    def test_basic_gst_calculation(self):
        """5% GST on ₹1000 base should yield ₹50 tax."""
        tb = calculate_booking_tax(base_amount=1000, quantity=1, days=1)
        self.assertEqual(tb.taxable_amount, Decimal("1000.00"))
        self.assertEqual(tb.total_tax_amount, Decimal("50.00"))
        self.assertEqual(tb.total_payable_amount, Decimal("1050.00"))

    def test_quantity_and_days(self):
        """2 guests × 3 days × ₹500 = ₹3000 taxable."""
        tb = calculate_booking_tax(base_amount=500, quantity=2, days=3)
        self.assertEqual(tb.subtotal_amount, Decimal("3000.00"))
        self.assertEqual(tb.taxable_amount, Decimal("3000.00"))
        self.assertEqual(tb.total_tax_amount, Decimal("150.00"))
        self.assertEqual(tb.total_payable_amount, Decimal("3150.00"))

    def test_cgst_sgst_split(self):
        """CGST and SGST should each be half the GST rate."""
        tb = calculate_booking_tax(base_amount=1000, quantity=1, days=1)
        self.assertEqual(tb.cgst_amount, Decimal("25.00"))
        self.assertEqual(tb.sgst_amount, Decimal("25.00"))
        self.assertEqual(tb.igst_amount, Decimal("0.00"))

    def test_discount(self):
        """Discount reduces taxable amount before GST is applied."""
        tb = calculate_booking_tax(base_amount=1000, quantity=1, days=1, discount=200)
        self.assertEqual(tb.discount_amount, Decimal("200.00"))
        self.assertEqual(tb.taxable_amount, Decimal("800.00"))
        self.assertEqual(tb.total_tax_amount, Decimal("40.00"))
        self.assertEqual(tb.total_payable_amount, Decimal("840.00"))

    def test_discount_cannot_exceed_subtotal(self):
        """Discount capped at subtotal — cannot go negative."""
        tb = calculate_booking_tax(base_amount=100, quantity=1, days=1, discount=999)
        self.assertEqual(tb.taxable_amount, Decimal("0.00"))
        self.assertEqual(tb.total_payable_amount, Decimal("0.00"))

    def test_zero_quantity(self):
        tb = calculate_booking_tax(base_amount=1000, quantity=0, days=1)
        self.assertEqual(tb.subtotal_amount, Decimal("0.00"))
        self.assertEqual(tb.total_payable_amount, Decimal("0.00"))

    def test_zero_price(self):
        tb = calculate_booking_tax(base_amount=0, quantity=2, days=3)
        self.assertEqual(tb.total_payable_amount, Decimal("0.00"))

    def test_paise_conversion(self):
        """amount_in_paise should be total_payable × 100 as integer."""
        tb = calculate_booking_tax(base_amount=1000, quantity=1, days=1)
        self.assertEqual(tb.amount_in_paise, 105000)

    def test_rounding(self):
        """Verify rounding to 2 decimal places."""
        tb = calculate_booking_tax(base_amount="333.33", quantity=1, days=1)
        # 333.33 * 5% = 16.6665 → rounded
        self.assertEqual(tb.taxable_amount, Decimal("333.33"))
        # CGST = 333.33 * 2.5 / 100 = 8.33325 → 8.33
        self.assertEqual(tb.cgst_amount, Decimal("8.33"))
        self.assertEqual(tb.sgst_amount, Decimal("8.33"))

    def test_custom_gst_rate(self):
        """Override the default rate."""
        tb = calculate_booking_tax(base_amount=1000, quantity=1, days=1, gst_rate=18)
        self.assertEqual(tb.gst_rate, Decimal("18.00"))
        self.assertEqual(tb.total_tax_amount, Decimal("180.00"))
        self.assertEqual(tb.tax_label, "GST @ 18%")

    def test_tax_label(self):
        tb = calculate_booking_tax(base_amount=1000, quantity=1, days=1)
        self.assertEqual(tb.tax_label, "GST @ 5%")

    def test_gst_disabled(self):
        """When GST is disabled, no tax should be applied."""
        disabled_config = dict(TEST_TAX_CONFIG)
        disabled_config["GST_ENABLED"] = False
        with self.settings(ROUTELESS_TAX_CONFIG=disabled_config):
            tb = calculate_booking_tax(base_amount=1000, quantity=1, days=1)
            self.assertEqual(tb.total_tax_amount, Decimal("0.00"))
            self.assertEqual(tb.total_payable_amount, Decimal("1000.00"))
            self.assertEqual(tb.tax_label, "No tax")

    def test_as_dict(self):
        """as_dict should return a plain dict with string Decimals."""
        tb = calculate_booking_tax(base_amount=1000, quantity=1, days=1)
        d = tb.as_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("total_payable_amount", d)
        self.assertEqual(d["total_payable_amount"], "1050.00")

    def test_result_is_frozen(self):
        """TaxBreakup should be immutable."""
        tb = calculate_booking_tax(base_amount=1000, quantity=1, days=1)
        with self.assertRaises(AttributeError):
            tb.total_payable_amount = Decimal("999")
