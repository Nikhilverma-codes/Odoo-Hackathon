"""Plans: what a subscription costs and how often it bills."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Money, TimestampMixin, enum_column
from app.models.product import Product, Tax


class BillingInterval(str, PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    interval: Mapped[BillingInterval] = mapped_column(
        enum_column(BillingInterval), default=BillingInterval.MONTHLY, nullable=False
    )
    min_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    available_from: Mapped[date | None] = mapped_column(Date)
    available_to: Mapped[date | None] = mapped_column(Date)

    # Per-plan lifecycle switches decided by the admin.
    auto_close_on_expiry: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_early_close: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_pause: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tax_id: Mapped[int | None] = mapped_column(ForeignKey("taxes.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped[Product] = relationship(lazy="joined")
    tax: Mapped[Tax | None] = relationship(lazy="joined")

    def is_available_on(self, day: date) -> bool:
        if not self.is_active:
            return False
        if self.available_from and day < self.available_from:
            return False
        if self.available_to and day > self.available_to:
            return False
        return True
