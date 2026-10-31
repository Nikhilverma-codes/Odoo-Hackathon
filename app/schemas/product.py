from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models.product import ProductType
from app.schemas.common import Money, Rate, Schema


class TaxIn(Schema):
    name: str = Field(min_length=1, max_length=80)
    rate: Rate = Field(default=Decimal("0"), ge=0, le=100)
    description: str | None = None
    is_active: bool = True


class TaxOut(Schema):
    id: int
    name: str
    rate: Rate
    description: str | None
    is_active: bool


class VariantIn(Schema):
    name: str = Field(min_length=1, max_length=120)
    price_delta: Money = Field(default=Decimal("0"))
    is_active: bool = True


class VariantOut(Schema):
    id: int
    name: str
    price_delta: Money
    is_active: bool


class ProductIn(Schema):
    name: str = Field(min_length=1, max_length=160)
    type: ProductType = ProductType.SERVICE
    sales_price: Money = Field(default=Decimal("0"), ge=0)
    cost_price: Money = Field(default=Decimal("0"), ge=0)
    notes: str | None = None
    tax_id: int | None = None
    is_active: bool = True


class ProductUpdateIn(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    type: ProductType | None = None
    sales_price: Money | None = Field(default=None, ge=0)
    cost_price: Money | None = Field(default=None, ge=0)
    notes: str | None = None
    tax_id: int | None = None
    is_active: bool | None = None


class ProductShort(Schema):
    id: int
    name: str
    type: ProductType
    sales_price: Money


class ProductOut(ProductShort):
    cost_price: Money
    notes: str | None
    tax: TaxOut | None
    is_active: bool
    variants: list[VariantOut]
    created_at: datetime
