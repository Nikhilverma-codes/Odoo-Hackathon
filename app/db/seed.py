"""Demo dataset: one billing month at Brightloop Software.

Idempotent - it bails out as soon as the admin account exists.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    BillingInterval,
    Customer,
    Discount,
    DiscountScope,
    DiscountType,
    PaymentMethod,
    Plan,
    Product,
    ProductType,
    ProductVariant,
    QuotationTemplate,
    QuotationTemplateLine,
    Role,
    SubscriptionStatus,
    Tax,
    User,
)
from app.schemas.invoice import PaymentCreateIn
from app.schemas.subscription import SubscriptionCreateIn, SubscriptionLineIn
from app.services import billing, invoices as invoice_service
from app.services import subscriptions as subscription_service

logger = logging.getLogger("brightloop.seed")


def seed_demo_data(db: Session) -> bool:
    if db.scalar(select(User.id).where(User.email == "admin@brightloop.io")):
        return False

    today = date.today()

    # ------------------------------------------------------------------ users
    admin = User(
        email="admin@brightloop.io",
        hashed_password=hash_password("Admin@1234"),
        full_name="Avery Admin",
        role=Role.ADMIN,
    )
    staff = User(
        email="sales@brightloop.io",
        hashed_password=hash_password("Staff@1234"),
        full_name="Sam Sales",
        role=Role.STAFF,
    )
    db.add_all([admin, staff])
    db.flush()

    # ---------------------------------------------------------------- customers
    acme = Customer(
        name="Acme Retail",
        email="billing@acme-retail.com",
        phone="+1 555 0100",
        billing_address="12 Market Street, Springfield",
        tax_id="ACME-9911",
    )
    northwind = Customer(
        name="Northwind Trading",
        email="finance@northwind.com",
        phone="+1 555 0144",
        billing_address="900 Harbour Road, Boston",
        tax_id="NW-2200",
    )
    lumen = Customer(
        name="Lumen Studio",
        email="hello@lumen-studio.com",
        billing_address="4 Rue de Lumière, Lyon",
    )
    db.add_all([acme, northwind, lumen])
    db.flush()

    for customer in (acme, northwind, lumen):
        db.add(
            User(
                email=customer.email,
                hashed_password=hash_password("Customer@1234"),
                full_name=f"{customer.name} Portal",
                role=Role.CUSTOMER,
                customer_id=customer.id,
            )
        )

    # -------------------------------------------------------------------- taxes
    vat = Tax(name="VAT 15%", rate=15, description="Standard sales tax")
    reduced = Tax(name="VAT 5%", rate=5, description="Reduced rate for add-ons")
    db.add_all([vat, reduced])
    db.flush()

    # ----------------------------------------------------------------- products
    erp = Product(
        name="Brightloop ERP",
        type=ProductType.MODULE,
        sales_price=1200,
        cost_price=300,
        notes="Core business suite, billed per seat.",
        tax_id=vat.id,
    )
    analytics = Product(
        name="Analytics Add-on",
        type=ProductType.ADDON,
        sales_price=250,
        cost_price=40,
        notes="Dashboards and scheduled reports.",
        tax_id=reduced.id,
    )
    support = Product(
        name="Priority Support",
        type=ProductType.SUPPORT,
        sales_price=4000,
        cost_price=1200,
        notes="24/7 response, yearly contract.",
        tax_id=vat.id,
    )
    db.add_all([erp, analytics, support])
    db.flush()

    db.add_all(
        [
            ProductVariant(product_id=erp.id, name="Odoo brand", price_delta=560),
            ProductVariant(product_id=erp.id, name="Brightloop brand", price_delta=0),
        ]
    )

    # -------------------------------------------------------------------- plans
    monthly = Plan(
        code="ERP-MONTHLY",
        name="ERP Monthly",
        product_id=erp.id,
        price=1200,
        interval=BillingInterval.MONTHLY,
        min_quantity=1,
        auto_close_on_expiry=True,
        allow_early_close=True,
        allow_pause=True,
        allow_renew=True,
        tax_id=vat.id,
    )
    yearly = Plan(
        code="ERP-YEARLY",
        name="ERP Yearly",
        product_id=erp.id,
        price=12000,
        interval=BillingInterval.YEARLY,
        min_quantity=1,
        available_from=today - timedelta(days=365),
        auto_close_on_expiry=True,
        allow_early_close=False,
        allow_pause=False,
        allow_renew=True,
        tax_id=vat.id,
    )
    db.add_all([monthly, yearly])
    db.flush()

    template = QuotationTemplate(
        name="Enterprise ERP Offer",
        plan_id=yearly.id,
        validity_days=30,
        payment_terms_days=30,
        notes="Standard enterprise bundle, valid for 30 days.",
    )
    template.lines = [
        QuotationTemplateLine(product_id=erp.id, quantity=10, unit_price=12000),
        QuotationTemplateLine(product_id=support.id, quantity=1),
    ]
    db.add(template)
    db.flush()

    # ---------------------------------------------------------------- discounts
    volume = Discount(
        name="Volume seats 10%",
        code="SEATS10",
        type=DiscountType.PERCENTAGE,
        value=10,
        scope=DiscountScope.SUBSCRIPTION,
        min_quantity=3,
        notes="Applies to subscriptions with at least three seats.",
    )
    brand_launch = Discount(
        name="Odoo brand launch",
        code="ODOO500",
        type=DiscountType.FIXED,
        value=500,
        scope=DiscountScope.PRODUCT,
        product_id=erp.id,
        max_uses=50,
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=120),
    )
    db.add_all([volume, brand_launch])
    db.flush()

    # ------------------------------------------------------------ subscriptions
    acme_sub = subscription_service.create_subscription(
        db,
        SubscriptionCreateIn(
            customer_id=acme.id,
            plan_id=monthly.id,
            start_date=today - timedelta(days=75),
            payment_terms_days=5,
            notes="Monthly seats, volume discount applied.",
            lines=[
                SubscriptionLineIn(product_id=erp.id, quantity=5, unit_price=1200),
                SubscriptionLineIn(product_id=analytics.id, quantity=1, unit_price=250),
            ],
            discount_ids=[volume.id],
        ),
        admin,
    )
    subscription_service.transition(db, acme_sub, SubscriptionStatus.CONFIRMED, admin, "Quote accepted")
    subscription_service.transition(db, acme_sub, SubscriptionStatus.ACTIVE, admin, "Live")

    northwind_sub = subscription_service.create_subscription(
        db,
        SubscriptionCreateIn(
            customer_id=northwind.id,
            plan_id=yearly.id,
            start_date=today - timedelta(days=40),
            payment_terms_days=30,
            notes="Annual enterprise contract.",
            lines=[
                SubscriptionLineIn(product_id=erp.id, quantity=1, unit_price=12000),
                SubscriptionLineIn(product_id=support.id, quantity=2, unit_price=4000),
            ],
            discount_ids=[brand_launch.id],
        ),
        admin,
    )
    subscription_service.transition(
        db, northwind_sub, SubscriptionStatus.CONFIRMED, admin, "Signed contract"
    )
    subscription_service.transition(db, northwind_sub, SubscriptionStatus.ACTIVE, admin, "Live")

    # A quote built from the template - stays in the pipeline, never billed.
    subscription_service.create_subscription(
        db,
        SubscriptionCreateIn(
            customer_id=lumen.id,
            plan_id=yearly.id,
            start_date=today + timedelta(days=5),
            quotation_template_id=template.id,
            status=SubscriptionStatus.QUOTATION,
            notes="Sent from the enterprise template.",
        ),
        staff,
    )

    # --------------------------------------------------------------- billing run
    result = billing.run_billing(db, as_of=today, auto_confirm=True)
    logger.info("Seed billing run: %s", result)

    # -------------------------------------------------------------- payments
    db.flush()
    return _seed_payments(db, acme_sub.id, northwind_sub.id, admin)


def _seed_payments(db: Session, acme_sub_id: int, northwind_sub_id: int, admin: User) -> bool:
    from app.models import Invoice

    today = date.today()
    acme_invoices = list(
        db.scalars(
            select(Invoice)
            .where(Invoice.subscription_id == acme_sub_id)
            .order_by(Invoice.issue_date)
        )
    )
    if len(acme_invoices) >= 2:
        first, second = acme_invoices[0], acme_invoices[1]
        invoice_service.record_payment(
            db,
            first,
            PaymentCreateIn(
                method=PaymentMethod.BANK_TRANSFER,
                amount=first.amount_due,
                paid_on=first.issue_date + timedelta(days=2),
                reference="ACME-SEPA-0912",
            ),
            admin,
        )
        invoice_service.record_payment(
            db,
            second,
            PaymentCreateIn(
                method=PaymentMethod.CARD,
                amount=second.amount_due,
                paid_on=today,
                reference="ACME-CARD-1024",
                note="Paid in full by finance",
            ),
            admin,
        )

    northwind_invoice = db.scalar(
        select(Invoice)
        .where(Invoice.subscription_id == northwind_sub_id)
        .order_by(Invoice.issue_date)
    )
    if northwind_invoice:
        invoice_service.record_payment(
            db,
            northwind_invoice,
            PaymentCreateIn(
                method=PaymentMethod.BANK_TRANSFER,
                amount=8000,
                paid_on=today,
                reference="NW-WIRE-5501",
                note="Part payment, balance promised next week",
            ),
            admin,
        )

    db.commit()
    return True
