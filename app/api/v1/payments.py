from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, PaginationDep, StaffUser
from app.api.pagination import paginate
from app.models import Invoice, Payment, PaymentMethod
from app.schemas.common import Page
from app.schemas.invoice import PaymentOut

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=Page[PaymentOut])
def list_payments(
    staff: StaffUser,
    db: DbSession,
    pagination: PaginationDep,
    invoice_id: int | None = None,
    method: PaymentMethod | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    stmt = select(Payment)
    if invoice_id is not None:
        stmt = stmt.where(Payment.invoice_id == invoice_id)
    if method is not None:
        stmt = stmt.where(Payment.method == method)
    if date_from is not None:
        stmt = stmt.where(Payment.paid_on >= date_from)
    if date_to is not None:
        stmt = stmt.where(Payment.paid_on <= date_to)
    stmt = stmt.order_by(Payment.paid_on.desc(), Payment.id.desc())
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, staff: StaffUser, db: DbSession):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    return payment


@router.get("/{payment_id}/invoice", response_model=dict)
def payment_invoice(payment_id: int, staff: StaffUser, db: DbSession):
    """Tiny convenience hop for the UI: which invoice did this payment settle?"""
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    invoice = db.get(Invoice, payment.invoice_id)
    return {
        "payment_id": payment.id,
        "invoice_id": invoice.id if invoice else None,
        "invoice_number": invoice.number if invoice else None,
        "invoice_status": invoice.status.value if invoice else None,
    }
