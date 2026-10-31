from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.api.deps import AdminUser, DbSession, PaginationDep
from app.api.pagination import paginate
from app.core.security import hash_password
from app.models import Role, User
from app.schemas.auth import UserOut
from app.schemas.common import Page
from app.schemas.user import StaffCreateIn, UserUpdateIn

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[UserOut])
def list_users(
    admin: AdminUser,
    db: DbSession,
    pagination: PaginationDep,
    role: Role | None = None,
    is_active: bool | None = None,
    q: str | None = None,
):
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if q:
        needle = f"%{q.lower()}%"
        stmt = stmt.where(or_(User.email.ilike(needle), User.full_name.ilike(needle)))
    stmt = stmt.order_by(User.created_at.desc(), User.id.desc())
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.post("/staff", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreateIn, admin: AdminUser, db: DbSession):
    """Only admins can add internal team members."""
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, admin: AdminUser, db: DbSession):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdateIn, admin: AdminUser, db: DbSession):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id and payload.is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot disable your own account")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
