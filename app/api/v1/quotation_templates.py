from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, PaginationDep, StaffUser
from app.api.pagination import paginate
from app.models import Plan, Product, ProductVariant, QuotationTemplate, QuotationTemplateLine
from app.schemas.common import MessageOut, Page
from app.schemas.invoice import TemplateIn, TemplateOut

router = APIRouter(prefix="/quotation-templates", tags=["quotation templates"])


@router.get("", response_model=Page[TemplateOut])
def list_templates(
    staff: StaffUser,
    db: DbSession,
    pagination: PaginationDep,
    is_active: bool | None = None,
):
    stmt = select(QuotationTemplate)
    if is_active is not None:
        stmt = stmt.where(QuotationTemplate.is_active == is_active)
    stmt = stmt.order_by(QuotationTemplate.name)
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(payload: TemplateIn, staff: StaffUser, db: DbSession):
    if not db.get(Plan, payload.plan_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Plan not found")
    if db.scalar(select(QuotationTemplate.id).where(QuotationTemplate.name == payload.name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A template with this name already exists")

    template = QuotationTemplate(
        name=payload.name,
        plan_id=payload.plan_id,
        validity_days=payload.validity_days,
        payment_terms_days=payload.payment_terms_days,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    for line in payload.lines:
        if not db.get(Product, line.product_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Product {line.product_id} not found")
        if line.variant_id is not None:
            variant = db.get(ProductVariant, line.variant_id)
            if not variant or variant.product_id != line.product_id:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Variant {line.variant_id} does not belong to product {line.product_id}",
                )
        template.lines.append(QuotationTemplateLine(**line.model_dump()))

    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: int, staff: StaffUser, db: DbSession):
    template = db.get(QuotationTemplate, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return template


@router.delete("/{template_id}", response_model=MessageOut)
def deactivate_template(template_id: int, staff: StaffUser, db: DbSession):
    template = db.get(QuotationTemplate, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    template.is_active = False
    db.add(template)
    db.commit()
    return MessageOut(message=f"Template {template.name} deactivated")
