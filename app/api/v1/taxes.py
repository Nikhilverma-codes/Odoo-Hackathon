from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AdminUser, CurrentUser, DbSession, PaginationDep
from app.api.pagination import paginate
from app.models import Product, Tax
from app.schemas.common import MessageOut, Page
from app.schemas.product import TaxIn, TaxOut

router = APIRouter(prefix="/taxes", tags=["taxes"])


@router.get("", response_model=Page[TaxOut])
def list_taxes(user: CurrentUser, db: DbSession, pagination: PaginationDep):
    stmt = select(Tax).order_by(Tax.name, Tax.id)
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.post("", response_model=TaxOut, status_code=status.HTTP_201_CREATED)
def create_tax(payload: TaxIn, admin: AdminUser, db: DbSession):
    if db.scalar(select(Tax.id).where(Tax.name == payload.name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A tax with this name already exists")
    tax = Tax(**payload.model_dump())
    db.add(tax)
    db.commit()
    db.refresh(tax)
    return tax


@router.patch("/{tax_id}", response_model=TaxOut)
def update_tax(tax_id: int, payload: TaxIn, admin: AdminUser, db: DbSession):
    tax = db.get(Tax, tax_id)
    if not tax:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tax not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tax, field, value)
    db.add(tax)
    db.commit()
    db.refresh(tax)
    return tax


@router.delete("/{tax_id}", response_model=MessageOut)
def deactivate_tax(tax_id: int, admin: AdminUser, db: DbSession):
    tax = db.get(Tax, tax_id)
    if not tax:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tax not found")
    in_use = db.scalar(select(Product.id).where(Product.tax_id == tax.id).limit(1))
    if in_use:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This tax is still assigned to products"
        )
    tax.is_active = False
    db.add(tax)
    db.commit()
    return MessageOut(message=f"Tax {tax.name} deactivated")
