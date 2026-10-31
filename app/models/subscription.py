"""Subscriptions, their lines and their lifecycle history."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Money, Rate, TimestampMixin, enum_column, utcnow
from app.models.discount import SubscriptionDiscount
from app.models.plan import Plan
from app.models.product import Product, ProductVariant, Tax
from app.models.quotation import QuotationTemplate
from app.models.user import Customer, User


class SubscriptionStatus(str, PyEnum):
    DRAFT = "draft"
    QUOTATION = "quotation"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


#: Allowed status moves. Enforced in `app.services.subscriptions`.
STATUS_TRANSITIONS: dict[SubscriptionStatus, set[SubscriptionStatus]] = {
    SubscriptionStatus.DRAFT: {
        SubscriptionStatus.QUOTATION,
        SubscriptionStatus.CONFIRMED,
        SubscriptionStatus.CLOSED,
    },
    SubscriptionStatus.QUOTATION: {
        SubscriptionStatus.CONFIRMED,
        SubscriptionStatus.DRAFT,
        SubscriptionStatus.CLOSED,
    },
    SubscriptionStatus.CONFIRMED: {SubscriptionStatus.ACTIVE, SubscriptionStatus.CLOSED},
    SubscriptionStatus.ACTIVE: {
        SubscriptionStatus.PAUSED,
        SubscriptionStatus.CLOSED,
    },
    SubscriptionStatus.PAUSED: {SubscriptionStatus.ACTIVE, SubscriptionStatus.CLOSED},
    SubscriptionStatus.CLOSED: set(),
}


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quotation_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_templates.id", ondelete="SET NULL")
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        enum_column(SubscriptionStatus),
        default=SubscriptionStatus.DRAFT,
        nullable=False,
        index=True,
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Billing cursor - advanced by the billing run.
    current_period_start: Mapped[date | None] = mapped_column(Date)
    current_period_end: Mapped[date | None] = mapped_column(Date)
    next_billing_date: Mapped[date | None] = mapped_column(Date, index=True)

    # Snapshot of the plan switches at subscription time.
    auto_close_on_expiry: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_early_close: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_pause: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    paused_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_reason: Mapped[str | None] = mapped_column(String(255))
    renewed_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    customer: Mapped[Customer] = relationship(back_populates="subscriptions", lazy="joined")
    plan: Mapped[Plan] = relationship(lazy="joined")
    quotation_template: Mapped[QuotationTemplate | None] = relationship(lazy="joined")
    lines: Mapped[list[SubscriptionLine]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SubscriptionLine.id",
    )
    status_history: Mapped[list[SubscriptionStatusHistory]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="SubscriptionStatusHistory.id",
    )
    discounts: Mapped[list["SubscriptionDiscount"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    @property
    def is_billable(self) -> bool:
        return self.status is SubscriptionStatus.ACTIVE

    @property
    def line_subtotal(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal("0.00"))


class SubscriptionLine(Base, TimestampMixin):
    __tablename__ = "subscription_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    description: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    tax_id: Mapped[int | None] = mapped_column(ForeignKey("taxes.id", ondelete="SET NULL"))
    tax_rate: Mapped[Decimal] = mapped_column(Rate, nullable=False, default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))

    subscription: Mapped[Subscription] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship(lazy="joined")
    variant: Mapped[ProductVariant | None] = relationship(lazy="joined")
    tax: Mapped[Tax | None] = relationship(lazy="joined")


class SubscriptionStatusHistory(Base):
    __tablename__ = "subscription_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[SubscriptionStatus | None] = mapped_column(
        enum_column(SubscriptionStatus)
    )
    to_status: Mapped[SubscriptionStatus] = mapped_column(
        enum_column(SubscriptionStatus), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255))
    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    subscription: Mapped[Subscription] = relationship(back_populates="status_history")
    changed_by: Mapped[User | None] = relationship()
