"""Subscription creation, editing and lifecycle transitions."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.money import money
from app.db.base import utcnow
from app.models import (
    Customer,
    Discount,
    Plan,
    QuotationTemplate,
    Subscription,
    SubscriptionDiscount,
    SubscriptionLine,
    SubscriptionStatus,
    SubscriptionStatusHistory,
    Tax,
    User,
)
from app.models.subscription import STATUS_TRANSITIONS
from app.schemas.subscription import (
    SubscriptionCreateIn,
    SubscriptionLineIn,
    SubscriptionUpdateIn,
)
from app.services import numbering
from app.services.billing import next_period


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def get_subscription(db: Session, subscription_id: int) -> Subscription:
    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")
    return subscription


def _record_history(
    db: Session,
    subscription: Subscription,
    to_status: SubscriptionStatus,
    actor: User | None,
    note: str | None = None,
    from_status: SubscriptionStatus | None = None,
) -> None:
    db.add(
        SubscriptionStatusHistory(
            subscription_id=subscription.id,
            from_status=from_status if from_status is not None else subscription.status,
            to_status=to_status,
            note=note,
            changed_by_id=actor.id if actor else None,
        )
    )


def _build_line(db: Session, payload: SubscriptionLineIn) -> SubscriptionLine:
    from app.models import Product, ProductVariant

    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Product {payload.product_id} not found"
        )
    if not product.is_active:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Product {product.name} is not available"
        )

    variant = None
    unit_price = payload.unit_price
    if payload.variant_id is not None:
        variant = db.get(ProductVariant, payload.variant_id)
        if not variant or variant.product_id != product.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Variant {payload.variant_id} does not belong to product {product.id}",
            )
        if unit_price is None:
            unit_price = Decimal(product.sales_price) + Decimal(variant.price_delta)

    if unit_price is None:
        unit_price = Decimal(product.sales_price)

    tax = db.get(Tax, payload.tax_id) if payload.tax_id is not None else product.tax
    tax_rate = Decimal(tax.rate) if tax else Decimal("0")

    return SubscriptionLine(
        product_id=product.id,
        variant_id=variant.id if variant else None,
        description=payload.description or product.name,
        quantity=payload.quantity,
        unit_price=money(unit_price),
        tax_id=tax.id if tax else None,
        tax_rate=tax_rate,
        amount=money(unit_price * payload.quantity),
    )


def _validate_minimum(plan: Plan, lines: list[SubscriptionLine]) -> None:
    plan_lines = [line for line in lines if line.product_id == plan.product_id]
    if plan_lines:
        quantity = sum(line.quantity for line in plan_lines)
    else:
        quantity = sum(line.quantity for line in lines)
    if quantity < plan.min_quantity:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Plan {plan.code} requires a minimum quantity of {plan.min_quantity}",
        )


def _set_lines(db: Session, subscription: Subscription, payloads: list[SubscriptionLineIn]) -> None:
    subscription.lines.clear()
    for payload in payloads:
        subscription.lines.append(_build_line(db, payload))
    if subscription.lines:
        _validate_minimum(subscription.plan, subscription.lines)


def _attach_discount(
    db: Session, subscription: Subscription, discount_id: int
) -> SubscriptionDiscount:
    discount = db.get(Discount, discount_id)
    if not discount:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Discount {discount_id} not found")
    if not discount.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Discount is inactive")

    existing = next(
        (
            link
            for link in subscription.discounts
            if link.discount_id == discount_id and link.removed_at is None
        ),
        None,
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Discount already applied")
    if discount.max_uses is not None and discount.used_count >= discount.max_uses:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Discount usage limit reached")

    link = SubscriptionDiscount(discount=discount, applied_at=utcnow())
    subscription.discounts.append(link)
    return link


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def create_subscription(
    db: Session, payload: SubscriptionCreateIn, actor: User | None
) -> Subscription:
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    if not customer.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer is inactive")

    plan = db.get(Plan, payload.plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")

    start_date = payload.start_date or date.today()
    if not plan.is_available_on(start_date):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Plan {plan.code} is not available on {start_date.isoformat()}",
        )

    template = None
    if payload.quotation_template_id is not None:
        template = db.get(QuotationTemplate, payload.quotation_template_id)
        if not template:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Quotation template not found")

    subscription = Subscription(
        number=numbering.next_document_number(db, "SUB"),
        customer_id=customer.id,
        plan_id=plan.id,
        quotation_template_id=template.id if template else None,
        status=payload.status,
        start_date=start_date,
        expiry_date=payload.expiry_date,
        payment_terms_days=payload.payment_terms_days,
        auto_close_on_expiry=plan.auto_close_on_expiry,
        allow_early_close=plan.allow_early_close,
        allow_pause=plan.allow_pause,
        allow_renew=plan.allow_renew,
        notes=payload.notes,
        created_by_id=actor.id if actor else None,
    )

    if template:
        subscription.payment_terms_days = template.payment_terms_days
        if subscription.expiry_date is None:
            subscription.expiry_date = start_date + timedelta(days=template.validity_days)

    db.add(subscription)
    db.flush()  # assign subscription.id before building children

    line_payloads = list(payload.lines)
    if not line_payloads and template:
        line_payloads = [
            SubscriptionLineIn(
                product_id=line.product_id,
                variant_id=line.variant_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
            )
            for line in template.lines
        ]
    if not line_payloads:
        line_payloads = [
            SubscriptionLineIn(
                product_id=plan.product_id,
                quantity=plan.min_quantity,
                unit_price=plan.price,
            )
        ]
    _set_lines(db, subscription, line_payloads)

    for discount_id in payload.discount_ids:
        _attach_discount(db, subscription, discount_id)

    _record_history(
        db, subscription, subscription.status, actor, note="Subscription created", from_status=None
    )
    db.flush()
    return subscription


def update_subscription(
    db: Session, subscription: Subscription, payload: SubscriptionUpdateIn, actor: User | None
) -> Subscription:
    if subscription.status is SubscriptionStatus.CLOSED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A closed subscription cannot be edited")

    data = payload.model_dump(exclude_unset=True)
    if "expiry_date" in data:
        subscription.expiry_date = data["expiry_date"]
    if "payment_terms_days" in data:
        subscription.payment_terms_days = data["payment_terms_days"]
    if "notes" in data:
        subscription.notes = data["notes"]

    if payload.lines is not None:
        if not payload.lines:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "A subscription needs at least one line")
        _set_lines(db, subscription, payload.lines)

    if payload.discount_ids is not None:
        wanted = set(payload.discount_ids)
        for link in list(subscription.discounts):
            if link.removed_at is None and link.discount_id not in wanted:
                link.removed_at = utcnow()
                link.removed_reason = "Removed by user"
        for discount_id in wanted:
            _attach_discount(db, subscription, discount_id)

    db.flush()
    return subscription


def transition(
    db: Session,
    subscription: Subscription,
    new_status: SubscriptionStatus,
    actor: User | None,
    note: str | None = None,
) -> Subscription:
    if new_status is subscription.status:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Subscription is already in that status")

    allowed = STATUS_TRANSITIONS[subscription.status]
    if new_status not in allowed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot move from {subscription.status.value} to {new_status.value}",
        )

    if new_status is SubscriptionStatus.PAUSED and not subscription.allow_pause:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This plan cannot be paused")
    if new_status is SubscriptionStatus.CLOSED and not subscription.allow_early_close:
        if subscription.expiry_date and date.today() < subscription.expiry_date:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "This plan cannot be closed before its end date"
            )

    previous = subscription.status
    subscription.status = new_status

    if new_status is SubscriptionStatus.ACTIVE:
        subscription.paused_at = None
        if subscription.next_billing_date is None:
            _, period_end, _ = next_period(subscription.plan, subscription.start_date)
            subscription.current_period_start = subscription.start_date
            subscription.current_period_end = period_end
            # The first period has not been invoiced yet, so the cursor stays
            # on the start date until the billing run picks it up.
            subscription.next_billing_date = subscription.start_date
    elif new_status is SubscriptionStatus.PAUSED:
        subscription.paused_at = utcnow()
    elif new_status is SubscriptionStatus.CLOSED:
        subscription.closed_at = utcnow()
        subscription.closed_reason = note or "Closed"
        subscription.next_billing_date = None

    _record_history(db, subscription, new_status, actor, note=note, from_status=previous)
    db.flush()
    return subscription


def close_subscription(
    db: Session, subscription: Subscription, actor: User | None, reason: str | None = None
) -> Subscription:
    if subscription.status is SubscriptionStatus.CLOSED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Subscription is already closed")
    return transition(db, subscription, SubscriptionStatus.CLOSED, actor, note=reason or "Closed")


def renew_subscription(
    db: Session,
    subscription: Subscription,
    actor: User | None,
    *,
    start_date: date | None = None,
    expiry_date: date | None = None,
    notes: str | None = None,
) -> Subscription:
    if not subscription.allow_renew:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This plan cannot be renewed")
    if subscription.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.CLOSED):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Only active or closed subscriptions can be renewed"
        )

    new_start = start_date or (
        subscription.expiry_date + timedelta(days=1)
        if subscription.expiry_date
        else date.today()
    )

    renewal = Subscription(
        number=numbering.next_document_number(db, "SUB"),
        customer_id=subscription.customer_id,
        plan_id=subscription.plan_id,
        quotation_template_id=subscription.quotation_template_id,
        status=SubscriptionStatus.CONFIRMED,
        start_date=new_start,
        expiry_date=expiry_date,
        payment_terms_days=subscription.payment_terms_days,
        auto_close_on_expiry=subscription.auto_close_on_expiry,
        allow_early_close=subscription.allow_early_close,
        allow_pause=subscription.allow_pause,
        allow_renew=subscription.allow_renew,
        renewed_from_id=subscription.id,
        notes=notes or f"Renewal of {subscription.number}",
        created_by_id=actor.id if actor else None,
    )
    renewal.lines = [
        SubscriptionLine(
            product_id=line.product_id,
            variant_id=line.variant_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            tax_id=line.tax_id,
            tax_rate=line.tax_rate,
            amount=line.amount,
        )
        for line in subscription.lines
    ]
    for link in subscription.discounts:
        if link.removed_at is None:
            renewal.discounts.append(
                SubscriptionDiscount(discount_id=link.discount_id, applied_at=utcnow())
            )

    db.add(renewal)
    db.flush()
    _record_history(
        db, renewal, SubscriptionStatus.CONFIRMED, actor, note="Renewal created", from_status=None
    )
    transition(db, renewal, SubscriptionStatus.ACTIVE, actor, note="Renewal activated")
    db.flush()
    return renewal
