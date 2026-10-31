from __future__ import annotations

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination


def paginate(db: Session, stmt: Select[Any], pagination: Pagination) -> tuple[list[Any], int]:
    """Run `stmt` for one page and return (rows, total_count)."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(stmt.limit(pagination.page_size).offset(pagination.offset)).unique().all()
    )
    return rows, total
