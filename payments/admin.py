from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import Payment, Commission, Payout, PaymentLog, LedgerEntry, Invoice, InvoiceCounter, VendorSettlement


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = (
        "booking", "user", "amount", "currency", "payment_status",
        "razorpay_order_id", "razorpay_payment_id", "created_at", "paid_at",
    )
    list_filter = ("payment_status", "currency", "created_at", "paid_at", "invoice_generated")
    search_fields = (
        "booking__id", "user__email", "user__username",
        "razorpay_order_id", "razorpay_payment_id",
    )
    readonly_fields = (
        "razorpay_order_id", "razorpay_payment_id", "razorpay_signature",
        "raw_response", "created_at", "updated_at", "paid_at",
        "base_amount", "subtotal_amount", "discount_amount", "taxable_amount",
        "gst_rate", "cgst_amount", "sgst_amount", "igst_amount",
        "total_tax_amount", "total_payable_amount", "tax_label", "sac_code",
    )
    fieldsets = (
        ("Booking", {
            "fields": ("booking", "user", "amount", "currency", "payment_status"),
        }),
        ("Tax Breakup (Snapshot)", {
            "fields": (
                "base_amount", "subtotal_amount", "discount_amount",
                "taxable_amount", "gst_rate", "tax_label", "sac_code",
                "cgst_amount", "sgst_amount", "igst_amount",
                "total_tax_amount", "total_payable_amount",
                "invoice_required", "invoice_generated",
            ),
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


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = (
        "invoice_number", "booking", "customer_name", "total_amount",
        "gst_rate", "status", "invoice_date", "pdf_link",
    )
    list_filter = ("status", "financial_year", "invoice_date")
    search_fields = (
        "invoice_number", "customer_name", "customer_email",
        "booking__id", "razorpay_payment_id",
    )
    readonly_fields = (
        "invoice_number", "invoice_date", "financial_year",
        "supplier_name", "supplier_gstin", "supplier_address",
        "supplier_state", "supplier_state_code",
        "customer_name", "customer_email", "customer_phone",
        "taxable_amount", "gst_rate", "cgst_amount", "sgst_amount",
        "igst_amount", "total_tax_amount", "total_amount",
        "razorpay_order_id", "razorpay_payment_id",
        "created_at", "updated_at",
    )
    fieldsets = (
        ("Invoice", {
            "fields": ("invoice_number", "invoice_date", "financial_year", "status", "booking", "payment", "user"),
        }),
        ("Supplier (Routeless)", {
            "fields": ("supplier_name", "supplier_gstin", "supplier_address", "supplier_state", "supplier_state_code"),
            "classes": ("collapse",),
        }),
        ("Customer", {
            "fields": ("customer_name", "customer_email", "customer_phone", "customer_billing_address", "customer_gstin"),
        }),
        ("Service", {
            "fields": ("sac_code", "service_description"),
        }),
        ("Amounts", {
            "fields": ("taxable_amount", "gst_rate", "cgst_amount", "sgst_amount", "igst_amount", "total_tax_amount", "total_amount", "currency"),
        }),
        ("Razorpay", {
            "fields": ("razorpay_order_id", "razorpay_payment_id"),
            "classes": ("collapse",),
        }),
        ("PDF", {
            "fields": ("pdf_file",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    @admin.display(description="PDF")
    def pdf_link(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">📄 Download</a>', obj.pdf_file.url)
        return "-"


@admin.register(InvoiceCounter)
class InvoiceCounterAdmin(ModelAdmin):
    list_display = ("financial_year", "last_number")
    readonly_fields = ("financial_year", "last_number")


@admin.register(VendorSettlement)
class VendorSettlementAdmin(ModelAdmin):
    list_display = (
        "booking", "vendor", "customer_total_paid", "taxable_amount",
        "gst_amount_collected", "routeless_commission", "vendor_payout_amount",
        "payout_status", "created_at",
    )
    list_filter = ("payout_status", "created_at")
    search_fields = ("booking__id", "vendor__username", "vendor__email")
    readonly_fields = (
        "customer_total_paid", "taxable_amount", "gst_amount_collected",
        "routeless_commission", "vendor_payout_amount", "created_at", "updated_at",
    )
    fieldsets = (
        ("Settlement", {
            "fields": ("booking", "vendor", "payout_status", "payout_date"),
        }),
        ("Amounts", {
            "fields": (
                "customer_total_paid", "taxable_amount", "gst_amount_collected",
                "routeless_commission", "vendor_payout_amount",
            ),
        }),
        ("Notes", {
            "fields": ("internal_notes",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

