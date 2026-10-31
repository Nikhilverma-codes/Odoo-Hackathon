from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.api.deps import (
    CurrentUser,
    DbSession,
    PaginationDep,
    StaffUser,
    ensure_customer_access,
)
from app.api.pagination import paginate
from app.core.security import hash_password
from app.models import Customer, Role, User
from app.schemas.common import Page
from app.schemas.user import CustomerCreateIn, CustomerOut, CustomerUpdateIn

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=Page[CustomerOut])
def list_customers(
    staff: StaffUser,
    db: DbSession,
    pagination: PaginationDep,
    q: str | None = None,
    is_active: bool | None = None,
):
    stmt = select(Customer)
    if q:
        needle = f"%{q.lower()}%"
        stmt = stmt.where(or_(Customer.name.ilike(needle), Customer.email.ilike(needle)))
    if is_active is not None:
        stmt = stmt.where(Customer.is_active == is_active)
    stmt = stmt.order_by(Customer.name).order_by(Customer.id)
    items, total = paginate(db, stmt, pagination)
    return Page.build(items, total, pagination.page, pagination.page_size)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreateIn, staff: StaffUser, db: DbSession):
    email = str(payload.email).lower()
    if db.scalar(select(Customer.id).where(Customer.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A customer with this email already exists")

    customer = Customer(
        name=payload.name,
        contact_name=payload.contact_name,
        email=email,
        phone=payload.phone,
        billing_address=payload.billing_address,
        tax_id=payload.tax_id,
    )
    db.add(customer)
    db.flush()

    if payload.portal_password:
        db.add(
            User(
                email=email,
                hashed_password=hash_password(payload.portal_password),
                full_name=payload.name,
                role=Role.CUSTOMER,
                customer_id=customer.id,
            )
        )

    db.commit()
    db.refresh(customer)
    return customer


@router.get("/me", response_model=CustomerOut)
def read_my_customer(user: CurrentUser, db: DbSession):
    if user.role is not Role.CUSTOMER or user.customer_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This account is not linked to a customer")
    customer = db.get(Customer, user.customer_id)
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, user: CurrentUser, db: DbSession):
    ensure_customer_access(user, customer_id)
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int, payload: CustomerUpdateIn, staff: StaffUser, db: DbSession
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")

    data = payload.model_dump(exclude_unset=True)
    if "email" in data:
        email = str(data["email"]).lower()
        if db.scalar(
            select(Customer.id).where(Customer.email == email, Customer.id != customer.id)
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "A customer with this email already exists"
            )
        data["email"] = email

    for field, value in data.items():
        setattr(customer, field, value)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer
