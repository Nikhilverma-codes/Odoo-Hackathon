"""Factories shared by the test modules and fixtures."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models import (
    BillingInterval,
    Customer,
    Plan,
    Product,
    Role,
    Tax,
    User,
)


def make_user(
    db: Session, email: str, role: Role = Role.ADMIN, customer: Customer | None = None
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("Passw0rd!"),
        full_name=email.split("@")[0].title(),
        role=role,
        customer_id=customer.id if customer else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_customer(db: Session, name: str = "Acme Retail", email: str | None = None) -> Customer:
    customer = Customer(name=name, email=email or f"{name.lower().replace(' ', '.')}@test.io")
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def make_catalogue(db: Session, price: str = "100") -> tuple[Product, Plan, Tax]:
    tax = Tax(name="VAT 15%", rate=15)
    db.add(tax)
    db.flush()
    product = Product(name="Brightloop ERP", sales_price=price, tax_id=tax.id)
    db.add(product)
    db.flush()
    plan = Plan(
        code="ERP-MONTHLY",
        name="ERP Monthly",
        product_id=product.id,
        price=price,
        interval=BillingInterval.MONTHLY,
        min_quantity=1,
        tax_id=tax.id,
    )
    db.add(plan)
    db.commit()
    db.refresh(product)
    db.refresh(plan)
    db.refresh(tax)
    return product, plan, tax
