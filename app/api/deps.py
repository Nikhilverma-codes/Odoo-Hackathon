"""Reusable FastAPI dependencies: auth, roles, pagination."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Role, User

DbSession = Annotated[Session, Depends(get_db)]

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/token", auto_error=False
)

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    if not token:
        raise _credentials_error
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", ""))
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise _credentials_error from exc

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise _credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role):
    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this resource",
            )
        return user

    return dependency


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
StaffUser = Annotated[User, Depends(require_roles(Role.ADMIN, Role.STAFF))]


class Pagination:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="1-based page number"),
        page_size: int = Query(20, ge=1, le=200, description="Rows per page"),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


PaginationDep = Annotated[Pagination, Depends(Pagination)]


def ensure_customer_access(user: User, customer_id: int | None) -> None:
    """Customers may only touch their own account."""
    if user.role is Role.CUSTOMER and user.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own account",
        )
