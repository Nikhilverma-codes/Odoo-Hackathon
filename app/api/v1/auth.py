from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_token,
    validate_password,
    verify_password,
)
from app.db.base import utcnow
from app.models import Customer, PasswordResetToken, Role, User
from app.schemas.auth import (
    AuthResultOut,
    ChangePasswordIn,
    ForgotPasswordIn,
    ForgotPasswordOut,
    LoginIn,
    RegisterIn,
    ResetPasswordIn,
    TokenOut,
    UserOut,
)
from app.schemas.common import MessageOut
from app.services.email import send_password_reset

router = APIRouter(prefix="/auth", tags=["auth"])

#: Compared against when the email is unknown, to keep login timing uniform.
_DUMMY_HASH = hash_password("not-a-real-password-A1!")


def _issue_token(user: User) -> AuthResultOut:
    expires_in = settings.access_token_expire_minutes * 60
    token = create_access_token(
        user.id, role=user.role.value, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    return AuthResultOut(
        token=TokenOut(access_token=token, expires_in=expires_in),
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=AuthResultOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: DbSession) -> AuthResultOut:
    """Public signup: one email, one account."""
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    if db.scalar(select(Customer.id).where(Customer.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    customer = Customer(
        name=payload.company_name or payload.full_name,
        email=email,
        phone=payload.phone,
    )
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=Role.CUSTOMER,
        customer=customer,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.post("/login", response_model=AuthResultOut)
def login(payload: LoginIn, db: DbSession) -> AuthResultOut:
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    stored = user.hashed_password if user else _DUMMY_HASH
    password_ok = verify_password(payload.password, stored)

    if not user or not password_ok:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled")

    user.last_login_at = utcnow()
    db.commit()
    return _issue_token(user)


@router.post("/token", response_model=TokenOut, include_in_schema=True)
def login_form(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession
) -> TokenOut:
    """OAuth2 password flow, used by the Swagger "Authorize" button."""
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled")

    user.last_login_at = utcnow()
    db.commit()
    return TokenOut(
        access_token=create_access_token(
            user.id,
            role=user.role.value,
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        ),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserOut)
def read_me(user: CurrentUser) -> User:
    return user


@router.post("/me/password", response_model=MessageOut)
def change_password(payload: ChangePasswordIn, user: CurrentUser, db: DbSession) -> MessageOut:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.hashed_password = hash_password(validate_password(payload.new_password))
    db.add(user)
    db.commit()
    return MessageOut(message="Password updated")


@router.post("/forgot-password", response_model=ForgotPasswordOut)
def forgot_password(payload: ForgotPasswordIn, db: DbSession) -> ForgotPasswordOut:
    """Always answers the same way, so the endpoint cannot be used to enumerate users."""
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email))

    raw_token: str | None = None
    reset_url: str | None = None

    if user and user.is_active:
        raw_token, token_hash = generate_reset_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=utcnow() + timedelta(minutes=settings.password_reset_expire_minutes),
                created_at=utcnow(),
            )
        )
        db.commit()
        reset_url = f"{settings.frontend_url}/reset-password?token={raw_token}"
        send_password_reset(to=user.email, full_name=user.full_name, reset_url=reset_url)

    response = ForgotPasswordOut(
        message="If that email is registered, a reset link is on its way."
    )
    if not settings.is_production and raw_token:
        # Handy for local development / tests without an SMTP server.
        response.reset_token = raw_token
        response.reset_url = reset_url
    return response


@router.post("/reset-password", response_model=MessageOut)
def reset_password(payload: ResetPasswordIn, db: DbSession) -> MessageOut:
    token_hash = hash_token(payload.token)
    record = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    if not record or record.used_at is not None or record.expires_at < utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or expired")

    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or expired")

    user.hashed_password = hash_password(payload.password)
    record.used_at = utcnow()
    # Invalidate every other outstanding reset for this user.
    for other in db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
        )
    ):
        other.used_at = utcnow()
    db.commit()
    return MessageOut(message="Password reset. You can now sign in.")
