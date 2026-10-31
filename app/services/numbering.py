from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Invoice, Subscription


def next_document_number(db: Session, prefix: str, model=Subscription) -> str:
    """Sequential per-year document number, e.g. SUB/2026/00042."""
    year = date.today().year
    pattern = f"{prefix}/{year}/%"
    if model is Subscription:
        column = Subscription.number
    elif model is Invoice:
        column = Invoice.number
    else:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported model for numbering: {model!r}")

    last = db.scalar(select(func.max(column)).where(column.like(pattern)))
    sequence = int(last.rsplit("/", 1)[-1]) + 1 if last else 1
    return f"{prefix}/{year}/{sequence:05d}"
