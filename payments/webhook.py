import json
import logging

import razorpay
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone

from .models import Payment, PaymentLog
from .services import get_razorpay_client, calculate_ledger_entries

logger = logging.getLogger(__name__)


@csrf_exempt
def razorpay_webhook_view(request):
    """
    Razorpay webhook endpoint.

    - CSRF exempt (Razorpay cannot send CSRF tokens)
    - Verifies webhook signature using RAZORPAY_WEBHOOK_SECRET
    - Idempotent: checks event_id before processing
    - Handles: payment.captured, payment.failed, order.paid
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")

    payload = request.body.decode("utf-8")
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature:
        return HttpResponseBadRequest("Missing signature.")

    # Use dedicated webhook secret (NOT the API key secret)
    webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("RAZORPAY_WEBHOOK_SECRET is not configured.")
        return HttpResponseBadRequest("Webhook not configured.")

    client = get_razorpay_client()
    if not client:
        return HttpResponseBadRequest("Payment gateway not configured.")

    # Verify webhook signature using raw payload (before any parsing)
    try:
        client.utility.verify_webhook_signature(payload, signature, webhook_secret)
    except razorpay.errors.SignatureVerificationError:
        logger.warning("Webhook signature verification failed.")
        return HttpResponseBadRequest("Invalid signature.")

    data = json.loads(payload)
    event = data.get("event")
    event_id = data.get("id", "")  # Razorpay event ID for deduplication

    if not event:
        return HttpResponseBadRequest("Missing event type.")

    # --- Idempotency check: skip if this event_id was already processed ---
    if event_id and PaymentLog.objects.filter(event_id=event_id).exists():
        logger.info("Duplicate webhook event %s — skipping.", event_id)
        return HttpResponse("Duplicate event, already processed.")

    payment_entity = data.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_order_id = payment_entity.get("order_id")
    razorpay_payment_id = payment_entity.get("id")

    if not razorpay_order_id:
        return HttpResponse("Order ID not found in payload, ignoring.")

    try:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )
            booking = payment.booking

            if event == "payment.captured":
                PaymentLog.objects.create(
                    payment=payment,
                    event_type="webhook_captured",
                    event_id=event_id,
                    payload=payload,
                    status="success",
                )

                if payment.payment_status != "success":
                    payment.payment_status = "success"
                    payment.razorpay_payment_id = razorpay_payment_id
                    payment.paid_at = timezone.now()
                    payment.raw_response = payment_entity
                    payment.save()

                    booking.booking_status = "confirmed"  # lowercase to match Status enum
                    booking.save(update_fields=["booking_status", "updated_at"])

                    calculate_ledger_entries(booking, reference_id=razorpay_payment_id)

                    logger.info(
                        "Webhook: Booking %s confirmed via payment.captured", booking.id
                    )

            elif event == "payment.failed":
                PaymentLog.objects.create(
                    payment=payment,
                    event_type="webhook_failed",
                    event_id=event_id,
                    payload=payload,
                    status="success",
                )

                if payment.payment_status != "success":
                    payment.payment_status = "failed"
                    payment.raw_response = payment_entity
                    payment.save(update_fields=["payment_status", "raw_response", "updated_at"])

                    logger.info(
                        "Webhook: Payment failed for booking %s", booking.id
                    )

            elif event == "order.paid":
                PaymentLog.objects.create(
                    payment=payment,
                    event_type="webhook_order_paid",
                    event_id=event_id,
                    payload=payload,
                    status="success",
                )

                # order.paid is a backup confirmation — only act if not already success
                if payment.payment_status != "success":
                    payment.payment_status = "success"
                    payment.paid_at = timezone.now()
                    payment.save(update_fields=["payment_status", "paid_at", "updated_at"])

                    booking.booking_status = "confirmed"
                    booking.save(update_fields=["booking_status", "updated_at"])

                    calculate_ledger_entries(
                        booking, reference_id=razorpay_payment_id or ""
                    )

                    logger.info(
                        "Webhook: Booking %s confirmed via order.paid", booking.id
                    )

            # TODO: Handle refund.processed when refund flow is implemented
            # elif event == "refund.processed":
            #     refund_entity = data.get("payload", {}).get("refund", {}).get("entity", {})
            #     ...

            else:
                PaymentLog.objects.create(
                    payment=payment,
                    event_type=f"webhook_{event}",
                    event_id=event_id,
                    payload=payload,
                    status="ignored",
                )
                logger.info("Webhook: Unhandled event type '%s' for order %s", event, razorpay_order_id)

    except Payment.DoesNotExist:
        logger.warning("Webhook: No payment found for order_id %s", razorpay_order_id)
        return HttpResponse("Payment matching order_id not found.")

    except Exception as e:
        logger.exception("Webhook processing error for order %s", razorpay_order_id)
        PaymentLog.objects.create(
            event_type="webhook_error",
            event_id=event_id,
            payload=f"Error: {e}\nPayload: {payload}",
            status="error",
        )

    return HttpResponse("Webhook processed successfully.")
