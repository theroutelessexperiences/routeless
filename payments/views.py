from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from marketplace.models import Booking
from .models import Payment, PaymentLog
from .services import verify_payment_signature, calculate_ledger_entries
from marketplace.services.emails import send_payment_success_email, send_host_new_booking_email
import logging
import decimal

logger = logging.getLogger(__name__)


@login_required
def checkout_verify(request):
    if request.method != "POST":
        return redirect("home")

    booking_id = request.POST.get("booking_id")
    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_signature = request.POST.get("razorpay_signature")

    try:
        with transaction.atomic():
            booking = get_object_or_404(
                Booking.objects.select_for_update(),
                id=booking_id,
                user=request.user
            )

            payment = get_object_or_404(
                Payment.objects.select_for_update(),
                booking=booking,
                razorpay_order_id=razorpay_order_id
            )

            if payment.payment_status == "success":
                messages.info(request, "This payment has already been verified successfully.")
                return redirect(f"/booking-success/?booking_id={booking.id}")

            success, error = verify_payment_signature(
                razorpay_payment_id,
                razorpay_order_id,
                razorpay_signature
            )

            PaymentLog.objects.create(
                payment=payment,
                event_type="verification_attempt",
                payload=f"razorpay_payment_id: {razorpay_payment_id}, razorpay_order_id: {razorpay_order_id}",
                status="success" if success else "error"
            )

            if not success:
                payment.payment_status = "failed"
                payment.save(update_fields=["payment_status"])
                messages.error(request, f"Payment verification failed: {error}")
                return redirect("payments:payment_failed", pk=booking.id)

            payment.payment_status = "success"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.save()

            from marketplace.models import AvailabilitySlot

            if booking.check_in_date:
                slot = AvailabilitySlot.objects.select_for_update().filter(
                    experience=booking.experience,
                    date=booking.check_in_date,
                    is_available=True
                ).first()

                if slot:
                    available_capacity = slot.capacity - slot.booked_count
                    if booking.guests_count > available_capacity:
                        payment.payment_status = "failed"
                        payment.save(update_fields=["payment_status"])
                        messages.error(request, "This slot is no longer available in the requested capacity.")
                        return redirect("payments:payment_failed", pk=booking.id)

                    slot.booked_count += booking.guests_count
                    if slot.booked_count >= slot.capacity:
                        slot.is_available = False
                    slot.save()

            platform_fee_percentage = decimal.Decimal("0.15")
            total_price_dec = decimal.Decimal(str(booking.total_price))
            booking.platform_fee = total_price_dec * platform_fee_percentage
            booking.host_payout = total_price_dec - booking.platform_fee
            booking.total_paid = booking.total_price
            booking.booking_status = "confirmed"
            booking.save()

            calculate_ledger_entries(booking, reference_id=razorpay_payment_id)

        try:
            send_payment_success_email(booking)
            send_host_new_booking_email(booking)

            from chat.utils import send_realtime_notification

            if booking.user:
                send_realtime_notification(
                    user_id=booking.user.id,
                    title="Payment Successful",
                    message=f"Your payment for {booking.experience.title} was successful.",
                    link="/my-bookings/"
                )

            if booking.experience.host:
                send_realtime_notification(
                    user_id=booking.experience.host.id,
                    title="New Booking Confirmed",
                    message=f"{booking.traveler_name} booked {booking.experience.title}.",
                    link="/dashboard/host/"
                )

        except Exception as e:
            logger.error(f"Error sending payment notifications: {e}")

        messages.success(request, "Payment successful! Your booking is confirmed.")
        return redirect(f"/booking-success/?booking_id={booking.id}")

    except Exception as e:
        logger.exception("Unexpected checkout_verify failure")
        messages.error(request, f"An unexpected error occurred: {e}")
        return redirect("home")


@login_required
def payment_failed(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    return render(request, "marketplace/payment_failed.html", {"booking": booking})


@login_required
def retry_payment(request, booking_id):
    """
    Allows a user to retry a failed payment.
    Clears the existing failed payment and generates a new razorpay order.
    """
    if request.method != "POST":
        return redirect("my_bookings")

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    with transaction.atomic():
        Payment.objects.filter(booking=booking, payment_status="failed").delete()

        if booking.booking_status in ["cancelled", "pending", "payment_processing", "refunded"]:
            booking.booking_status = "payment_processing"
            booking.save(update_fields=["booking_status"])

    return redirect("checkout", pk=booking.id)