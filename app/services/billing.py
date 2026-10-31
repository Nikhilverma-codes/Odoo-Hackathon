"""Dates, billing windows and the invoice generation engine."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.money import ZERO, allocate, money, percentage
from app.db.base import utcnow
from app.models import (
    BillingInterval,
    Discount,
    DiscountRedemption,
    DiscountScope,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Plan,
    Subscription,
    SubscriptionStatus,
)
from app.services import numbering


# --------------------------------------------------------------------------- #
# Date arithmetic
# --------------------------------------------------------------------------- #
def add_months(day: date, months: int) -> date:
    year = day.year + (day.month - 1 + months) // 12
    month = (day.month - 1 + months) % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def add_interval(day: date, interval: BillingInterval, count: int = 1) -> date:
    if interval is BillingInterval.DAILY:
        return day + timedelta(days=count)
    if interval is BillingInterval.WEEKLY:
        return day + timedelta(weeks=count)
    if interval is BillingInterval.MONTHLY:
        return add_months(day, count)
    if interval is BillingInterval.YEARLY:
        return add_months(day, 12 * count)
    raise ValueError(f"Unsupported interval: {interval}")


def next_period(plan: Plan, period_start: date) -> tuple[date, date, date]:
    """Return (period_start, period_end_inclusive, next_start)."""
    following = add_interval(period_start, plan.interval)
    return period_start, following - timedelta(days=1), following


# --------------------------------------------------------------------------- #
# Draft lines & discount resolution
# --------------------------------------------------------------------------- #
@dataclass
class DraftLine:
    product_id: int | None
    description: str
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    subtotal: Decimal
    discount: Decimal = ZERO
    tax_amount: Decimal = ZERO
    total: Decimal = ZERO

    @property
    def net(self) -> Decimal:
        return self.subtotal - self.discount


@dataclass
class AppliedDiscount:
    discount: Discount
    amount: Decimal


@dataclass
class PricedInvoice:
    lines: list[DraftLine]
    discounts: list[AppliedDiscount] = field(default_factory=list)

    @property
    def subtotal(self) -> Decimal:
        return sum((line.subtotal for line in self.lines), ZERO)

    @property
    def discount_total(self) -> Decimal:
        return sum((line.discount for line in self.lines), ZERO)

    @property
    def tax_total(self) -> Decimal:
        return sum((line.tax_amount for line in self.lines), ZERO)

    @property
    def total(self) -> Decimal:
        return money(self.subtotal - self.discount_total + self.tax_total)


def _apply_discount(
    discount: Discount,
    lines: list[DraftLine],
    indices: list[int],
    on_date: date,
    total_quantity: int,
    gross_subtotal: Decimal,
) -> AppliedDiscount | None:
    """Apply one rule to the matching lines, respecting its guard rails."""
    if not discount.is_live_on(on_date):
        return None
    if gross_subtotal < discount.min_purchase_amount:
        return None
    if total_quantity < discount.min_quantity:
        return None

    base = sum((lines[i].subtotal for i in indices), ZERO)
    remaining = sum((lines[i].subtotal - lines[i].discount for i in indices), ZERO)
    base = min(base, remaining)
    if base <= ZERO:
        return None

    amount = min(discount.compute(base), base)
    if amount <= ZERO:
        return None

    weights = [lines[i].subtotal for i in indices]
    for index, share in zip(indices, allocate(amount, weights), strict=True):
        lines[index].discount += share

    return AppliedDiscount(discount=discount, amount=amount)


def price_lines(
    lines: list[DraftLine],
    subscription: Subscription,
    on_date: date,
) -> PricedInvoice:
    """Apply every live discount attached to the subscription, then taxes."""
    priced = PricedInvoice(lines=lines)
    gross_subtotal = priced.subtotal
    total_quantity = sum(line.quantity for line in lines)

    for link in subscription.discounts:
        if not link.is_active:
            continue
        discount = link.discount
        if discount.scope is DiscountScope.PRODUCT:
            indices = [
                i for i, line in enumerate(lines) if line.product_id == discount.product_id
            ]
        else:
            indices = list(range(len(lines)))
        if not indices:
            continue
        applied = _apply_discount(
            discount, lines, indices, on_date, total_quantity, gross_subtotal
        )
        if applied:
            priced.discounts.append(applied)

    for line in lines:
        line.tax_amount = percentage(line.net, line.tax_rate)
        line.total = money(line.net + line.tax_amount)

    return priced


# --------------------------------------------------------------------------- #
# Invoice creation
# --------------------------------------------------------------------------- #
def build_invoice(
    db: Session,
    subscription: Subscription,
    period_start: date,
    period_end: date,
    *,
    issue_date: date | None = None,
    due_date: date | None = None,
    auto_confirm: bool = True,
    notes: str | None = None,
) -> Invoice:
    """Create (and optionally confirm) the invoice for one billing period.

    Committed by the caller. Raises ValueError when the period is already billed.
    """
    existing = db.scalar(
        select(Invoice.id).where(
            Invoice.subscription_id == subscription.id,
            Invoice.period_start == period_start,
        )
    )
    if existing:
        raise ValueError(f"Subscription {subscription.number} is already billed for {period_start}")

    issue = issue_date or period_start
    due = due_date or issue + timedelta(days=subscription.payment_terms_days)

    draft_lines = [
        DraftLine(
            product_id=line.product_id,
            description=line.description or line.product.name,
            quantity=line.quantity,
            unit_price=line.unit_price,
            tax_rate=line.tax_rate,
            subtotal=money(line.unit_price * line.quantity),
        )
        for line in subscription.lines
    ]
    if not draft_lines:
        raise ValueError(f"Subscription {subscription.number} has no lines")

    priced = price_lines(draft_lines, subscription, issue)

    invoice = Invoice(
        number=numbering.next_document_number(db, "INV", Invoice),
        subscription_id=subscription.id,
        customer_id=subscription.customer_id,
        issue_date=issue,
        due_date=due,
        period_start=period_start,
        period_end=period_end,
        subtotal=priced.subtotal,
        discount_total=priced.discount_total,
        tax_total=priced.tax_total,
        total=priced.total,
        notes=notes,
        status=InvoiceStatus.DRAFT,
    )
    invoice.lines = [
        InvoiceLine(
            product_id=line.product_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            tax_rate=line.tax_rate,
            subtotal=line.subtotal,
            discount_amount=line.discount,
            tax_amount=line.tax_amount,
            total=line.total,
        )
        for line in priced.lines
    ]

    if auto_confirm:
        invoice.status = InvoiceStatus.CONFIRMED
        invoice.confirmed_at = utcnow()

    db.add(invoice)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as exc:  # the DB constraint is the real guard
        try:
            db.expunge(invoice)
        except Exception:  # pragma: no cover - object may already be detached
            pass
        raise ValueError(
            f"Subscription {subscription.number} is already billed for {period_start}"
        ) from exc

    # Record usage only for invoices that are actually issued.
    if auto_confirm:
        for applied in priced.discounts:
            applied.discount.used_count += 1
            db.add(
                DiscountRedemption(
                    discount_id=applied.discount.id,
                    subscription_id=subscription.id,
                    invoice_id=invoice.id,
                    amount=applied.amount,
                )
            )
        db.flush()

    return invoice


def advance_subscription(db: Session, subscription: Subscription) -> bool:
    """Move the billing cursor forward. Returns True when the term ended."""
    plan = subscription.plan
    if subscription.next_billing_date is None:
        return False

    _, _, following = next_period(plan, subscription.next_billing_date)
    subscription.current_period_start = subscription.next_billing_date
    subscription.current_period_end = following - timedelta(days=1)

    term_ended = bool(
        subscription.expiry_date and following > subscription.expiry_date
    )
    if term_ended:
        subscription.next_billing_date = None
        if subscription.auto_close_on_expiry:
            subscription.status = SubscriptionStatus.CLOSED
            subscription.closed_at = utcnow()
            subscription.closed_reason = "Term ended"
            return True
    else:
        subscription.next_billing_date = following
    return term_ended


def run_billing(
    db: Session,
    *,
    as_of: date,
    auto_confirm: bool = True,
    dry_run: bool = False,
    max_cycles: int = 60,
) -> dict:
    """Invoice every active subscription that is due on or before `as_of`."""
    subscriptions = list(
        db.scalars(
            select(Subscription)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.next_billing_date.is_not(None),
                Subscription.next_billing_date <= as_of,
            )
            .order_by(Subscription.next_billing_date)
        ).unique()
    )

    invoice_ids: list[int] = []
    invoice_numbers: list[str] = []
    errors: list[str] = []
    closed = 0
    skipped = 0

    for subscription in subscriptions:
        cycles = 0
        while (
            subscription.next_billing_date is not None
            and subscription.next_billing_date <= as_of
            and cycles < max_cycles
        ):
            cycles += 1
            if subscription.expiry_date and subscription.next_billing_date > subscription.expiry_date:
                subscription.next_billing_date = None
                if subscription.auto_close_on_expiry:
                    subscription.status = SubscriptionStatus.CLOSED
                    subscription.closed_at = utcnow()
                    subscription.closed_reason = "Term ended"
                    closed += 1
                break

            period_start, period_end, _ = next_period(
                subscription.plan, subscription.next_billing_date
            )
            if dry_run:
                invoice_numbers.append(f"(dry-run) {subscription.number} {period_start}")
                break
            try:
                invoice = build_invoice(
                    db,
                    subscription,
                    period_start,
                    period_end,
                    issue_date=period_start,
                    auto_confirm=auto_confirm,
                )
            except ValueError as exc:
                errors.append(str(exc))
                skipped += 1
                break
            invoice_ids.append(invoice.id)
            invoice_numbers.append(invoice.number)

            if advance_subscription(db, subscription):
                closed += 1
                break

    if not dry_run:
        db.flush()
    else:
        db.rollback()

    return {
        "as_of": as_of,
        "dry_run": dry_run,
        "scanned": len(subscriptions),
        "invoiced": len(invoice_ids),
        "skipped": skipped,
        "closed": closed,
        "invoice_ids": invoice_ids,
        "invoice_numbers": invoice_numbers,
        "errors": errors,
    }
