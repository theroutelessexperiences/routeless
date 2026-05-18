"""
Server-side GST / tax calculation service.

All arithmetic uses ``Decimal`` with ``ROUND_HALF_UP`` to avoid
floating-point drift.  The module is intentionally free of database
calls so it can be unit-tested in isolation.
"""

from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
_TWO_PLACES = Decimal("0.01")


def _r(value: Decimal) -> Decimal:
    """Round a Decimal to two decimal places (ROUND_HALF_UP)."""
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _get_default_gst_rate() -> Decimal:
    """Return the default GST rate from project settings."""
    cfg = getattr(settings, "ROUTELESS_TAX_CONFIG", {})
    return Decimal(str(cfg.get("DEFAULT_GST_RATE", "5.00")))


def _is_gst_enabled() -> bool:
    cfg = getattr(settings, "ROUTELESS_TAX_CONFIG", {})
    return bool(cfg.get("GST_ENABLED", True))


# -------------------------------------------------------------------
# Result dataclass
# -------------------------------------------------------------------
@dataclass(frozen=True)
class TaxBreakup:
    """Immutable snapshot of a price + tax calculation."""

    base_amount: Decimal          # price per unit (per person per day)
    quantity: int                 # guest count
    days: int                     # number of days
    subtotal_amount: Decimal      # base × quantity × days
    discount_amount: Decimal      # any discount applied
    taxable_amount: Decimal       # subtotal − discount
    gst_rate: Decimal             # e.g. 5.00
    cgst_amount: Decimal          # taxable × gst_rate / 2 / 100
    sgst_amount: Decimal          # same
    igst_amount: Decimal          # 0 for now (intra-state assumed)
    total_tax_amount: Decimal     # cgst + sgst + igst
    total_payable_amount: Decimal # taxable + tax
    amount_in_paise: int          # total_payable × 100 (for Razorpay)
    tax_label: str                # e.g. "GST @ 5%"

    def as_dict(self) -> dict:
        """Return a plain dict (safe for template / JSON contexts)."""
        d = asdict(self)
        # Convert Decimal → str for JSON serialisation safety
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = str(v)
        return d


# -------------------------------------------------------------------
# Main calculation function
# -------------------------------------------------------------------
def calculate_booking_tax(
    base_amount,
    quantity: int = 1,
    days: int = 1,
    discount: Decimal | int | float | str = 0,
    gst_rate: Decimal | None = None,
) -> TaxBreakup:
    """
    Calculate the full price + tax breakup for a booking.

    Parameters
    ----------
    base_amount : Decimal-like
        Per-person-per-day price (the experience's ``price_per_person``
        or the dynamic price).
    quantity : int
        Number of guests.
    days : int
        Number of days/nights.
    discount : Decimal-like
        Flat discount to apply *before* tax.
    gst_rate : Decimal or None
        Override the GST percentage.  ``None`` → use default from
        settings.

    Returns
    -------
    TaxBreakup
        Immutable dataclass with every line-item amount.
    """
    base_amount = Decimal(str(base_amount))
    discount = Decimal(str(discount))

    if gst_rate is None:
        gst_rate = _get_default_gst_rate()
    else:
        gst_rate = Decimal(str(gst_rate))

    # Guard against nonsensical inputs
    if quantity < 0:
        quantity = 0
    if days < 0:
        days = 0
    if discount < 0:
        discount = Decimal("0")

    subtotal = _r(base_amount * quantity * days)
    discount = _r(min(discount, subtotal))  # discount cannot exceed subtotal
    taxable = _r(subtotal - discount)

    if _is_gst_enabled() and gst_rate > 0:
        half_rate = _r(gst_rate / Decimal("2"))
        cgst = _r(taxable * half_rate / Decimal("100"))
        sgst = _r(taxable * half_rate / Decimal("100"))
        igst = Decimal("0.00")
        total_tax = _r(cgst + sgst + igst)
        label = f"GST @ {gst_rate.normalize()}%"
    else:
        cgst = sgst = igst = total_tax = Decimal("0.00")
        label = "No tax"

    total_payable = _r(taxable + total_tax)
    paise = int(total_payable * 100)

    return TaxBreakup(
        base_amount=_r(base_amount),
        quantity=quantity,
        days=days,
        subtotal_amount=subtotal,
        discount_amount=discount,
        taxable_amount=taxable,
        gst_rate=_r(gst_rate),
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        total_tax_amount=total_tax,
        total_payable_amount=total_payable,
        amount_in_paise=paise,
        tax_label=label,
    )
