from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models import Invoice, Role
from tests.factories import auth_headers, make_catalogue, make_customer, make_user


@pytest.fixture()
def billing_setup(client, db: Session):
    admin = make_user(db, "admin@brightloop.io")
    customer = make_customer(db)
    product, plan, _ = make_catalogue(db)
    headers = auth_headers(admin)

    created = client.post(
        "/api/v1/subscriptions",
        headers=headers,
        json={
            "customer_id": customer.id,
            "plan_id": plan.id,
            "start_date": date.today().isoformat(),
            "payment_terms_days": 7,
            "lines": [
                {"product_id": product.id, "quantity": 2, "unit_price": 100},
            ],
        },
    )
    assert created.status_code == 201, created.text
    subscription = created.json()

    assert client.post(
        f"/api/v1/subscriptions/{subscription['id']}/confirm", headers=headers
    ).status_code == 200
    assert client.post(
        f"/api/v1/subscriptions/{subscription['id']}/activate", headers=headers
    ).status_code == 200

    return {
        "admin": admin,
        "customer": customer,
        "product": product,
        "plan": plan,
        "subscription": subscription,
        "headers": headers,
    }


def test_billing_run_creates_invoice_with_tax(client, billing_setup):
    headers = billing_setup["headers"]
    today = date.today().isoformat()

    run = client.post(
        "/api/v1/invoices/run-billing", headers=headers, json={"as_of": today}
    )
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["scanned"] == 1
    assert body["invoiced"] == 1
    assert body["closed"] == 0

    invoice = client.get(f"/api/v1/invoices/{body['invoice_ids'][0]}", headers=headers).json()
    assert invoice["subtotal"] == 200.0
    assert invoice["tax_total"] == 30.0
    assert invoice["total"] == 230.0
    assert invoice["status"] == "confirmed"
    assert invoice["amount_due"] == 230.0


def test_billing_run_never_bills_the_same_period_twice(client, billing_setup):
    headers = billing_setup["headers"]
    today = date.today().isoformat()

    first = client.post("/api/v1/invoices/run-billing", headers=headers, json={"as_of": today})
    second = client.post("/api/v1/invoices/run-billing", headers=headers, json={"as_of": today})

    assert first.json()["invoiced"] == 1
    assert second.json()["invoiced"] == 0

    invoices = client.get("/api/v1/invoices", headers=headers).json()
    assert invoices["total"] == 1


def test_billing_run_catches_up_missed_periods(client, billing_setup):
    headers = billing_setup["headers"]
    future = (date.today() + timedelta(days=70)).isoformat()

    run = client.post("/api/v1/invoices/run-billing", headers=headers, json={"as_of": future})
    assert run.status_code == 200
    # Three monthly periods (current, +30, +60) are billed in one pass.
    assert run.json()["invoiced"] == 3


def test_dry_run_writes_nothing(client, billing_setup):
    headers = billing_setup["headers"]
    run = client.post(
        "/api/v1/invoices/run-billing",
        headers=headers,
        json={"as_of": date.today().isoformat(), "dry_run": True},
    )
    assert run.json()["invoiced"] == 0
    assert client.get("/api/v1/invoices", headers=headers).json()["total"] == 0


def test_discount_applies_then_usage_limit_stops_it(client, billing_setup):
    headers = billing_setup["headers"]
    subscription_id = billing_setup["subscription"]["id"]

    rule = client.post(
        "/api/v1/discounts",
        headers=headers,
        json={
            "name": "Seat promo",
            "type": "percentage",
            "value": 10,
            "scope": "subscription",
            "max_uses": 1,
        },
    )
    assert rule.status_code == 201, rule.text
    discount_id = rule.json()["id"]

    applied = client.post(
        f"/api/v1/subscriptions/{subscription_id}/discounts",
        headers=headers,
        json={"discount_id": discount_id},
    )
    assert applied.status_code == 200, applied.text

    first = client.post(
        f"/api/v1/subscriptions/{subscription_id}/invoices", headers=headers
    )
    assert first.status_code == 201, first.text
    assert first.json()["discount_total"] == 20.0
    assert first.json()["subtotal"] == 200.0
    assert first.json()["total"] == 207.0
    assert first.json()["status"] == "confirmed"

    # The rule hit max_uses=1, so the next period bills at full price.
    second = client.post(
        f"/api/v1/subscriptions/{subscription_id}/invoices", headers=headers
    )
    assert second.status_code == 201
    assert second.json()["discount_total"] == 0.0
    assert second.json()["total"] == 230.0


def test_partial_then_full_payment(client, billing_setup):
    headers = billing_setup["headers"]
    run = client.post(
        "/api/v1/invoices/run-billing",
        headers=headers,
        json={"as_of": date.today().isoformat()},
    )
    invoice_id = run.json()["invoice_ids"][0]

    partial = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        headers=headers,
        json={"amount": 100, "method": "card", "reference": "CARD-1"},
    )
    assert partial.status_code == 201, partial.text

    invoice = client.get(f"/api/v1/invoices/{invoice_id}", headers=headers).json()
    assert invoice["status"] == "confirmed"
    assert invoice["amount_paid"] == 100.0
    assert invoice["amount_due"] == 130.0

    rest = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        headers=headers,
        json={"amount": 130, "method": "bank_transfer"},
    )
    assert rest.status_code == 201

    invoice = client.get(f"/api/v1/invoices/{invoice_id}", headers=headers).json()
    assert invoice["status"] == "paid"
    assert invoice["amount_due"] == 0.0

    overpay = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        headers=headers,
        json={"amount": 5, "method": "cash"},
    )
    assert overpay.status_code == 400


def test_cannot_pay_a_draft_invoice(client, billing_setup):
    headers = billing_setup["headers"]
    subscription_id = billing_setup["subscription"]["id"]
    invoice = client.post(
        f"/api/v1/subscriptions/{subscription_id}/invoices",
        headers=headers,
        params={"auto_confirm": False},
    ).json()
    assert invoice["status"] == "draft"

    payment = client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        headers=headers,
        json={"amount": 10, "method": "cash"},
    )
    assert payment.status_code == 400


def test_customer_only_sees_own_invoices(client, db, billing_setup):
    headers = billing_setup["headers"]
    run = client.post(
        "/api/v1/invoices/run-billing",
        headers=headers,
        json={"as_of": date.today().isoformat()},
    )
    invoice_id = run.json()["invoice_ids"][0]

    other_customer = make_customer(db, "Northwind Trading")
    outsider = make_user(
        db, "outsider@test.io", role=Role.CUSTOMER, customer=other_customer
    )
    outsider_headers = auth_headers(outsider)

    assert client.get(f"/api/v1/invoices/{invoice_id}", headers=outsider_headers).status_code == 403
    assert client.get("/api/v1/invoices", headers=outsider_headers).json()["total"] == 0

    owner = make_user(
        db,
        "owner@test.io",
        role=Role.CUSTOMER,
        customer=billing_setup["customer"],
    )
    own = client.get("/api/v1/invoices", headers=auth_headers(owner)).json()
    assert own["total"] == 1


def test_overdue_report_and_summary(client, db: Session, billing_setup):
    headers = billing_setup["headers"]
    run = client.post(
        "/api/v1/invoices/run-billing",
        headers=headers,
        json={"as_of": date.today().isoformat()},
    )
    invoice_id = run.json()["invoice_ids"][0]

    invoice = db.get(Invoice, invoice_id)
    invoice.due_date = date.today() - timedelta(days=4)
    db.commit()

    overdue = client.get("/api/v1/reports/overdue", headers=headers)
    assert overdue.status_code == 200
    assert len(overdue.json()) == 1
    assert overdue.json()[0]["days_overdue"] == 4

    summary = client.get("/api/v1/reports/summary", headers=headers).json()
    assert summary["active_subscriptions"] == 1
    assert summary["mrr"] == 200.0
    assert summary["arr"] == 2400.0
    assert summary["revenue_invoiced"] == 230.0
    assert summary["revenue_collected"] == 0.0
    assert summary["outstanding_amount"] == 230.0
    assert summary["overdue_invoices"] == 1
    assert summary["overdue_amount"] == 230.0
    assert summary["upcoming_renewals"][0]["amount"] == 200.0
