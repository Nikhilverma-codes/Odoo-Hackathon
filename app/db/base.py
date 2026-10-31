"""Declarative base plus shared column types and mixins."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum, Integer, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite has no timezone support)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Money(TypeDecorator):
    """Store money as integer cents, expose `Decimal` in Python."""

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> int | None:
        if value is None:
            return None
        return int((Decimal(str(value)) * 100).quantize(Decimal("1")))

    def process_result_value(self, value: Any, dialect: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(int(value)) / 100


class Rate(TypeDecorator):
    """A percentage such as 15.0000 stored as an integer basis-points value."""

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> int | None:
        if value is None:
            return None
        return int((Decimal(str(value)) * 10_000).quantize(Decimal("1")))

    def process_result_value(self, value: Any, dialect: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(int(value)) / 10_000


def enum_column(enum_cls: type[PyEnum], length: int = 32) -> SAEnum:
    """Store enum *values* (not names) as plain strings, without native enums."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
