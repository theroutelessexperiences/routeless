"""
Invoice creation service.

Provides idempotent invoice creation and sequential invoice numbering.
"""

import logging
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from .models import Invoice, InvoiceCounter, Payment, VendorSettlement

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _get_financial_year(d: date) -> str:
    """
    Return the Indian financial-year string for a given date.
    FY runs April → March.  E.g. 15 Jan 2026 → "25-26",
    10 May 2026 → "26-27".
    """
    if d.month >= 4:
        start_year = d.year
    else:
        start_year = d.year - 1
    end_year = start_year + 1
    return f"{start_year % 100:02d}-{end_year % 100:02d}"


def _tax_cfg():
    return getattr(settings, "ROUTELESS_TAX_CONFIG", {})


# -------------------------------------------------------------------
# Sequential invoice-number generator
# -------------------------------------------------------------------
def generate_invoice_number(invoice_date: date | None = None) -> tuple[str, str]:
    """
    Thread-safe sequential invoice numbering.

    Returns (invoice_number, financial_year) e.g. ("RTL/25-26/000001", "25-26").
    Uses ``select_for_update`` on ``InvoiceCounter`` to serialise.
    """
    if invoice_date is None:
        invoice_date = date.today()

    fy = _get_financial_year(invoice_date)
    prefix = _tax_cfg().get("INVOICE_PREFIX", "RTL")

    with transaction.atomic():
        counter, _created = InvoiceCounter.objects.select_for_update().get_or_create(
            financial_year=fy,
            defaults={"last_number": 0},
        )
        counter.last_number += 1
        counter.save(update_fields=["last_number"])
        number = f"{prefix}/{fy}/{counter.last_number:06d}"

    return number, fy


# -------------------------------------------------------------------
# Main entry-point: create invoice for a booking
# -------------------------------------------------------------------
def create_invoice_for_booking(booking, payment: Payment) -> Invoice:
    """
    Idempotent invoice creation.

    If an invoice already exists for the booking, returns it.
    Otherwise builds a new one from the payment's tax snapshot.
    """
    # Idempotency check
    existing = Invoice.objects.filter(booking=booking).first()
    if existing:
        logger.info("Invoice %s already exists for booking #%s", existing.invoice_number, booking.id)
        return existing

    cfg = _tax_cfg()
    today = date.today()
    inv_number, fy = generate_invoice_number(today)

    # Build service description
    experience = booking.experience
    svc_desc = (
        f"{experience.title} — "
        f"{booking.check_in_date.strftime('%d %b %Y')} to "
        f"{booking.check_out_date.strftime('%d %b %Y')}, "
        f"{booking.guests_count} guest(s)"
    )

    invoice = Invoice.objects.create(
        booking=booking,
        payment=payment,
        user=booking.user,
        invoice_number=inv_number,
        invoice_date=today,
        financial_year=fy,
        # Supplier (Routeless)
        supplier_name=cfg.get("SUPPLIER_NAME", "Routeless Travel Pvt. Ltd."),
        supplier_gstin=cfg.get("SUPPLIER_GSTIN", ""),
        supplier_address=cfg.get("SUPPLIER_ADDRESS", ""),
        supplier_state=cfg.get("SUPPLIER_STATE", ""),
        supplier_state_code=cfg.get("SUPPLIER_STATE_CODE", ""),
        # Customer
        customer_name=booking.traveler_name or booking.user.get_full_name() or booking.user.username,
        customer_email=booking.traveler_email or booking.user.email,
        customer_phone=getattr(booking, "traveler_phone", ""),
        customer_billing_address="",
        customer_gstin="",
        # Service
        sac_code=payment.sac_code or cfg.get("DEFAULT_SAC_CODE", "998555"),
        service_description=svc_desc,
        # Amounts from payment snapshot
        taxable_amount=payment.taxable_amount,
        gst_rate=payment.gst_rate,
        cgst_amount=payment.cgst_amount,
        sgst_amount=payment.sgst_amount,
        igst_amount=payment.igst_amount,
        total_tax_amount=payment.total_tax_amount,
        total_amount=payment.total_payable_amount or payment.amount,
        currency=payment.currency,
        # Razorpay refs
        razorpay_order_id=payment.razorpay_order_id or "",
        razorpay_payment_id=payment.razorpay_payment_id or "",
        status="generated",
    )

    # Mark payment as invoice generated
    payment.invoice_generated = True
    payment.save(update_fields=["invoice_generated"])

    logger.info("Created invoice %s for booking #%s", inv_number, booking.id)
    return invoice


# -------------------------------------------------------------------
# Vendor settlement creation
# -------------------------------------------------------------------
def create_vendor_settlement(booking, payment: Payment) -> VendorSettlement:
    """
    Idempotent vendor settlement creation.

    The settlement records how much the vendor should be paid after
    platform commission and GST deduction.
    """
    existing = VendorSettlement.objects.filter(booking=booking).first()
    if existing:
        logger.info("Settlement already exists for booking #%s", booking.id)
        return existing

    cfg = _tax_cfg()
    commission_rate = cfg.get("PLATFORM_COMMISSION_RATE", Decimal("0.15"))

    taxable = payment.taxable_amount or payment.amount
    gst_collected = payment.total_tax_amount or Decimal("0")
    total_paid = payment.total_payable_amount or payment.amount
    commission = (taxable * commission_rate).quantize(Decimal("0.01"))
    vendor_payout = taxable - commission

    settlement = VendorSettlement.objects.create(
        booking=booking,
        vendor=booking.experience.host,
        customer_total_paid=total_paid,
        taxable_amount=taxable,
        gst_amount_collected=gst_collected,
        routeless_commission=commission,
        vendor_payout_amount=vendor_payout,
        payout_status="pending",
    )

    logger.info(
        "Created vendor settlement for booking #%s: payout=₹%s, commission=₹%s",
        booking.id, vendor_payout, commission,
    )
    return settlement
