from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.core.security import validate_password
from app.models.user import Role
from app.schemas.common import Schema


class _PasswordMixin:
    password: str = Field(min_length=1, max_length=128)

    @field_validator("password")
    @classmethod
    def _check_policy(cls, value: str) -> str:
        return validate_password(value)


class RegisterIn(_PasswordMixin, Schema):
    """Public self-signup: creates a customer account plus its portal user."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=160)
    company_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=40)


class LoginIn(Schema):
    email: EmailStr
    password: str


class TokenOut(Schema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(Schema):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    customer_id: int | None
    last_login_at: datetime | None
    created_at: datetime


class AuthResultOut(Schema):
    token: TokenOut
    user: UserOut


class ForgotPasswordIn(Schema):
    email: EmailStr


class ForgotPasswordOut(Schema):
    message: str
    # Only returned outside production, so local dev can click through without SMTP.
    reset_token: str | None = None
    reset_url: str | None = None


class ResetPasswordIn(_PasswordMixin, Schema):
    token: str = Field(min_length=10)


class ChangePasswordIn(Schema):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _check_policy(cls, value: str) -> str:
        return validate_password(value)
