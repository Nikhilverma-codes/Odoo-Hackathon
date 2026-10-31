from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.api.deps import (
    CurrentUser,
    DbSession,
    PaginationDep,
    StaffUser,
    ensure_customer_access,
)
from app.api.pagination import paginate
from app.db.base import utcnow
from app.models import (
    Customer,
    Invoice,
    InvoiceStatus,
    Plan,
    Role,
    Subscription,
    SubscriptionStatus,
)
from app.schemas.common import MessageOut, Page
from app.schemas.discount import ApplyDiscountIn
from app.schemas.invoice import InvoiceOut
from app.schemas.subscription import (
    CloseIn,
    RenewIn,
    StatusChangeIn,
    SubscriptionCreateIn,
    SubscriptionDetailOut,
    SubscriptionOut,
    SubscriptionUpdateIn,
)
from app.services import billing, subscriptions as subscription_service

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _get_visible(db: DbSession, subscription_id: int, user: CurrentUser) -> Subscription:
    subscription = subscription_service.get_subscription(db, subscription_id)
    ensure_customer_access(user, subscription.customer_id)
    return subscription


@router.get("", response_model=Page[SubscriptionOut])
def list_subscriptions(
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    status: SubscriptionStatus | None = None,
    customer_id: int | None = None,
    plan_id: int | None = None,
    q: str | None = None,
    expiring_before: date | None = None,
):
    stmt = select(Subscription)
    if user.role is Role.CUSTOMER:
        stmt = stmt.where(Subscription.customer_id == user.customer_id)
    elif customer_id is not None:
        stmt = stmt.where(Subscription.customer_id == customer_id)

    if status is not None:
        stmt = stmt.where(Subscription.status == status)
    if plan_id is not None:
        stmt = stmt.where(Subscription.plan_id == plan_id)
    if expiring_before is not None:
        stmt = stmt.where(
            Subscription.expiry_date.is_not(None),
            Subscription.expiry_date <= expiring_before,
        )
    if q:
        needle = f"%{q.lower()}%"
        stmt = stmt.join(Customer, Customer.id == Subscription.customer_id).where(
            or_(Subscription.number.ilike(needle), Customer.name.ilike(needle))
        )

    stmt = stmt.order_by(Subscription.created_at.desc(), Subscription.id.desc())
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.post("", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreateIn, staff: StaffUser, db: DbSession):
    if not db.get(Plan, payload.plan_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Plan not found")
    subscription = subscription_service.create_subscription(db, payload, staff)
    db.commit()
    return subscription


@router.get("/{subscription_id}", response_model=SubscriptionDetailOut)
def get_subscription(subscription_id: int, user: CurrentUser, db: DbSession):
    return _get_visible(db, subscription_id, user)


@router.patch("/{subscription_id}", response_model=SubscriptionOut)
def update_subscription(
    subscription_id: int, payload: SubscriptionUpdateIn, staff: StaffUser, db: DbSession
):
    subscription = subscription_service.get_subscription(db, subscription_id)
    subscription = subscription_service.update_subscription(db, subscription, payload, staff)
    db.commit()
    return subscription


@router.post("/{subscription_id}/status", response_model=SubscriptionOut)
def change_status(
    subscription_id: int, payload: StatusChangeIn, staff: StaffUser, db: DbSession
):
    subscription = subscription_service.get_subscription(db, subscription_id)
    subscription = subscription_service.transition(
        db, subscription, payload.status, staff, payload.note
    )
    db.commit()
    return subscription


@router.post("/{subscription_id}/confirm", response_model=SubscriptionOut)
def confirm_subscription(
    subscription_id: int, staff: StaffUser, db: DbSession, note: str | None = None
):
    subscription = subscription_service.get_subscription(db, subscription_id)
    subscription = subscription_service.transition(
        db, subscription, SubscriptionStatus.CONFIRMED, staff, note
    )
    db.commit()
    return subscription


@router.post("/{subscription_id}/activate", response_model=SubscriptionOut)
def activate_subscription(
    subscription_id: int, staff: StaffUser, db: DbSession, note: str | None = None
):
    subscription = subscription_service.get_subscription(db, subscription_id)
    subscription = subscription_service.transition(
        db, subscription, SubscriptionStatus.ACTIVE, staff, note
    )
    db.commit()
    return subscription


@router.post("/{subscription_id}/pause", response_model=SubscriptionOut)
def pause_subscription(
    subscription_id: int, user: CurrentUser, db: DbSession, note: str | None = None
):
    subscription = _get_visible(db, subscription_id, user)
    if user.role is Role.CUSTOMER and not subscription.allow_pause:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This plan cannot be paused")
    subscription = subscription_service.transition(
        db, subscription, SubscriptionStatus.PAUSED, user, note
    )
    db.commit()
    return subscription


@router.post("/{subscription_id}/resume", response_model=SubscriptionOut)
def resume_subscription(
    subscription_id: int, user: CurrentUser, db: DbSession, note: str | None = None
):
    subscription = _get_visible(db, subscription_id, user)
    subscription = subscription_service.transition(
        db, subscription, SubscriptionStatus.ACTIVE, user, note or "Resumed"
    )
    db.commit()
    return subscription


@router.post("/{subscription_id}/close", response_model=SubscriptionOut)
def close_subscription(
    subscription_id: int, payload: CloseIn, staff: StaffUser, db: DbSession
):
    subscription = subscription_service.get_subscription(db, subscription_id)
    subscription = subscription_service.close_subscription(db, subscription, staff, payload.reason)
    db.commit()
    return subscription


@router.post("/{subscription_id}/renew", response_model=SubscriptionOut, status_code=201)
def renew_subscription(
    subscription_id: int, payload: RenewIn, staff: StaffUser, db: DbSession
):
    subscription = subscription_service.get_subscription(db, subscription_id)
    renewal = subscription_service.renew_subscription(
        db,
        subscription,
        staff,
        start_date=payload.start_date,
        expiry_date=payload.expiry_date,
        notes=payload.notes,
    )
    db.commit()
    return renewal


@router.post("/{subscription_id}/discounts", response_model=SubscriptionOut)
def apply_discount(
    subscription_id: int, payload: ApplyDiscountIn, staff: StaffUser, db: DbSession
):
    subscription = subscription_service.get_subscription(db, subscription_id)
    subscription_service._attach_discount(db, subscription, payload.discount_id)
    db.commit()
    return subscription


@router.delete("/{subscription_id}/discounts/{discount_id}", response_model=MessageOut)
def remove_discount(
    subscription_id: int, discount_id: int, staff: StaffUser, db: DbSession
):
    subscription = subscription_service.get_subscription(db, subscription_id)
    link = next(
        (
            item
            for item in subscription.discounts
            if item.discount_id == discount_id and item.removed_at is None
        ),
        None,
    )
    if not link:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discount is not applied to this subscription")
    link.removed_at = utcnow()
    link.removed_reason = "Removed by user"
    db.commit()
    return MessageOut(message="Discount removed")


@router.get("/{subscription_id}/invoices", response_model=Page[InvoiceOut])
def list_subscription_invoices(
    subscription_id: int,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    status: InvoiceStatus | None = None,
):
    _get_visible(db, subscription_id, user)
    stmt = select(Invoice).where(Invoice.subscription_id == subscription_id)
    if status is not None:
        stmt = stmt.where(Invoice.status == status)
    stmt = stmt.order_by(Invoice.issue_date.desc(), Invoice.id.desc())
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.post(
    "/{subscription_id}/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED
)
def generate_invoice(
    subscription_id: int,
    staff: StaffUser,
    db: DbSession,
    auto_confirm: bool = Query(True, description="Confirm the invoice immediately"),
):
    """Bill the next period for one subscription (billing day, done by hand)."""
    subscription = subscription_service.get_subscription(db, subscription_id)
    if subscription.status is not SubscriptionStatus.ACTIVE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only active subscriptions can be billed")

    period_start = subscription.next_billing_date or date.today()
    start, end, _ = billing.next_period(subscription.plan, period_start)
    try:
        invoice = billing.build_invoice(
            db,
            subscription,
            start,
            end,
            issue_date=start,
            auto_confirm=auto_confirm,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    if subscription.next_billing_date == start:
        billing.advance_subscription(db, subscription)
    db.commit()
    return invoice
