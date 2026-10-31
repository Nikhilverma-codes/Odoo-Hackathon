"""Discount rules and their application to subscriptions / invoices."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Money, TimestampMixin, enum_column, utcnow
from app.models.product import Product
from app.core.money import to_decimal

if TYPE_CHECKING:  # pragma: no cover
    from app.models.invoice import Invoice
    from app.models.subscription import Subscription


class DiscountType(str, PyEnum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"


class DiscountScope(str, PyEnum):
    SUBSCRIPTION = "subscription"
    PRODUCT = "product"


class Discount(Base, TimestampMixin):
    """Only admins create these. `used_count` guards the global usage limit."""

    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    type: Mapped[DiscountType] = mapped_column(enum_column(DiscountType), nullable=False)
    value: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    scope: Mapped[DiscountScope] = mapped_column(
        enum_column(DiscountScope), default=DiscountScope.SUBSCRIPTION, nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )

    min_purchase_amount: Mapped[Decimal] = mapped_column(
        Money, default=Decimal("0"), nullable=False
    )
    min_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    start_date: Mapped[date | None] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, index=True)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    product: Mapped[Product | None] = relationship(lazy="joined")
    redemptions: Mapped[list[DiscountRedemption]] = relationship(
        back_populates="discount", cascade="all, delete-orphan"
    )

    def is_live_on(self, day: date) -> bool:
        if not self.is_active:
            return False
        if self.start_date and day < self.start_date:
            return False
        if self.end_date and day > self.end_date:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True

    def compute(self, base_amount: Decimal) -> Decimal:
        base = max(to_decimal(base_amount), Decimal("0.00"))
        value = to_decimal(self.value)
        if self.type is DiscountType.PERCENTAGE:
            amount = base * value / Decimal("100")
        else:
            amount = value
        return min(amount, base).quantize(Decimal("0.01"))


class SubscriptionDiscount(Base):
    """Links a rule to a subscription so it applies to every future invoice."""

    __tablename__ = "subscription_discounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    discount_id: Mapped[int] = mapped_column(
        ForeignKey("discounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime)
    removed_reason: Mapped[str | None] = mapped_column(String(255))

    subscription: Mapped[Subscription] = relationship(back_populates="discounts")
    discount: Mapped[Discount] = relationship(lazy="joined")

    @property
    def is_active(self) -> bool:
        return self.removed_at is None


class DiscountRedemption(Base):
    """One row per discount actually used on an invoice."""

    __tablename__ = "discount_redemptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    discount_id: Mapped[int] = mapped_column(
        ForeignKey("discounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), index=True
    )
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    discount: Mapped[Discount] = relationship(back_populates="redemptions")
    invoice: Mapped[Invoice | None] = relationship()
