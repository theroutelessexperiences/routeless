import uuid
import logging
from decimal import Decimal

import razorpay
from django.conf import settings

from .models import Payment, Commission, PaymentLog, LedgerEntry

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Razorpay client
# -------------------------------------------------------------------
def get_razorpay_client():
    """Return an authenticated Razorpay client, or None if keys are missing."""
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")

    if not key_id or not key_secret:
        logger.warning(
            "Razorpay client not configured: RAZORPAY_KEY_ID=%s, RAZORPAY_KEY_SECRET=%s",
            "SET" if key_id else "MISSING",
            "SET" if key_secret else "MISSING",
        )
        return None
    return razorpay.Client(auth=(key_id, key_secret))


# -------------------------------------------------------------------
# Create Razorpay order
# -------------------------------------------------------------------
def create_razorpay_order(booking, tax_breakup=None):
    """
    Creates a Razorpay order from the total_price of a Booking.
    Saves the new Payment record with razorpay_order_id.

    If *tax_breakup* (a ``TaxBreakup`` dataclass) is provided, the
    Payment model is populated with a tax snapshot and the Razorpay
    order amount uses the GST-inclusive ``total_payable_amount``.

    Returns (success: bool, payment_or_error).
    """
    logger.info(
        "create_razorpay_order: booking=%s, PAYMENTS_DEMO_MODE=%s, "
        "RAZORPAY_KEY_ID=%s, RAZORPAY_KEY_SECRET=%s",
        booking.id,
        getattr(settings, "PAYMENTS_DEMO_MODE", "UNSET"),
        "SET" if getattr(settings, "RAZORPAY_KEY_ID", "") else "MISSING",
        "SET" if getattr(settings, "RAZORPAY_KEY_SECRET", "") else "MISSING",
    )

    # Determine the payable amount
    if tax_breakup is not None:
        payable_amount = tax_breakup.total_payable_amount
    else:
        payable_amount = booking.total_price

    payment, created = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            "amount": payable_amount,
            "currency": "INR",
            "user": booking.user,
        },
    )

    # Populate tax snapshot if provided (on first creation or update)
    if tax_breakup is not None and (created or not payment.gst_rate):
        payment.base_amount = tax_breakup.base_amount
        payment.subtotal_amount = tax_breakup.subtotal_amount
        payment.discount_amount = tax_breakup.discount_amount
        payment.taxable_amount = tax_breakup.taxable_amount
        payment.gst_rate = tax_breakup.gst_rate
        payment.cgst_amount = tax_breakup.cgst_amount
        payment.sgst_amount = tax_breakup.sgst_amount
        payment.igst_amount = tax_breakup.igst_amount
        payment.total_tax_amount = tax_breakup.total_tax_amount
        payment.total_payable_amount = tax_breakup.total_payable_amount
        payment.tax_label = tax_breakup.tax_label
        payment.amount = payable_amount
        payment.save()

    # If order exists and payment is still pending, reuse it
    if payment.razorpay_order_id and payment.payment_status in ("pending", "created"):
        return True, payment

    # Ensure user is set on legacy records
    if not payment.user and booking.user:
        payment.user = booking.user

    # --- DEMO MODE ---
    if getattr(settings, "PAYMENTS_DEMO_MODE", False):
        payment.razorpay_order_id = f"demo_order_{uuid.uuid4().hex[:8]}"
        payment.amount = payable_amount
        payment.payment_status = "pending"
        payment.save()

        PaymentLog.objects.create(
            payment=payment,
            event_type="order_created",
            payload="DEMO_MODE_ORDER",
            status="success",
        )
        return True, payment

    # --- LIVE MODE ---
    client = get_razorpay_client()
    if not client:
        return False, "Razorpay client not configured."

    if tax_breakup is not None:
        amount_in_paise = tax_breakup.amount_in_paise
    else:
        amount_in_paise = int(booking.total_price * 100)

    try:
        order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"booking_{booking.id}",
            "payment_capture": 1,
            "notes": {
                "booking_id": str(booking.id),
                "user_id": str(booking.user_id) if booking.user_id else "",
                "experience_id": str(booking.experience_id),
                "experience_title": str(booking.experience.title)[:50],
            },
        })

        payment.razorpay_order_id = order.get("id")
        payment.amount = payable_amount
        payment.payment_status = "pending"
        payment.raw_response = order
        payment.save()

        PaymentLog.objects.create(
            payment=payment,
            event_type="order_created",
            payload=str(order),
            status="success",
        )

        return True, payment

    except Exception as e:
        logger.error("Razorpay order creation failed for booking %s: %s", booking.id, e)
        PaymentLog.objects.create(
            payment=payment,
            event_type="order_created",
            payload=str(e),
            status="error",
        )
        return False, str(e)


# -------------------------------------------------------------------
# Verify payment signature
# -------------------------------------------------------------------
def verify_payment_signature(razorpay_payment_id, razorpay_order_id, razorpay_signature):
    """
    Verifies payment signature from Razorpay.
    Returns (success: bool, error_message_or_none).
    """
    # Demo mode bypass
    if getattr(settings, "PAYMENTS_DEMO_MODE", False) and str(razorpay_order_id).startswith("demo_order_"):
        return True, None

    client = get_razorpay_client()
    if not client:
        return False, "Razorpay client not configured."

    params_dict = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
    }

    try:
        client.utility.verify_payment_signature(params_dict)
        return True, None
    except razorpay.errors.SignatureVerificationError:
        return False, "Signature verification failed."
    except Exception as e:
        return False, str(e)


# -------------------------------------------------------------------
# Ledger entries (post-payment accounting)
# -------------------------------------------------------------------
def calculate_ledger_entries(booking, reference_id=""):
    """
    Creates immutable LedgerEntry records once payment is successful.
    Idempotent — skips if entries already exist.
    """
    if LedgerEntry.objects.filter(booking=booking).exists():
        return

    total_amount = Decimal(str(booking.total_price))
    commission_rate = Decimal("0.10")
    platform_fee = total_amount * commission_rate
    host_earning = total_amount - platform_fee

    LedgerEntry.objects.create(
        booking=booking,
        entry_type="customer_payment",
        amount=total_amount,
        reference_id=reference_id,
    )

    LedgerEntry.objects.create(
        booking=booking,
        entry_type="platform_commission",
        amount=-platform_fee,
        reference_id=reference_id,
    )

    LedgerEntry.objects.create(
        booking=booking,
        entry_type="host_earning",
        amount=-host_earning,
        reference_id=reference_id,
    )