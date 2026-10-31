from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.api.deps import DbSession, StaffUser
from app.schemas.report import (
    OverdueInvoiceOut,
    ReportSummaryOut,
    RevenueReportOut,
)
from app.schemas.invoice import InvoiceOut
from app.services import reporting

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=ReportSummaryOut)
def summary(
    staff: StaffUser,
    db: DbSession,
    as_of: date | None = Query(None, description="Defaults to today"),
):
    """One screen for the finance lead: active subs, revenue, outstanding, overdue."""
    return reporting.summary(db, as_of)


@router.get("/revenue", response_model=RevenueReportOut)
def revenue(
    staff: StaffUser,
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    group_by: str = Query("month", pattern="^(day|month)$"),
):
    today = date.today()
    start = date_from or (today.replace(day=1) - timedelta(days=150))
    end = date_to or today
    return reporting.revenue_report(db, start, end, group_by)


@router.get("/overdue", response_model=list[OverdueInvoiceOut])
def overdue(
    staff: StaffUser,
    db: DbSession,
    as_of: date | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    rows = reporting.overdue_invoices(db, as_of, limit)
    return [
        {
            "invoice": InvoiceOut.model_validate(row["invoice"]),
            "days_overdue": row["days_overdue"],
        }
        for row in rows
    ]
