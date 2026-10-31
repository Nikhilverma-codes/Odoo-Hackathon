from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import or_, select

from app.api.deps import (
    CurrentUser,
    DbSession,
    PaginationDep,
    StaffUser,
    ensure_customer_access,
)
from app.api.pagination import paginate
from app.models import Customer, Invoice, InvoiceStatus, Role
from app.schemas.common import Page
from app.schemas.invoice import (
    BillingRunIn,
    BillingRunOut,
    CancelInvoiceIn,
    InvoiceCreateIn,
    InvoiceOut,
    InvoiceUpdateIn,
    PaymentCreateIn,
    PaymentOut,
)
from app.services import billing, invoices as invoice_service
from app.services import subscriptions as subscription_service

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _get_visible(db: DbSession, invoice_id: int, user: CurrentUser) -> Invoice:
    invoice = invoice_service.get_invoice(db, invoice_id)
    ensure_customer_access(user, invoice.customer_id)
    return invoice


@router.post("/run-billing", response_model=BillingRunOut)
def run_billing(payload: BillingRunIn, staff: StaffUser, db: DbSession):
    """Invoice every subscription that is due. Idempotent: each period bills once."""
    result = billing.run_billing(
        db,
        as_of=payload.as_of or date.today(),
        auto_confirm=payload.auto_confirm,
        dry_run=payload.dry_run,
    )
    if payload.dry_run:
        db.rollback()
    else:
        db.commit()
    return result


@router.get("", response_model=Page[InvoiceOut])
def list_invoices(
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    status: InvoiceStatus | None = None,
    customer_id: int | None = None,
    subscription_id: int | None = None,
    overdue: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
):
    stmt = select(Invoice)
    if user.role is Role.CUSTOMER:
        stmt = stmt.where(Invoice.customer_id == user.customer_id)
    elif customer_id is not None:
        stmt = stmt.where(Invoice.customer_id == customer_id)

    if status is not None:
        stmt = stmt.where(Invoice.status == status)
    if subscription_id is not None:
        stmt = stmt.where(Invoice.subscription_id == subscription_id)
    if overdue:
        stmt = stmt.where(
            Invoice.status == InvoiceStatus.CONFIRMED,
            Invoice.due_date < date.today(),
            Invoice.total > Invoice.amount_paid,
        )
    if date_from is not None:
        stmt = stmt.where(Invoice.issue_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Invoice.issue_date <= date_to)
    if q:
        needle = f"%{q.lower()}%"
        stmt = stmt.join(Customer, Customer.id == Invoice.customer_id).where(
            or_(Invoice.number.ilike(needle), Customer.name.ilike(needle))
        )

    stmt = stmt.order_by(Invoice.issue_date.desc(), Invoice.id.desc())
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreateIn, staff: StaffUser, db: DbSession):
    subscription = subscription_service.get_subscription(db, payload.subscription_id)
    period_start = (
        payload.period_start
        or subscription.next_billing_date
        or subscription.current_period_start
        or date.today()
    )
    _, period_end, _ = billing.next_period(subscription.plan, period_start)
    if payload.period_end:
        period_end = payload.period_end

    try:
        invoice = billing.build_invoice(
            db,
            subscription,
            period_start,
            period_end,
            issue_date=payload.issue_date,
            due_date=payload.due_date,
            auto_confirm=payload.auto_confirm,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    if subscription.next_billing_date == period_start:
        billing.advance_subscription(db, subscription)
    db.commit()
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, user: CurrentUser, db: DbSession):
    return _get_visible(db, invoice_id, user)


@router.patch("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: int, payload: InvoiceUpdateIn, staff: StaffUser, db: DbSession
):
    invoice = invoice_service.get_invoice(db, invoice_id)
    if invoice.status is not InvoiceStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only draft invoices can be edited")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)
    db.commit()
    return invoice


@router.post("/{invoice_id}/confirm", response_model=InvoiceOut)
def confirm_invoice(invoice_id: int, staff: StaffUser, db: DbSession):
    invoice = invoice_service.get_invoice(db, invoice_id)
    invoice_service.confirm_invoice(db, invoice)
    db.commit()
    return invoice


@router.post("/{invoice_id}/cancel", response_model=InvoiceOut)
def cancel_invoice(
    invoice_id: int, payload: CancelInvoiceIn, staff: StaffUser, db: DbSession
):
    invoice = invoice_service.get_invoice(db, invoice_id)
    invoice_service.cancel_invoice(db, invoice, payload.reason)
    db.commit()
    return invoice


@router.post("/{invoice_id}/send", response_model=InvoiceOut)
def send_invoice(invoice_id: int, staff: StaffUser, db: DbSession):
    invoice = invoice_service.get_invoice(db, invoice_id)
    invoice_service.send_invoice(db, invoice)
    db.commit()
    return invoice


@router.get("/{invoice_id}/print", response_class=HTMLResponse)
def print_invoice(invoice_id: int, user: CurrentUser, db: DbSession):
    invoice = _get_visible(db, invoice_id, user)
    return HTMLResponse(invoice_service.invoice_document(invoice))


@router.post("/{invoice_id}/payments", response_model=PaymentOut, status_code=201)
def record_payment(
    invoice_id: int, payload: PaymentCreateIn, staff: StaffUser, db: DbSession
):
    invoice = invoice_service.get_invoice(db, invoice_id)
    payment = invoice_service.record_payment(db, invoice, payload, staff)
    db.commit()
    return payment
