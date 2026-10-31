from __future__ import annotations

from datetime import date, datetime

from pydantic import Field, model_validator

from app.models.plan import BillingInterval
from app.schemas.common import Money, Schema
from app.schemas.product import ProductShort, TaxOut


class PlanIn(Schema):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    product_id: int
    price: Money = Field(ge=0)
    interval: BillingInterval = BillingInterval.MONTHLY
    min_quantity: int = Field(default=1, ge=1)
    available_from: date | None = None
    available_to: date | None = None
    auto_close_on_expiry: bool = True
    allow_early_close: bool = True
    allow_pause: bool = True
    allow_renew: bool = True
    tax_id: int | None = None
    notes: str | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def _check_window(self) -> "PlanIn":
        if self.available_from and self.available_to:
            if self.available_to < self.available_from:
                raise ValueError("available_to must be on or after available_from")
        return self


class PlanUpdateIn(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    price: Money | None = Field(default=None, ge=0)
    interval: BillingInterval | None = None
    min_quantity: int | None = Field(default=None, ge=1)
    available_from: date | None = None
    available_to: date | None = None
    auto_close_on_expiry: bool | None = None
    allow_early_close: bool | None = None
    allow_pause: bool | None = None
    allow_renew: bool | None = None
    tax_id: int | None = None
    notes: str | None = None
    is_active: bool | None = None


class PlanShort(Schema):
    id: int
    code: str
    name: str
    interval: BillingInterval
    price: Money


class PlanOut(PlanShort):
    product: ProductShort
    tax: TaxOut | None
    min_quantity: int
    available_from: date | None
    available_to: date | None
    auto_close_on_expiry: bool
    allow_early_close: bool
    allow_pause: bool
    allow_renew: bool
    notes: str | None
    is_active: bool
    created_at: datetime
