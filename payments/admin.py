from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Payment, Commission, Payout, PaymentLog, LedgerEntry


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = (
        "booking", "user", "amount", "currency", "payment_status",
        "razorpay_order_id", "razorpay_payment_id", "created_at", "paid_at",
    )
    list_filter = ("payment_status", "currency", "created_at", "paid_at")
    search_fields = (
        "booking__id", "user__email", "user__username",
        "razorpay_order_id", "razorpay_payment_id",
    )
    readonly_fields = (
        "razorpay_order_id", "razorpay_payment_id", "razorpay_signature",
        "raw_response", "created_at", "updated_at", "paid_at",
    )
    fieldsets = (
        ("Booking", {
            "fields": ("booking", "user", "amount", "currency", "payment_status"),
        }),
        ("Razorpay Details", {
            "fields": (
                "razorpay_order_id", "razorpay_payment_id",
                "razorpay_signature", "raw_response",
            ),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "paid_at"),
        }),
    )


@admin.register(Commission)
class CommissionAdmin(ModelAdmin):
    list_display = ("booking", "total_amount", "platform_fee", "host_earning", "commission_rate", "calculated_at")
    list_filter = ("calculated_at",)
    search_fields = ("booking__id",)
    readonly_fields = ("calculated_at",)


@admin.register(Payout)
class PayoutAdmin(ModelAdmin):
    list_display = ("host", "booking", "amount", "payout_status", "payout_reference", "created_at")
    list_filter = ("payout_status", "created_at")
    search_fields = ("host__username", "host__email", "booking__id", "payout_reference")
    readonly_fields = ("created_at",)


@admin.register(LedgerEntry)
class LedgerEntryAdmin(ModelAdmin):
    list_display = ("id", "booking", "entry_type", "amount", "currency", "reference_id", "created_at")
    list_filter = ("entry_type", "currency", "created_at")
    search_fields = ("id", "booking__id", "reference_id")
    readonly_fields = ("id", "created_at")


@admin.register(PaymentLog)
class PaymentLogAdmin(ModelAdmin):
    list_display = ("id", "payment", "event_type", "event_id", "status", "timestamp")
    list_filter = ("event_type", "status", "timestamp")
    search_fields = ("payment__booking__id", "payment__razorpay_order_id", "event_id")
    readonly_fields = ("payload", "event_id", "timestamp")
