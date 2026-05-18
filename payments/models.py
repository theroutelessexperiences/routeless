from django.db import models
from django.contrib.auth.models import User
from marketplace.models import Booking
import uuid


class Payment(models.Model):
    STATUS_CHOICES = (
        ("created", "Created"),
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("verification_failed", "Verification Failed"),
        ("refunded", "Refunded"),
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    razorpay_order_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    payment_status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="created")
    raw_response = models.JSONField(null=True, blank=True, help_text="Raw Razorpay API response for debugging")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # --- Tax snapshot fields (added for GST breakup) ---
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Per-person-per-day price at booking time")
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="base × guests × days")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="subtotal − discount")
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="GST rate at booking time, e.g. 5.00")
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_payable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="taxable + tax = Razorpay amount")
    tax_currency = models.CharField(max_length=10, default="INR")
    sac_code = models.CharField(max_length=10, default="998555", blank=True)
    place_of_supply = models.CharField(max_length=100, blank=True, help_text="Customer state / place of supply")
    tax_label = models.CharField(max_length=50, blank=True, help_text="e.g. GST @ 5%")
    invoice_required = models.BooleanField(default=True)
    invoice_generated = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment for Booking #{self.booking.id} - {self.payment_status}"


class Commission(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='commission')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    host_earning = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2, help_text="e.g. 0.10 for 10%")
    calculated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Commission for Booking #{self.booking.id}"


class Payout(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processed", "Processed"),
        ("failed", "Failed"),
    )

    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts')
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payout')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payout_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payout_reference = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payout for {self.host.username} - {self.amount}"


class PaymentLog(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='logs', null=True, blank=True)
    event_type = models.CharField(max_length=50)  # e.g. "verification_attempt", "webhook_captured", "order_created"
    event_id = models.CharField(max_length=255, null=True, blank=True, help_text="Razorpay webhook event ID for deduplication")
    payload = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20)  # "success", "error", "pending"
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["event_id"], name="paymentlog_event_id_idx"),
        ]

    def __str__(self):
        return f"Log {self.event_type} - {self.status} at {self.timestamp}"


class LedgerEntry(models.Model):
    ENTRY_TYPE_CHOICES = (
        ("customer_payment", "Customer Payment"),
        ("platform_commission", "Platform Commission"),
        ("host_earning", "Host Earning"),
        ("refund", "Refund"),
        ("payout", "Host Payout"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="ledger_entries")

    entry_type = models.CharField(max_length=50, choices=ENTRY_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    reference_id = models.CharField(max_length=200, help_text="e.g Razorpay Payment ID or Payout ID")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_entry_type_display()} for Booking #{self.booking.id} - {self.amount}"


# -------------------------------------------------------------------
# Invoice (Routeless-generated customer invoice)
# -------------------------------------------------------------------
class InvoiceCounter(models.Model):
    """
    Simple auto-increment counter per financial year.
    Used with select_for_update() to guarantee unique sequential numbers.
    """
    financial_year = models.CharField(max_length=7, unique=True, help_text="e.g. 25-26")
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Invoice Counter"
        verbose_name_plural = "Invoice Counters"

    def __str__(self):
        return f"FY {self.financial_year}: last #{self.last_number}"


class Invoice(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("generated", "Generated"),
        ("sent", "Sent"),
        ("cancelled", "Cancelled"),
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="invoice")
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="invoice")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")

    invoice_number = models.CharField(max_length=30, unique=True, db_index=True)
    invoice_date = models.DateField()
    financial_year = models.CharField(max_length=7, help_text="e.g. 25-26")

    # Supplier info (Routeless — snapshot at invoice time)
    supplier_name = models.CharField(max_length=255)
    supplier_gstin = models.CharField(max_length=15, blank=True)
    supplier_address = models.TextField(blank=True)
    supplier_state = models.CharField(max_length=100, blank=True)
    supplier_state_code = models.CharField(max_length=5, blank=True)

    # Customer info (snapshot)
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_billing_address = models.TextField(blank=True)
    customer_gstin = models.CharField(max_length=15, blank=True)

    # Service details
    sac_code = models.CharField(max_length=10, default="998555")
    service_description = models.TextField()

    # Amount snapshot
    taxable_amount = models.DecimalField(max_digits=10, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")

    # Razorpay references
    razorpay_order_id = models.CharField(max_length=255, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True)

    # PDF file
    pdf_file = models.FileField(upload_to="invoices/", blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-invoice_date", "-created_at"]
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return f"Invoice {self.invoice_number} for Booking #{self.booking_id}"


# -------------------------------------------------------------------
# Vendor Settlement (internal payout tracking, NOT a customer invoice)
# -------------------------------------------------------------------
class VendorSettlement(models.Model):
    PAYOUT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="vendor_settlement")
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="settlements")

    customer_total_paid = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total paid by customer incl. GST")
    taxable_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Pre-tax base amount")
    gst_amount_collected = models.DecimalField(max_digits=10, decimal_places=2, help_text="GST portion collected from customer")
    routeless_commission = models.DecimalField(max_digits=10, decimal_places=2, help_text="Platform fee on taxable amount")
    vendor_payout_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount payable to vendor")

    payout_status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default="pending")
    payout_date = models.DateTimeField(null=True, blank=True)
    internal_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vendor Settlement"
        verbose_name_plural = "Vendor Settlements"

    def __str__(self):
        return f"Settlement for Booking #{self.booking_id} → {self.vendor.username}"

