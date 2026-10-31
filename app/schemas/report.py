from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.models.invoice import InvoiceStatus
from app.schemas.common import Money, Schema
from app.schemas.invoice import InvoiceOut


class UpcomingRenewalOut(Schema):
    subscription_id: int
    number: str
    customer_name: str
    next_billing_date: date
    amount: Money


class InvoiceStatusBreakdownOut(Schema):
    status: InvoiceStatus
    count: int
    total: Money


class ReportSummaryOut(Schema):
    generated_at: datetime
    as_of: date
    period_start: date
    period_end: date
    active_subscriptions: int
    paused_subscriptions: int
    mrr: Money
    arr: Money
    revenue_invoiced: Money
    revenue_collected: Money
    outstanding_amount: Money
    overdue_invoices: int
    overdue_amount: Money
    invoices_by_status: list[InvoiceStatusBreakdownOut]
    upcoming_renewals: list[UpcomingRenewalOut]


class RevenuePointOut(Schema):
    period: str
    invoiced: Money
    collected: Money


class RevenueReportOut(Schema):
    date_from: date
    date_to: date
    group_by: str
    total_invoiced: Money
    total_collected: Money
    points: list[RevenuePointOut]


class OverdueInvoiceOut(Schema):
    invoice: InvoiceOut
    days_overdue: int


class ReportQuery(Schema):
    date_from: date | None = Field(default=None)
    date_to: date | None = Field(default=None)
