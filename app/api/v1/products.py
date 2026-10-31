from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import AdminUser, CurrentUser, DbSession, PaginationDep
from app.api.pagination import paginate
from app.models import Product, ProductType, ProductVariant, Tax
from app.schemas.common import MessageOut, Page
from app.schemas.product import (
    ProductIn,
    ProductOut,
    ProductUpdateIn,
    VariantIn,
    VariantOut,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=Page[ProductOut])
def list_products(
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    q: str | None = None,
    type: ProductType | None = None,
    is_active: bool | None = None,
):
    stmt = select(Product)
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q.lower()}%"))
    if type is not None:
        stmt = stmt.where(Product.type == type)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
    stmt = stmt.order_by(Product.name, Product.id)
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductIn, admin: AdminUser, db: DbSession):
    if payload.tax_id is not None and not db.get(Tax, payload.tax_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tax not found")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.post("/{product_id}/variants", response_model=VariantOut, status_code=status.HTTP_201_CREATED)
def add_variant(product_id: int, payload: VariantIn, admin: AdminUser, db: DbSession):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    if any(variant.name.lower() == payload.name.lower() for variant in product.variants):
        raise HTTPException(status.HTTP_409_CONFLICT, "This variant already exists")

    variant = ProductVariant(product_id=product.id, **payload.model_dump())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.patch("/variants/{variant_id}", response_model=VariantOut)
def update_variant(variant_id: int, payload: VariantIn, admin: AdminUser, db: DbSession):
    variant = db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variant not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(variant, field, value)
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(variant_id: int, admin: AdminUser, db: DbSession) -> Response:
    variant = db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variant not found")
    variant.is_active = False
    db.add(variant)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, user: CurrentUser, db: DbSession):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdateIn, admin: AdminUser, db: DbSession):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    if payload.tax_id is not None and not db.get(Tax, payload.tax_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tax not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=MessageOut)
def deactivate_product(product_id: int, admin: AdminUser, db: DbSession):
    """Soft delete - historical invoices keep referring to the product."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    product.is_active = False
    db.add(product)
    db.commit()
    return MessageOut(message=f"Product {product.name} deactivated")
