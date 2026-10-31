from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, or_, select

from app.api.deps import AdminUser, CurrentUser, DbSession, PaginationDep
from app.api.pagination import paginate
from app.models import BillingInterval, Plan, Product, Tax
from app.schemas.common import MessageOut, Page
from app.schemas.plan import PlanIn, PlanOut, PlanUpdateIn

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=Page[PlanOut])
def list_plans(
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    q: str | None = None,
    product_id: int | None = None,
    interval: BillingInterval | None = None,
    is_active: bool | None = None,
    available_on: date | None = None,
):
    stmt = select(Plan)
    if q:
        needle = f"%{q.lower()}%"
        stmt = stmt.where(or_(Plan.name.ilike(needle), Plan.code.ilike(needle)))
    if product_id is not None:
        stmt = stmt.where(Plan.product_id == product_id)
    if interval is not None:
        stmt = stmt.where(Plan.interval == interval)
    if is_active is not None:
        stmt = stmt.where(Plan.is_active == is_active)
    if available_on is not None:
        stmt = stmt.where(
            and_(
                or_(Plan.available_from.is_(None), Plan.available_from <= available_on),
                or_(Plan.available_to.is_(None), Plan.available_to >= available_on),
            )
        )
    stmt = stmt.order_by(Plan.name, Plan.id)
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanIn, admin: AdminUser, db: DbSession):
    if not db.get(Product, payload.product_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Product not found")
    if payload.tax_id is not None and not db.get(Tax, payload.tax_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tax not found")
    if db.scalar(select(Plan.id).where(Plan.code == payload.code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A plan with this code already exists")

    plan = Plan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, user: CurrentUser, db: DbSession):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    return plan


@router.patch("/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, payload: PlanUpdateIn, admin: AdminUser, db: DbSession):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    if payload.tax_id is not None and not db.get(Tax, payload.tax_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tax not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(plan, field, value)

    if plan.available_from and plan.available_to and plan.available_to < plan.available_from:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "available_to must be on or after available_from"
        )

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", response_model=MessageOut)
def deactivate_plan(plan_id: int, admin: AdminUser, db: DbSession):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    plan.is_active = False
    db.add(plan)
    db.commit()
    return MessageOut(message=f"Plan {plan.code} deactivated")
