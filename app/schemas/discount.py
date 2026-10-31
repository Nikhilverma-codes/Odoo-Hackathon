from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.models.discount import DiscountScope, DiscountType
from app.schemas.common import Money, Schema
from app.schemas.product import ProductShort


class DiscountIn(Schema):
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=40)
    type: DiscountType
    value: Money = Field(gt=0)
    scope: DiscountScope = DiscountScope.SUBSCRIPTION
    product_id: int | None = None
    min_purchase_amount: Money = Field(default=Decimal("0"), ge=0)
    min_quantity: int = Field(default=0, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    max_uses: int | None = Field(default=None, ge=1)
    is_active: bool = True
    notes: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> "DiscountIn":
        if self.scope is DiscountScope.PRODUCT and self.product_id is None:
            raise ValueError("A product-scoped discount needs product_id.")
        if self.type is DiscountType.PERCENTAGE and self.value > 100:
            raise ValueError("A percentage discount cannot exceed 100.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class DiscountUpdateIn(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=40)
    value: Money | None = Field(default=None, gt=0)
    min_purchase_amount: Money | None = Field(default=None, ge=0)
    min_quantity: int | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    max_uses: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    notes: str | None = None


class DiscountOut(Schema):
    id: int
    name: str
    code: str | None
    type: DiscountType
    value: Money
    scope: DiscountScope
    product: ProductShort | None
    min_purchase_amount: Money
    min_quantity: int
    start_date: date | None
    end_date: date | None
    max_uses: int | None
    used_count: int
    is_active: bool
    notes: str | None
    created_at: datetime


class SubscriptionDiscountOut(Schema):
    id: int
    discount: DiscountOut
    applied_at: datetime
    removed_at: datetime | None


class ApplyDiscountIn(Schema):
    discount_id: int
