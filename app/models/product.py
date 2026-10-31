"""Catalogue: products, variants and tax rates."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Money, Rate, TimestampMixin, enum_column


class ProductType(str, PyEnum):
    SERVICE = "service"
    ADDON = "addon"
    MODULE = "module"
    SUPPORT = "support"


class Tax(Base, TimestampMixin):
    """Tax rule applied automatically to invoice lines.

    `rate` is a percentage (15 == 15%).
    """

    __tablename__ = "taxes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    rate: Mapped[Decimal] = mapped_column(Rate, nullable=False, default=Decimal("0"))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list[Product]] = relationship(back_populates="tax")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    type: Mapped[ProductType] = mapped_column(
        enum_column(ProductType), default=ProductType.SERVICE, nullable=False
    )
    sales_price: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    cost_price: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text)
    tax_id: Mapped[int | None] = mapped_column(ForeignKey("taxes.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tax: Mapped[Tax | None] = relationship(back_populates="products")
    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )


class ProductVariant(Base, TimestampMixin):
    """e.g. brand "Odoo" which adds 560 to the price."""

    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("product_id", "name", name="uq_variant_product_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price_delta: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped[Product] = relationship(back_populates="variants")
