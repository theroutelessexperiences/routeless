from django.db import models
from django.contrib.auth.models import User
from marketplace.models import Booking

class Payment(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    )
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    razorpay_order_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

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
    event_type = models.CharField(max_length=50) # e.g. "verification_attempt", "webhook_captured", "order_created"
    payload = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20) # "success", "error", "pending"
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log {self.event_type} - {self.status} at {self.timestamp}"

import uuid

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
