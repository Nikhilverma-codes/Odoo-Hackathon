from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.models.invoice import InvoiceStatus, PaymentMethod
from app.schemas.common import Money, Rate, Schema
from app.schemas.plan import PlanShort
from app.schemas.product import ProductShort, VariantOut
from app.schemas.user import CustomerShort


# --------------------------------------------------------------------------- #
# Quotation templates
# --------------------------------------------------------------------------- #
class TemplateLineIn(Schema):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(default=1, ge=1)
    unit_price: Money | None = Field(default=None, ge=0)


class TemplateLineOut(Schema):
    id: int
    product: ProductShort
    variant: VariantOut | None
    quantity: int
    unit_price: Money | None


class TemplateIn(Schema):
    name: str = Field(min_length=1, max_length=160)
    plan_id: int
    validity_days: int = Field(default=30, ge=1, le=365)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    notes: str | None = None
    is_active: bool = True
    lines: list[TemplateLineIn] = Field(default_factory=list)


class TemplateOut(Schema):
    id: int
    name: str
    plan: PlanShort
    validity_days: int
    payment_terms_days: int
    notes: str | None
    is_active: bool
    lines: list[TemplateLineOut]
    created_at: datetime


# --------------------------------------------------------------------------- #
# Invoices & payments
# --------------------------------------------------------------------------- #
class InvoiceLineOut(Schema):
    id: int
    product: ProductShort | None
    description: str
    quantity: int
    unit_price: Money
    tax_rate: Rate
    subtotal: Money
    discount_amount: Money
    tax_amount: Money
    total: Money


class PaymentOut(Schema):
    id: int
    method: PaymentMethod
    amount: Money
    paid_on: date
    reference: str | None
    note: str | None
    created_at: datetime


class InvoiceOut(Schema):
    id: int
    number: str
    status: InvoiceStatus
    customer: CustomerShort
    subscription_id: int | None
    issue_date: date
    due_date: date
    period_start: date | None
    period_end: date | None
    currency: str
    subtotal: Money
    discount_total: Money
    tax_total: Money
    total: Money
    amount_paid: Money
    amount_due: Money
    is_overdue: bool
    notes: str | None
    sent_at: datetime | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancelled_reason: str | None
    lines: list[InvoiceLineOut]
    payments: list[PaymentOut]
    created_at: datetime


class InvoiceCreateIn(Schema):
    subscription_id: int
    issue_date: date | None = None
    due_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    notes: str | None = None
    auto_confirm: bool = False


class InvoiceUpdateIn(Schema):
    due_date: date | None = None
    notes: str | None = None


class PaymentCreateIn(Schema):
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    amount: Money = Field(gt=0)
    paid_on: date | None = None
    reference: str | None = Field(default=None, max_length=120)
    note: str | None = None


class CancelInvoiceIn(Schema):
    reason: str | None = Field(default=None, max_length=255)


class BillingRunIn(Schema):
    as_of: date | None = None
    auto_confirm: bool = True
    dry_run: bool = False


class BillingRunOut(Schema):
    as_of: date
    dry_run: bool
    scanned: int
    invoiced: int
    skipped: int
    closed: int
    invoice_ids: list[int]
    invoice_numbers: list[str]
    errors: list[str]
