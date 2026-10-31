from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.api.deps import AdminUser, DbSession, PaginationDep, StaffUser
from app.api.pagination import paginate
from app.models import Discount, DiscountScope, Product
from app.schemas.common import MessageOut, Page
from app.schemas.discount import DiscountIn, DiscountOut, DiscountUpdateIn

router = APIRouter(prefix="/discounts", tags=["discounts"])


@router.get("", response_model=Page[DiscountOut])
def list_discounts(
    staff: StaffUser,
    db: DbSession,
    pagination: PaginationDep,
    q: str | None = None,
    is_active: bool | None = None,
    scope: DiscountScope | None = None,
):
    stmt = select(Discount)
    if q:
        needle = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                Discount.name.ilike(needle),
                Discount.code.ilike(needle),
            )
        )
    if is_active is not None:
        stmt = stmt.where(Discount.is_active == is_active)
    if scope is not None:
        stmt = stmt.where(Discount.scope == scope)
    stmt = stmt.order_by(Discount.created_at.desc(), Discount.id.desc())
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.post("", response_model=DiscountOut, status_code=status.HTTP_201_CREATED)
def create_discount(payload: DiscountIn, admin: AdminUser, db: DbSession):
    """Only the admin can create discount rules."""
    if payload.product_id is not None and not db.get(Product, payload.product_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Product not found")
    if payload.code and db.scalar(select(Discount.id).where(Discount.code == payload.code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A discount with this code already exists")

    discount = Discount(**payload.model_dump())
    db.add(discount)
    db.commit()
    db.refresh(discount)
    return discount


@router.get("/{discount_id}", response_model=DiscountOut)
def get_discount(discount_id: int, staff: StaffUser, db: DbSession):
    discount = db.get(Discount, discount_id)
    if not discount:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discount not found")
    return discount


@router.patch("/{discount_id}", response_model=DiscountOut)
def update_discount(
    discount_id: int, payload: DiscountUpdateIn, admin: AdminUser, db: DbSession
):
    discount = db.get(Discount, discount_id)
    if not discount:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discount not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(discount, field, value)

    if discount.type.value == "percentage" and discount.value > 100:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A percentage cannot exceed 100")
    if discount.start_date and discount.end_date and discount.end_date < discount.start_date:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "end_date must be on or after start_date"
        )
    if (
        discount.scope is DiscountScope.PRODUCT
        and discount.product_id is None
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "A product-scoped discount needs product_id"
        )

    db.commit()
    db.refresh(discount)
    return discount


@router.delete("/{discount_id}", response_model=MessageOut)
def deactivate_discount(discount_id: int, admin: AdminUser, db: DbSession):
    discount = db.get(Discount, discount_id)
    if not discount:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discount not found")
    discount.is_active = False
    db.commit()
    return MessageOut(message=f"Discount {discount.name} deactivated")
