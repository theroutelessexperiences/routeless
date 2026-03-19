import razorpay
from django.conf import settings
from .models import Payment, Commission

def get_razorpay_client():
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    key_id = os.getenv("RAZORPAY_KEY_ID", getattr(settings, "RAZORPAY_KEY_ID", ""))
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", getattr(settings, "RAZORPAY_KEY_SECRET", ""))
    
    if not key_id or not key_secret:
        return None
    return razorpay.Client(auth=(key_id, key_secret))

def create_razorpay_order(booking):
    """
    Creates a Razorpay order from the total_price of a Booking.
    Saves the new Payment record with razorpay_order_id.
    """
    # Check if a Payment record already exists for this booking
    payment, created = Payment.objects.get_or_create(
        booking=booking,
        defaults={'amount': booking.total_price, 'currency': 'INR'}
    )
    
    # If order exists and payment is not failed, reuse it
    if payment.razorpay_order_id and payment.payment_status == 'pending':
        return True, payment

    from django.conf import settings
    if getattr(settings, 'PAYMENTS_DEMO_MODE', False):
        import uuid
        payment.razorpay_order_id = f"demo_order_{uuid.uuid4().hex[:8]}"
        payment.amount = booking.total_price
        payment.payment_status = "pending"
        payment.save()
        
        from .models import PaymentLog
        PaymentLog.objects.create(
            payment=payment,
            event_type="order_created",
            payload="DEMO_MODE_ORDER",
            status="success"
        )
        return True, payment

    client = get_razorpay_client()
    if not client:
        return False, "Razorpay client not configured."

    amount_in_paise = int(booking.total_price * 100)
    
    try:
        order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"receipt_{booking.id}",
            "payment_capture": 1
        })
        
        payment.razorpay_order_id = order.get("id")
        payment.amount = booking.total_price
        payment.payment_status = "pending"
        payment.save()
        
        from .models import PaymentLog
        PaymentLog.objects.create(
            payment=payment,
            event_type="order_created",
            payload=str(order),
            status="success"
        )
        
        return True, payment
        
    except Exception as e:
        from .models import PaymentLog
        PaymentLog.objects.create(
            payment=payment,
            event_type="order_created",
            payload=str(e),
            status="error"
        )
        return False, str(e)

def verify_payment_signature(razorpay_payment_id, razorpay_order_id, razorpay_signature):
    """
    Verifies payment signature from Razorpay.
    """
    from django.conf import settings
    if getattr(settings, 'PAYMENTS_DEMO_MODE', False) and str(razorpay_order_id).startswith('demo_order_'):
        return True, None

    client = get_razorpay_client()
    if not client:
        return False, "Razorpay client not configured."
        
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        client.utility.verify_payment_signature(params_dict)
        return True, None
    except razorpay.errors.SignatureVerificationError:
        return False, "Signature verification failed."
    except Exception as e:
        return False, str(e)

# def calculate_ledger_entries(booking, reference_id=""):
#     """
#     Calculates and creates immutable LedgerEntry records once payment is successful.
#     """
#     from .models import LedgerEntry
    
#     # Check if ledger already exists to ensure idempotency
#     if LedgerEntry.objects.filter(booking=booking).exists():
#         return

#     # Assuming standard 10% platform fee
#     commission_rate = Decimal("0.15")
#     total_amount = booking.total_price
#     platform_fee = total_amount * commission_rate
#     host_earning = total_amount - platform_fee
    
#     # 1. Record the full customer payment
#     LedgerEntry.objects.create(
#         booking=booking,
#         entry_type="customer_payment",
#         amount=total_amount,
#         reference_id=reference_id
#     )
    
#     # 2. Record the platform commission (negative entry)
#     LedgerEntry.objects.create(
#         booking=booking,
#         entry_type="platform_commission",
#         amount=-platform_fee,
#         reference_id=reference_id
#     )

#     # 3. Record the host earning (negative entry context for platform liability)
#     LedgerEntry.objects.create(
#         booking=booking,
#         entry_type="host_earning",
#         amount=-host_earning,
#         reference_id=reference_id
#     )
from decimal import Decimal
import razorpay
from django.conf import settings
from .models import Payment, Commission

def get_razorpay_client():
    import os
    from dotenv import load_dotenv
    load_dotenv()

    key_id = os.getenv("RAZORPAY_KEY_ID", getattr(settings, "RAZORPAY_KEY_ID", ""))
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", getattr(settings, "RAZORPAY_KEY_SECRET", ""))

    if not key_id or not key_secret:
        return None
    return razorpay.Client(auth=(key_id, key_secret))


def create_razorpay_order(booking):
    """
    Creates a Razorpay order from the total_price of a Booking.
    Saves the new Payment record with razorpay_order_id.
    """
    payment, created = Payment.objects.get_or_create(
        booking=booking,
        defaults={"amount": booking.total_price, "currency": "INR"}
    )

    if payment.razorpay_order_id and payment.payment_status == "pending":
        return True, payment

    if getattr(settings, "PAYMENTS_DEMO_MODE", False):
        import uuid
        payment.razorpay_order_id = f"demo_order_{uuid.uuid4().hex[:8]}"
        payment.amount = booking.total_price
        payment.payment_status = "pending"
        payment.save()

        from .models import PaymentLog
        PaymentLog.objects.create(
            payment=payment,
            event_type="order_created",
            payload="DEMO_MODE_ORDER",
            status="success"
        )
        return True, payment

    client = get_razorpay_client()
    if not client:
        return False, "Razorpay client not configured."

    amount_in_paise = int(booking.total_price * 100)

    try:
        order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"receipt_{booking.id}",
            "payment_capture": 1
        })

        payment.razorpay_order_id = order.get("id")
        payment.amount = booking.total_price
        payment.payment_status = "pending"
        payment.save()

        from .models import PaymentLog
        PaymentLog.objects.create(
            payment=payment,
            event_type="order_created",
            payload=str(order),
            status="success"
        )

        return True, payment

    except Exception as e:
        from .models import PaymentLog
        PaymentLog.objects.create(
            payment=payment,
            event_type="order_created",
            payload=str(e),
            status="error"
        )
        return False, str(e)


def verify_payment_signature(razorpay_payment_id, razorpay_order_id, razorpay_signature):
    """
    Verifies payment signature from Razorpay.
    """
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


def calculate_ledger_entries(booking, reference_id=""):
    """
    Calculates and creates immutable LedgerEntry records once payment is successful.
    """
    from .models import LedgerEntry

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
        reference_id=reference_id
    )

    LedgerEntry.objects.create(
        booking=booking,
        entry_type="platform_commission",
        amount=-platform_fee,
        reference_id=reference_id
    )

    LedgerEntry.objects.create(
        booking=booking,
        entry_type="host_earning",
        amount=-host_earning,
        reference_id=reference_id
    )