"""
Check-in / verification service for Routeless bookings.

Handles:
- Generating 6-digit check-in codes + UUID tokens after payment success
- Validating check-in attempts (ownership, status, date window, rate-limit)
- Performing the check-in state transition
- Generating QR code data URIs for customer booking passes
"""

import io
import base64
import logging
import random
import string
import uuid
from datetime import date

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults (overridable via settings.CHECKIN_CONFIG)
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "allow_on_date": True,       # allow check-in any time on check_in_date
    "hours_before": 2,           # used if start_time exists (future)
    "hours_after": 4,            # used if start_time exists (future)
    "max_attempts": 10,          # max failed attempts per booking
}


def _get_config():
    return {**_DEFAULTS, **getattr(settings, "CHECKIN_CONFIG", {})}


# ---------------------------------------------------------------------------
# Generate credentials (called after payment success — idempotent)
# ---------------------------------------------------------------------------
def generate_checkin_credentials(booking):
    """
    Assign a 6-digit code and UUID token to a confirmed booking.
    Idempotent: if credentials already exist, this is a no-op.
    """
    if booking.checkin_code and booking.checkin_token:
        return  # already generated

    if booking.booking_status not in ("confirmed", "checked_in", "completed"):
        logger.warning(
            "Skipping checkin credential generation for booking #%s (status=%s)",
            booking.id, booking.booking_status,
        )
        return

    # Generate unique 6-digit numeric code
    for _ in range(20):  # retry to avoid collision
        code = "".join(random.choices(string.digits, k=6))
        from marketplace.models import Booking
        if not Booking.objects.filter(checkin_code=code).exclude(pk=booking.pk).exists():
            break
    else:
        # extremely unlikely — fallback
        code = "".join(random.choices(string.digits, k=6))

    booking.checkin_code = code
    booking.checkin_token = uuid.uuid4()
    booking.save(update_fields=["checkin_code", "checkin_token", "updated_at"])

    logger.info(
        "Generated check-in credentials for booking #%s (code=%s)",
        booking.id, code,
    )


# ---------------------------------------------------------------------------
# Validate check-in attempt
# ---------------------------------------------------------------------------
def validate_checkin(code_or_token, host_user):
    """
    Validate a check-in code or token submitted by a host.

    Returns (booking, errors) where errors is a list of strings.
    If errors is non-empty, check-in should not proceed.
    """
    from marketplace.models import Booking

    errors = []
    booking = None
    config = _get_config()

    # --- Find booking ---
    code_or_token = (code_or_token or "").strip()
    if not code_or_token:
        return None, ["Please enter a check-in code."]

    # Try as 6-digit code first, then as UUID token
    if len(code_or_token) == 6 and code_or_token.isdigit():
        booking = Booking.objects.filter(checkin_code=code_or_token).select_related(
            "experience", "experience__host", "user"
        ).first()
    else:
        try:
            token_uuid = uuid.UUID(code_or_token)
            booking = Booking.objects.filter(checkin_token=token_uuid).select_related(
                "experience", "experience__host", "user"
            ).first()
        except (ValueError, AttributeError):
            pass

    if not booking:
        return None, ["Invalid check-in code. No matching booking found."]

    # --- Track attempt ---
    booking.checkin_attempt_count += 1
    booking.last_checkin_attempt_at = timezone.now()
    booking.save(update_fields=["checkin_attempt_count", "last_checkin_attempt_at"])

    # --- Rate limit ---
    if booking.checkin_attempt_count > config["max_attempts"]:
        errors.append(
            f"Too many verification attempts ({booking.checkin_attempt_count}). "
            "Please contact support."
        )
        return booking, errors

    # --- Host ownership ---
    if booking.experience.host != host_user:
        errors.append("This booking belongs to a different host.")
        return None, errors  # Don't reveal booking details

    # --- Booking status checks ---
    if booking.booking_status in ("cancelled", "refunded"):
        errors.append(f"This booking is {booking.booking_status}. Check-in is not allowed.")
        return booking, errors

    if booking.booking_status == "checked_in":
        errors.append("This booking has already been checked in.")
        return booking, errors

    if booking.booking_status == "completed":
        errors.append("This booking is already completed.")
        return booking, errors

    if booking.booking_status != "confirmed":
        errors.append(f"Booking status is '{booking.booking_status}'. Only confirmed bookings can be checked in.")
        return booking, errors

    # --- Payment check ---
    try:
        payment = booking.payment
        if payment.payment_status != "success":
            errors.append("Payment has not been completed for this booking.")
            return booking, errors
    except Exception:
        errors.append("No payment record found for this booking.")
        return booking, errors

    # --- Date window check ---
    today = date.today()
    if config.get("allow_on_date", True):
        if booking.check_in_date != today:
            if booking.check_in_date > today:
                errors.append(
                    f"Check-in is not available yet. The booking date is {booking.check_in_date.strftime('%d %b %Y')}."
                )
            else:
                errors.append(
                    f"Check-in window has passed. The booking date was {booking.check_in_date.strftime('%d %b %Y')}."
                )
            return booking, errors

    return booking, errors


# ---------------------------------------------------------------------------
# Perform check-in
# ---------------------------------------------------------------------------
@transaction.atomic
def perform_checkin(booking, host_user, method="manual_code", notes=""):
    """
    Mark a validated booking as checked in.
    """
    from marketplace.models import Booking

    booking = Booking.objects.select_for_update().get(pk=booking.pk)

    # Double-check status hasn't changed
    if booking.booking_status != "confirmed":
        raise ValueError(f"Cannot check in: booking status is '{booking.booking_status}'")

    now = timezone.now()
    booking.booking_status = "checked_in"
    booking.checkin_status = "checked_in"
    booking.checked_in_at = now
    booking.checked_in_by = host_user
    booking.checkin_method = method
    booking.checkin_notes = notes
    booking.save()

    logger.info(
        "Booking #%s checked in by host %s (method=%s)",
        booking.id, host_user.username, method,
    )
    return booking


# ---------------------------------------------------------------------------
# QR code generation
# ---------------------------------------------------------------------------
def generate_qr_data_uri(booking):
    """
    Generate a QR code as a base64 PNG data URI for a booking's check-in token.
    Returns a string like 'data:image/png;base64,...' or empty string on failure.
    """
    if not booking.checkin_token:
        return ""

    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M

        # Encode the token as a simple verification URL / string
        qr_content = f"ROUTELESS-CHECKIN:{booking.checkin_token}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#1a1a2e", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode("utf-8")

        return f"data:image/png;base64,{encoded}"

    except Exception as e:
        logger.error("QR generation failed for booking #%s: %s", booking.id, e)
        return ""
