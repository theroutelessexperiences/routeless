import json
import razorpay
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Payment, PaymentLog
from marketplace.models import Booking
from .services import get_razorpay_client, calculate_ledger_entries

@csrf_exempt
def razorpay_webhook_view(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")

    payload = request.body.decode('utf-8')
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature:
        return HttpResponseBadRequest("Missing signature.")

    secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    client = get_razorpay_client()
    
    if not client:
        return HttpResponseBadRequest("Payment gateway not configured")

    try:
        client.utility.verify_webhook_signature(payload, signature, secret)
    except razorpay.errors.SignatureVerificationError:
        return HttpResponseBadRequest("Invalid signature.")
    
    data = json.loads(payload)
    event = data.get("event")
    
    if not event:
        return HttpResponseBadRequest("Missing event format.")

    payment_entity = data.get('payload', {}).get('payment', {}).get('entity', {})
    razorpay_order_id = payment_entity.get("order_id")
    razorpay_payment_id = payment_entity.get("id")

    if not razorpay_order_id:
        return HttpResponse("Order ID not found, ignoring.")

    try:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(razorpay_order_id=razorpay_order_id)
            booking = payment.booking
            
            PaymentLog.objects.create(
                payment=payment,
                event_type="webhook_captured" if event == "payment.captured" else "webhook_failed",
                payload=payload,
                status="success"
            )

            if event == "payment.captured":
                if payment.payment_status != "success":
                    payment.payment_status = "success"
                    payment.razorpay_payment_id = razorpay_payment_id
                    payment.save()
                    
                    booking.booking_status = "Confirmed"
                    booking.save()
                    
                    calculate_ledger_entries(booking, reference_id=razorpay_payment_id)

            elif event == "payment.failed":
                if payment.payment_status != "success":
                    payment.payment_status = "failed"
                    payment.save()
                    
    except Payment.DoesNotExist:
        return HttpResponse("Payment matching order_id not found.")
    except Exception as e:
        PaymentLog.objects.create(
            event_type="webhook_error",
            payload=f"Error: {e}\nPayload: {payload}",
            status="error"
        )

    return HttpResponse("Webhook processed successfully.")
