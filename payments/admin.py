from django.contrib import admin
from .models import Payment, Commission, Payout, PaymentLog, LedgerEntry

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'currency', 'payment_status', 'razorpay_order_id', 'created_at')
    list_filter = ('payment_status', 'currency')
    search_fields = ('booking__id', 'razorpay_order_id', 'razorpay_payment_id')

@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'entry_type', 'amount', 'currency', 'reference_id', 'created_at')
    list_filter = ('entry_type', 'currency', 'created_at')
    search_fields = ('id', 'booking__id', 'reference_id')

@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'event_type', 'status', 'timestamp')
    list_filter = ('event_type', 'status', 'timestamp')
    search_fields = ('payment__booking__id', 'payment__razorpay_order_id')
    readonly_fields = ('payload',)
