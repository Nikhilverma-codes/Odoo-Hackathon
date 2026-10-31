"""Quotation templates a sales rep can start an offer from."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Money, TimestampMixin
from app.models.plan import Plan
from app.models.product import Product, ProductVariant


class QuotationTemplate(Base, TimestampMixin):
    __tablename__ = "quotation_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    validity_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    plan: Mapped[Plan] = relationship(lazy="joined")
    lines: Mapped[list[QuotationTemplateLine]] = relationship(
        back_populates="template", cascade="all, delete-orphan", lazy="selectin"
    )


class QuotationTemplateLine(Base, TimestampMixin):
    __tablename__ = "quotation_template_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("quotation_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Money)

    template: Mapped[QuotationTemplate] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship(lazy="joined")
    variant: Mapped[ProductVariant | None] = relationship(lazy="joined")
