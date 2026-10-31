from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Role
from tests.factories import auth_headers, make_catalogue, make_customer, make_user


def _create_subscription(client, db: Session, **overrides):
    admin = make_user(db, "admin@brightloop.io")
    customer = make_customer(db)
    product, plan, _ = make_catalogue(db)
    payload = {
        "customer_id": customer.id,
        "plan_id": plan.id,
        "start_date": date.today().isoformat(),
        "payment_terms_days": 30,
        "lines": [{"product_id": product.id, "quantity": 1, "unit_price": 100}],
    }
    payload.update(overrides)
    response = client.post(
        "/api/v1/subscriptions", headers=auth_headers(admin), json=payload
    )
    return admin, customer, product, plan, response


def test_lifecycle_must_follow_the_state_machine(client, db):
    admin, *_ , response = _create_subscription(client, db)
    subscription = response.json()
    headers = auth_headers(admin)

    # draft -> active is not allowed
    jump = client.post(
        f"/api/v1/subscriptions/{subscription['id']}/activate", headers=headers
    )
    assert jump.status_code == 400

    client.post(f"/api/v1/subscriptions/{subscription['id']}/confirm", headers=headers)
    activated = client.post(
        f"/api/v1/subscriptions/{subscription['id']}/activate", headers=headers
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"
    assert activated.json()["next_billing_date"] == date.today().isoformat()

    paused = client.post(
        f"/api/v1/subscriptions/{subscription['id']}/pause", headers=headers
    )
    assert paused.json()["status"] == "paused"
    resumed = client.post(
        f"/api/v1/subscriptions/{subscription['id']}/resume", headers=headers
    )
    assert resumed.json()["status"] == "active"

    history = client.get(
        f"/api/v1/subscriptions/{subscription['id']}", headers=headers
    ).json()["status_history"]
    # created, confirmed, active, paused, active
    assert [row["to_status"] for row in history] == [
        "draft",
        "confirmed",
        "active",
        "paused",
        "active",
    ]


def test_plan_minimum_quantity_is_enforced(client, db):
    admin = make_user(db, "admin2@brightloop.io")
    customer = make_customer(db)
    product, plan, _ = make_catalogue(db)

    plan.min_quantity = 5
    db.commit()

    response = client.post(
        "/api/v1/subscriptions",
        headers=auth_headers(admin),
        json={
            "customer_id": customer.id,
            "plan_id": plan.id,
            "lines": [{"product_id": product.id, "quantity": 2}],
        },
    )
    assert response.status_code == 400
    assert "minimum quantity" in response.json()["detail"]


def test_variant_price_is_added(client, db):
    from app.models import ProductVariant

    admin = make_user(db, "admin3@brightloop.io")
    customer = make_customer(db)
    product, plan, _ = make_catalogue(db)
    variant = ProductVariant(product_id=product.id, name="Odoo brand", price_delta=560)
    db.add(variant)
    db.commit()

    response = client.post(
        "/api/v1/subscriptions",
        headers=auth_headers(admin),
        json={
            "customer_id": customer.id,
            "plan_id": plan.id,
            "lines": [{"product_id": product.id, "variant_id": variant.id, "quantity": 1}],
        },
    )
    assert response.status_code == 201, response.text
    line = response.json()["lines"][0]
    assert line["unit_price"] == 660.0
    assert line["amount"] == 660.0


def test_renewal_copies_lines_and_links_back(client, db):
    admin, customer, product, plan, response = _create_subscription(client, db)
    subscription = response.json()
    headers = auth_headers(admin)
    client.post(f"/api/v1/subscriptions/{subscription['id']}/confirm", headers=headers)
    client.post(f"/api/v1/subscriptions/{subscription['id']}/activate", headers=headers)

    renewed = client.post(
        f"/api/v1/subscriptions/{subscription['id']}/renew",
        headers=headers,
        json={"expiry_date": (date.today() + timedelta(days=365)).isoformat()},
    )
    assert renewed.status_code == 201, renewed.text
    body = renewed.json()
    assert body["renewed_from_id"] == subscription["id"]
    assert body["status"] == "active"
    assert body["lines"][0]["product"]["id"] == product.id
    assert body["number"] != subscription["number"]


def test_quotation_template_creates_subscription(client, db):
    admin = make_user(db, "admin4@brightloop.io")
    customer = make_customer(db)
    product, plan, _ = make_catalogue(db)

    template = client.post(
        "/api/v1/quotation-templates",
        headers=auth_headers(admin),
        json={
            "name": "Enterprise offer",
            "plan_id": plan.id,
            "validity_days": 14,
            "payment_terms_days": 45,
            "lines": [{"product_id": product.id, "quantity": 3}],
        },
    )
    assert template.status_code == 201, template.text
    template_id = template.json()["id"]

    created = client.post(
        "/api/v1/subscriptions",
        headers=auth_headers(admin),
        json={
            "customer_id": customer.id,
            "plan_id": plan.id,
            "quotation_template_id": template_id,
            "status": "quotation",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["lines"][0]["quantity"] == 3
    assert body["payment_terms_days"] == 45
    assert body["expiry_date"] == (date.today() + timedelta(days=14)).isoformat()


def test_customer_cannot_read_another_customers_subscription(client, db):
    admin, customer, product, plan, response = _create_subscription(client, db)
    subscription_id = response.json()["id"]

    other = make_customer(db, "Northwind Trading")
    outsider = make_user(db, "x@test.io", role=Role.CUSTOMER, customer=other)

    detail = client.get(
        f"/api/v1/subscriptions/{subscription_id}", headers=auth_headers(outsider)
    )
    assert detail.status_code == 403


def test_admin_only_endpoints_are_protected(client, db):
    customer = make_customer(db)
    customer_user = make_user(db, "c@test.io", role=Role.CUSTOMER, customer=customer)
    staff = make_user(db, "s@test.io", role=Role.STAFF)

    plan_payload = {
        "code": "X",
        "name": "X",
        "product_id": 1,
        "price": 10,
    }
    assert client.post(
        "/api/v1/plans", headers=auth_headers(customer_user), json=plan_payload
    ).status_code == 403
    assert client.post(
        "/api/v1/plans", headers=auth_headers(staff), json=plan_payload
    ).status_code == 403
    # 400/404 is fine - the point is it got past the role check.
    assert client.post(
        "/api/v1/plans", headers=auth_headers(make_user(db, "a@test.io")), json=plan_payload
    ).status_code in (400, 404)
