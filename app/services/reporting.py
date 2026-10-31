"""Finance-facing aggregates: MRR, revenue, outstanding and overdue."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException, status as http_status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.money import ZERO, money, to_decimal
from app.db.base import utcnow
from app.models import (
    BillingInterval,
    Invoice,
    InvoiceStatus,
    Payment,
    Plan,
    Subscription,
    SubscriptionLine,
    SubscriptionStatus,
)

#: How many of each interval fit in a month, used to normalize MRR.
_INTERVAL_FACTOR: dict[BillingInterval, Decimal] = {
    BillingInterval.DAILY: Decimal("365") / Decimal("12"),
    BillingInterval.WEEKLY: Decimal("52") / Decimal("12"),
    BillingInterval.MONTHLY: Decimal("1"),
    BillingInterval.YEARLY: Decimal("1") / Decimal("12"),
}


def _month_bounds(as_of: date) -> tuple[date, date]:
    start = as_of.replace(day=1)
    next_month = (start + timedelta(days=32)).replace(day=1)
    return start, next_month - timedelta(days=1)


def _mrr(db: Session, as_of: date) -> Decimal:
    rows = db.execute(
        select(Plan.interval, func.coalesce(func.sum(SubscriptionLine.amount), 0))
        .select_from(SubscriptionLine)
        .join(Subscription, Subscription.id == SubscriptionLine.subscription_id)
        .join(Plan, Plan.id == Subscription.plan_id)
        .where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.start_date <= as_of,
        )
        .group_by(Plan.interval)
    ).all()

    total = ZERO
    for interval, amount in rows:
        total += to_decimal(amount) * _INTERVAL_FACTOR[BillingInterval(interval)]
    return money(total)


def summary(db: Session, as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    period_start, period_end = _month_bounds(as_of)

    def count(status_: SubscriptionStatus) -> int:
        return int(
            db.scalar(
                select(func.count(Subscription.id)).where(Subscription.status == status_)
            )
            or 0
        )

    invoiced = to_decimal(
        db.scalar(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(
                Invoice.status.in_([InvoiceStatus.CONFIRMED, InvoiceStatus.PAID]),
                Invoice.issue_date >= period_start,
                Invoice.issue_date <= period_end,
            )
        )
    )
    collected = to_decimal(
        db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .where(
                Invoice.status != InvoiceStatus.CANCELLED,
                Payment.paid_on >= period_start,
                Payment.paid_on <= period_end,
            )
        )
    )

    outstanding_stmt = select(
        func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0)
    ).where(Invoice.status == InvoiceStatus.CONFIRMED, Invoice.total > Invoice.amount_paid)
    outstanding = to_decimal(db.scalar(outstanding_stmt))

    overdue_stmt = select(
        func.count(Invoice.id),
        func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0),
    ).where(
        Invoice.status == InvoiceStatus.CONFIRMED,
        Invoice.due_date < as_of,
        Invoice.total > Invoice.amount_paid,
    )
    overdue_count, overdue_amount = db.execute(overdue_stmt).one()

    breakdown = db.execute(
        select(
            Invoice.status,
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.total), 0),
        )
        .where(Invoice.status != InvoiceStatus.CANCELLED)
        .group_by(Invoice.status)
    ).all()

    renewals = list(
        db.scalars(
            select(Subscription)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.next_billing_date.is_not(None),
                Subscription.next_billing_date >= as_of,
                Subscription.next_billing_date <= as_of + timedelta(days=30),
            )
            .order_by(Subscription.next_billing_date)
            .limit(10)
        ).unique()
    )

    mrr = _mrr(db, as_of)

    return {
        "generated_at": utcnow(),
        "as_of": as_of,
        "period_start": period_start,
        "period_end": period_end,
        "active_subscriptions": count(SubscriptionStatus.ACTIVE),
        "paused_subscriptions": count(SubscriptionStatus.PAUSED),
        "mrr": mrr,
        "arr": money(mrr * 12),
        "revenue_invoiced": money(invoiced),
        "revenue_collected": money(collected),
        "outstanding_amount": money(outstanding),
        "overdue_invoices": int(overdue_count or 0),
        "overdue_amount": money(overdue_amount),
        "invoices_by_status": [
            {"status": row[0], "count": int(row[1]), "total": money(row[2])}
            for row in breakdown
        ],
        "upcoming_renewals": [
            {
                "subscription_id": sub.id,
                "number": sub.number,
                "customer_name": sub.customer.name,
                "next_billing_date": sub.next_billing_date,
                "amount": money(sub.line_subtotal),
            }
            for sub in renewals
            if sub.next_billing_date
        ],
    }


def revenue_report(
    db: Session,
    date_from: date,
    date_to: date,
    group_by: str = "month",
) -> dict:
    if group_by not in {"day", "month"}:
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "group_by must be 'day' or 'month'")
    if date_to < date_from:
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "date_to must be on or after date_from")

    fmt = "%Y-%m-%d" if group_by == "day" else "%Y-%m"

    invoiced_rows = db.execute(
        select(func.strftime(fmt, Invoice.issue_date), func.sum(Invoice.total))
        .where(
            Invoice.status.in_([InvoiceStatus.CONFIRMED, InvoiceStatus.PAID]),
            Invoice.issue_date >= date_from,
            Invoice.issue_date <= date_to,
        )
        .group_by(func.strftime(fmt, Invoice.issue_date))
    ).all()

    collected_rows = db.execute(
        select(func.strftime(fmt, Payment.paid_on), func.sum(Payment.amount))
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .where(
            Invoice.status != InvoiceStatus.CANCELLED,
            Payment.paid_on >= date_from,
            Payment.paid_on <= date_to,
        )
        .group_by(func.strftime(fmt, Payment.paid_on))
    ).all()

    buckets: dict[str, dict[str, Decimal]] = {}
    for period, amount in invoiced_rows:
        buckets.setdefault(period, {"invoiced": ZERO, "collected": ZERO})["invoiced"] = to_decimal(amount)
    for period, amount in collected_rows:
        buckets.setdefault(period, {"invoiced": ZERO, "collected": ZERO})["collected"] = to_decimal(amount)

    points = [
        {
            "period": period,
            "invoiced": money(values["invoiced"]),
            "collected": money(values["collected"]),
        }
        for period, values in sorted(buckets.items())
    ]
    return {
        "date_from": date_from,
        "date_to": date_to,
        "group_by": group_by,
        "total_invoiced": money(sum((p["invoiced"] for p in points), ZERO)),
        "total_collected": money(sum((p["collected"] for p in points), ZERO)),
        "points": points,
    }


def overdue_invoices(db: Session, as_of: date | None = None, limit: int = 100) -> list[dict]:
    as_of = as_of or date.today()
    invoices = list(
        db.scalars(
            select(Invoice)
            .where(
                Invoice.status == InvoiceStatus.CONFIRMED,
                Invoice.due_date < as_of,
                Invoice.total > Invoice.amount_paid,
            )
            .order_by(Invoice.due_date)
            .limit(limit)
        ).unique()
    )
    return [
        {"invoice": invoice, "days_overdue": (as_of - invoice.due_date).days}
        for invoice in invoices
    ]
