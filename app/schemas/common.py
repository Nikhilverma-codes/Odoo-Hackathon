"""Shared schema helpers: money serialization, pagination envelopes."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer

#: Decimals are stored exactly, but emitted as plain JSON numbers for clients.
Money = Annotated[
    Decimal,
    PlainSerializer(lambda v: round(float(v), 2), return_type=float, when_used="json"),
]
Rate = Annotated[
    Decimal,
    PlainSerializer(lambda v: round(float(v), 4), return_type=float, when_used="json"),
]

T = TypeVar("T")


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    message: str


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, page_size: int) -> "Page[T]":
        pages = (total + page_size - 1) // page_size if page_size else 0
        return cls(
            items=items, total=total, page=page, page_size=page_size, pages=pages
        )
