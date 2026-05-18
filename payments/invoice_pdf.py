"""
Invoice PDF generation using ReportLab.

Generates a clean, Routeless-branded PDF invoice and saves it
to the Invoice model's ``pdf_file`` field.
"""

import io
import logging
from decimal import Decimal

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def _fmt(amount) -> str:
    """Format a Decimal as ₹X,XX,XXX.XX (Indian numbering)."""
    try:
        amt = Decimal(str(amount))
        sign = "-" if amt < 0 else ""
        amt = abs(amt)
        integer_part = int(amt)
        decimal_part = f"{amt - integer_part:.2f}"[1:]  # .XX

        s = str(integer_part)
        if len(s) <= 3:
            formatted = s
        else:
            last_three = s[-3:]
            remaining = s[:-3]
            # Indian grouping: pairs from right
            groups = []
            while remaining:
                groups.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            formatted = ",".join(groups) + "," + last_three

        return f"{sign}₹{formatted}{decimal_part}"
    except Exception:
        return f"₹{amount}"


def generate_invoice_pdf(invoice) -> bool:
    """
    Generate a PDF for the given Invoice instance and save it
    to ``invoice.pdf_file``.

    Returns True on success, False on failure.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        logger.error("reportlab is not installed — cannot generate PDF invoice")
        return False

    try:
        buf = io.BytesIO()
        width, height = A4
        c = canvas.Canvas(buf, pagesize=A4)

        # Margins
        left = 25 * mm
        right = width - 25 * mm
        top = height - 20 * mm
        content_width = right - left

        # ── Brand header ──────────────────────────────────────────────
        c.setFillColor(colors.HexColor("#2B6777"))
        c.rect(0, height - 35 * mm, width, 35 * mm, fill=True, stroke=False)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(left, height - 22 * mm, "THE ROUTELESS")
        c.setFont("Helvetica", 9)
        c.drawString(left, height - 28 * mm, "Travel Experiences Marketplace")

        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(right, height - 22 * mm, "TAX INVOICE")

        y = height - 45 * mm

        # ── Invoice meta ──────────────────────────────────────────────
        c.setFillColor(colors.HexColor("#333333"))
        meta_items = [
            ("Invoice No.", invoice.invoice_number),
            ("Date", invoice.invoice_date.strftime("%d %b %Y")),
            ("Booking ID", f"#{invoice.booking_id}"),
        ]
        if invoice.razorpay_payment_id:
            meta_items.append(("Payment Ref", invoice.razorpay_payment_id))

        c.setFont("Helvetica-Bold", 9)
        for label, val in meta_items:
            c.drawString(left, y, f"{label}:")
            c.setFont("Helvetica", 9)
            c.drawString(left + 30 * mm, y, val)
            c.setFont("Helvetica-Bold", 9)
            y -= 5 * mm

        y -= 5 * mm

        # ── Supplier / Customer ───────────────────────────────────────
        col_mid = left + content_width / 2

        # Supplier
        c.setFillColor(colors.HexColor("#2B6777"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left, y, "FROM (Supplier)")
        y -= 5 * mm
        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, invoice.supplier_name)
        y -= 4.5 * mm
        c.setFont("Helvetica", 8)
        if invoice.supplier_gstin:
            c.drawString(left, y, f"GSTIN: {invoice.supplier_gstin}")
            y -= 4 * mm
        if invoice.supplier_address:
            for line in invoice.supplier_address.split("\n")[:3]:
                c.drawString(left, y, line.strip())
                y -= 4 * mm
        if invoice.supplier_state:
            c.drawString(left, y, f"State: {invoice.supplier_state}")
            if invoice.supplier_state_code:
                c.drawString(left + 50 * mm, y, f"Code: {invoice.supplier_state_code}")
            y -= 4 * mm

        # Customer (right column)
        cy = y + 22 * mm  # align with supplier start
        c.setFillColor(colors.HexColor("#2B6777"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(col_mid, cy, "TO (Customer)")
        cy -= 5 * mm
        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(col_mid, cy, invoice.customer_name)
        cy -= 4.5 * mm
        c.setFont("Helvetica", 8)
        c.drawString(col_mid, cy, invoice.customer_email)
        cy -= 4 * mm
        if invoice.customer_phone:
            c.drawString(col_mid, cy, f"Phone: {invoice.customer_phone}")
            cy -= 4 * mm
        if invoice.customer_gstin:
            c.drawString(col_mid, cy, f"GSTIN: {invoice.customer_gstin}")
            cy -= 4 * mm

        y -= 8 * mm

        # ── Divider ──────────────────────────────────────────────────
        c.setStrokeColor(colors.HexColor("#E0E0E0"))
        c.setLineWidth(0.5)
        c.line(left, y, right, y)
        y -= 8 * mm

        # ── Service description ──────────────────────────────────────
        c.setFillColor(colors.HexColor("#2B6777"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, "Service Details")
        y -= 6 * mm

        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica", 9)
        # Wrap long text
        desc = invoice.service_description
        max_chars = 90
        while desc:
            c.drawString(left, y, desc[:max_chars])
            desc = desc[max_chars:]
            y -= 4.5 * mm

        c.setFont("Helvetica", 8)
        c.drawString(left, y, f"SAC Code: {invoice.sac_code}")
        y -= 8 * mm

        # ── Price breakup table ──────────────────────────────────────
        c.setStrokeColor(colors.HexColor("#2B6777"))
        c.setLineWidth(0.5)

        # Table header
        table_top = y
        c.setFillColor(colors.HexColor("#2B6777"))
        c.rect(left, y - 6 * mm, content_width, 6 * mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left + 3 * mm, y - 4.5 * mm, "Description")
        c.drawRightString(right - 3 * mm, y - 4.5 * mm, "Amount")

        y -= 10 * mm

        # Table rows
        rows = [
            ("Taxable Amount", _fmt(invoice.taxable_amount)),
        ]

        if invoice.cgst_amount:
            half_rate = invoice.gst_rate / 2
            rows.append((f"CGST @ {half_rate}%", _fmt(invoice.cgst_amount)))
            rows.append((f"SGST @ {half_rate}%", _fmt(invoice.sgst_amount)))

        if invoice.igst_amount:
            rows.append((f"IGST @ {invoice.gst_rate}%", _fmt(invoice.igst_amount)))

        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica", 9)
        for label, val in rows:
            c.drawString(left + 3 * mm, y, label)
            c.drawRightString(right - 3 * mm, y, val)
            y -= 5.5 * mm

        # Divider before total
        y -= 1 * mm
        c.setStrokeColor(colors.HexColor("#2B6777"))
        c.setLineWidth(1)
        c.line(left, y, right, y)
        y -= 6 * mm

        # Total row
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#2B6777"))
        c.drawString(left + 3 * mm, y, "Total Payable")
        c.drawRightString(right - 3 * mm, y, _fmt(invoice.total_amount))
        y -= 4 * mm

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(left + 3 * mm, y, f"(Inclusive of {invoice.gst_rate}% GST)")
        y -= 12 * mm

        # ── Payment info ─────────────────────────────────────────────
        if invoice.razorpay_payment_id:
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(colors.HexColor("#2B6777"))
            c.drawString(left, y, "Payment Information")
            y -= 5 * mm
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.HexColor("#333333"))
            c.drawString(left, y, f"Razorpay Payment ID: {invoice.razorpay_payment_id}")
            y -= 4 * mm
            if invoice.razorpay_order_id:
                c.drawString(left, y, f"Razorpay Order ID: {invoice.razorpay_order_id}")
                y -= 4 * mm
            c.drawString(left, y, "Payment Mode: Online (Razorpay)")
            y -= 10 * mm

        # ── Footer ───────────────────────────────────────────────────
        footer_y = 25 * mm
        c.setStrokeColor(colors.HexColor("#E0E0E0"))
        c.setLineWidth(0.5)
        c.line(left, footer_y + 5 * mm, right, footer_y + 5 * mm)

        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#999999"))
        c.drawCentredString(
            width / 2, footer_y,
            "This is a computer-generated invoice and does not require a physical signature.",
        )
        c.drawCentredString(
            width / 2, footer_y - 4 * mm,
            f"© {invoice.invoice_date.year} The Routeless — {invoice.supplier_name}",
        )

        c.showPage()
        c.save()

        # Save to model
        buf.seek(0)
        filename = f"invoice_{invoice.invoice_number.replace('/', '_')}.pdf"
        invoice.pdf_file.save(filename, ContentFile(buf.read()), save=True)
        invoice.status = "generated"
        invoice.save(update_fields=["status"])

        logger.info("Generated PDF for invoice %s", invoice.invoice_number)
        return True

    except Exception:
        logger.exception("Failed to generate PDF for invoice %s", invoice.invoice_number)
        return False
