from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.core.security import validate_password
from app.models.user import Role
from app.schemas.common import Schema


class CustomerShort(Schema):
    id: int
    name: str
    email: str


class CustomerOut(CustomerShort):
    contact_name: str | None
    phone: str | None
    billing_address: str | None
    tax_id: str | None
    is_active: bool
    created_at: datetime


class CustomerCreateIn(Schema):
    name: str = Field(min_length=1, max_length=160)
    contact_name: str | None = Field(default=None, max_length=160)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    billing_address: str | None = None
    tax_id: str | None = Field(default=None, max_length=60)
    portal_password: str | None = Field(default=None, description="Creates a portal login when set")

    @field_validator("portal_password")
    @classmethod
    def _check_policy(cls, value: str | None) -> str | None:
        return validate_password(value) if value else value


class CustomerUpdateIn(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    contact_name: str | None = Field(default=None, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    billing_address: str | None = None
    tax_id: str | None = Field(default=None, max_length=60)
    is_active: bool | None = None


class StaffCreateIn(Schema):
    """Only an admin may call this."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    full_name: str = Field(min_length=1, max_length=160)
    role: Role = Role.STAFF

    @field_validator("password")
    @classmethod
    def _check_policy(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("role")
    @classmethod
    def _staff_only(cls, value: Role) -> Role:
        if value is Role.CUSTOMER:
            raise ValueError("Use POST /auth/register or /customers to create customers.")
        return value


class UserUpdateIn(Schema):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None
