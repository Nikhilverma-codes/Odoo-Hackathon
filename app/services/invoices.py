"""Invoice state changes and payment recording."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.money import money
from app.db.base import utcnow
from app.models import Invoice, InvoiceStatus, Payment, PaymentMethod, User
from app.schemas.invoice import PaymentCreateIn
from app.services.email import send_email


def get_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    return invoice


def confirm_invoice(db: Session, invoice: Invoice) -> Invoice:
    if invoice.status is InvoiceStatus.CANCELLED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A cancelled invoice cannot be confirmed")
    if invoice.status is not InvoiceStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only draft invoices can be confirmed")
    invoice.status = InvoiceStatus.CONFIRMED
    invoice.confirmed_at = utcnow()
    db.flush()
    return invoice


def cancel_invoice(db: Session, invoice: Invoice, reason: str | None = None) -> Invoice:
    if invoice.status is InvoiceStatus.PAID:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A paid invoice cannot be cancelled")
    if invoice.status is InvoiceStatus.CANCELLED:
        return invoice
    invoice.status = InvoiceStatus.CANCELLED
    invoice.cancelled_at = utcnow()
    invoice.cancelled_reason = reason
    db.flush()
    return invoice


def send_invoice(db: Session, invoice: Invoice) -> Invoice:
    if invoice.status is InvoiceStatus.DRAFT:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Confirm the invoice before sending it"
        )
    if invoice.status is InvoiceStatus.CANCELLED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cancelled invoices cannot be sent")
    invoice.sent_at = utcnow()
    send_email(
        to=invoice.customer.email,
        subject=f"Invoice {invoice.number} from Brightloop",
        body=(
            f"Hello {invoice.customer.name},\n\n"
            f"Invoice {invoice.number} for {invoice.total} {invoice.currency} "
            f"is due on {invoice.due_date.isoformat()}.\n\nThank you."
        ),
    )
    db.flush()
    return invoice


def record_payment(
    db: Session, invoice: Invoice, payload: PaymentCreateIn, actor: User | None
) -> Payment:
    if invoice.status in (InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Payments can only be recorded against confirmed invoices"
        )

    amount = money(payload.amount)
    if amount > invoice.amount_due:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Amount exceeds the outstanding balance of {invoice.amount_due}",
        )

    payment = Payment(
        invoice_id=invoice.id,
        method=payload.method or PaymentMethod.BANK_TRANSFER,
        amount=amount,
        paid_on=payload.paid_on or date.today(),
        reference=payload.reference,
        note=payload.note,
        recorded_by_id=actor.id if actor else None,
    )
    db.add(payment)

    invoice.amount_paid = money(Decimal(invoice.amount_paid) + amount)
    if invoice.amount_paid >= invoice.total:
        invoice.status = InvoiceStatus.PAID
    db.flush()
    return payment


def invoice_document(invoice: Invoice) -> str:
    """Minimal printable HTML - swap for a PDF renderer later."""
    rows = "".join(
        f"<tr><td>{line.description}</td><td>{line.quantity}</td>"
        f"<td>{line.unit_price}</td><td>{line.discount_amount}</td>"
        f"<td>{line.tax_rate}%</td><td>{line.total}</td></tr>"
        for line in invoice.lines
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Invoice {invoice.number}</title>
<style>
  body{{font-family:system-ui,sans-serif;max-width:760px;margin:40px auto;color:#111}}
  table{{width:100%;border-collapse:collapse;margin-top:24px}}
  th,td{{text-align:left;padding:8px;border-bottom:1px solid #e5e7eb}}
  tfoot td{{font-weight:600}}
  .muted{{color:#6b7280}}
</style></head>
<body>
  <h1>Invoice {invoice.number}</h1>
  <p class="muted">Issued {invoice.issue_date} &middot; Due {invoice.due_date} &middot;
     Status: {invoice.status.value}</p>
  <h3>{invoice.customer.name}</h3>
  <p class="muted">{invoice.customer.billing_address or ''}</p>
  <table>
    <thead><tr><th>Description</th><th>Qty</th><th>Unit</th><th>Discount</th>
      <th>Tax</th><th>Total</th></tr></thead>
    <tbody>{rows}</tbody>
    <tfoot>
      <tr><td colspan="5">Subtotal</td><td>{invoice.subtotal} {invoice.currency}</td></tr>
      <tr><td colspan="5">Discounts</td><td>-{invoice.discount_total} {invoice.currency}</td></tr>
      <tr><td colspan="5">Tax</td><td>{invoice.tax_total} {invoice.currency}</td></tr>
      <tr><td colspan="5">Total</td><td>{invoice.total} {invoice.currency}</td></tr>
      <tr><td colspan="5">Paid</td><td>{invoice.amount_paid} {invoice.currency}</td></tr>
      <tr><td colspan="5">Outstanding</td><td>{invoice.amount_due} {invoice.currency}</td></tr>
    </tfoot>
  </table>
</body></html>"""
