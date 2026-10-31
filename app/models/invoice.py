"""Invoices, invoice lines and payments."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Money, Rate, TimestampMixin, enum_column
from app.models.product import Product
from app.models.subscription import Subscription
from app.models.user import Customer, User


class InvoiceStatus(str, PyEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentMethod(str, PyEnum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    PAYPAL = "paypal"
    DIRECT_DEBIT = "direct_debit"
    OTHER = "other"


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        # Guarantees the billing run can never bill the same period twice.
        UniqueConstraint(
            "subscription_id", "period_start", name="uq_invoice_subscription_period"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        enum_column(InvoiceStatus),
        default=InvoiceStatus.DRAFT,
        nullable=False,
        index=True,
    )

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(
        Money, default=Decimal("0"), nullable=False
    )
    tax_total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(
        Money, default=Decimal("0"), nullable=False
    )

    notes: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_reason: Mapped[str | None] = mapped_column(String(255))

    subscription: Mapped[Subscription | None] = relationship(lazy="joined")
    customer: Mapped[Customer] = relationship(back_populates="invoices", lazy="joined")
    lines: Mapped[list[InvoiceLine]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InvoiceLine.id",
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Payment.id",
    )

    @property
    def amount_due(self) -> Decimal:
        return max(self.total - self.amount_paid, Decimal("0.00"))

    @property
    def is_overdue(self) -> bool:
        return (
            self.status is InvoiceStatus.CONFIRMED
            and self.amount_due > 0
            and self.due_date < date.today()
        )

    @property
    def is_editable(self) -> bool:
        return self.status in (InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED)


class InvoiceLine(Base, TimestampMixin):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(Rate, nullable=False, default=Decimal("0"))
    subtotal: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(
        Money, nullable=False, default=Decimal("0")
    )
    tax_amount: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))

    invoice: Mapped[Invoice] = relationship(back_populates="lines")
    product: Mapped[Product | None] = relationship(lazy="joined")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[PaymentMethod] = mapped_column(
        enum_column(PaymentMethod), default=PaymentMethod.BANK_TRANSFER, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    paid_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reference: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)
    recorded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
    recorded_by: Mapped[User | None] = relationship()
