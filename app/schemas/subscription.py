from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, computed_field, field_validator

from app.models.subscription import SubscriptionStatus
from app.schemas.common import Money, Rate, Schema
from app.schemas.discount import SubscriptionDiscountOut
from app.schemas.plan import PlanShort
from app.schemas.product import ProductShort, VariantOut
from app.schemas.user import CustomerShort


class SubscriptionLineIn(Schema):
    product_id: int
    variant_id: int | None = None
    description: str | None = Field(default=None, max_length=255)
    quantity: int = Field(default=1, ge=1)
    unit_price: Money | None = Field(default=None, ge=0)
    tax_id: int | None = None


class SubscriptionLineOut(Schema):
    id: int
    product: ProductShort
    variant: VariantOut | None
    description: str | None
    quantity: int
    unit_price: Money
    tax_rate: Rate
    amount: Money


class SubscriptionCreateIn(Schema):
    customer_id: int
    plan_id: int
    quotation_template_id: int | None = None
    start_date: date | None = None
    expiry_date: date | None = None
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    notes: str | None = None
    status: SubscriptionStatus = SubscriptionStatus.DRAFT
    lines: list[SubscriptionLineIn] = Field(default_factory=list)
    discount_ids: list[int] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def _only_starting_states(cls, value: SubscriptionStatus) -> SubscriptionStatus:
        if value not in (SubscriptionStatus.DRAFT, SubscriptionStatus.QUOTATION):
            raise ValueError("A subscription must start as draft or quotation.")
        return value


class SubscriptionUpdateIn(Schema):
    expiry_date: date | None = None
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)
    notes: str | None = None
    lines: list[SubscriptionLineIn] | None = None
    discount_ids: list[int] | None = None


class StatusChangeIn(Schema):
    status: SubscriptionStatus
    note: str | None = Field(default=None, max_length=255)


class RenewIn(Schema):
    start_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None


class CloseIn(Schema):
    reason: str | None = Field(default=None, max_length=255)


class SubscriptionStatusHistoryOut(Schema):
    id: int
    from_status: SubscriptionStatus | None
    to_status: SubscriptionStatus
    note: str | None
    created_at: datetime


class SubscriptionOut(Schema):
    id: int
    number: str
    status: SubscriptionStatus
    customer: CustomerShort
    plan: PlanShort
    quotation_template_id: int | None
    start_date: date
    expiry_date: date | None
    payment_terms_days: int
    current_period_start: date | None
    current_period_end: date | None
    next_billing_date: date | None
    auto_close_on_expiry: bool
    allow_early_close: bool
    allow_pause: bool
    allow_renew: bool
    paused_at: datetime | None
    closed_at: datetime | None
    closed_reason: str | None
    renewed_from_id: int | None
    notes: str | None
    lines: list[SubscriptionLineOut]
    discounts: list[SubscriptionDiscountOut]
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def subtotal(self) -> float:
        return round(float(sum((line.amount for line in self.lines), Decimal("0.00"))), 2)


class SubscriptionDetailOut(SubscriptionOut):
    status_history: list[SubscriptionStatusHistoryOut]
