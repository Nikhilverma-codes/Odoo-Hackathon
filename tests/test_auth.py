from __future__ import annotations

from app.core.security import password_policy_violations
from app.models import Role
from tests.factories import auth_headers, make_user


def test_password_policy_rules():
    assert password_policy_violations("Passw0rd!") == []
    assert "must be longer than 8 characters" in password_policy_violations("Pass0rd!")
    assert "must contain an uppercase letter" in password_policy_violations("passw0rd!")
    assert "must contain a lowercase letter" in password_policy_violations("PASSW0RD!")
    assert "must contain a special character" in password_policy_violations("Passw0rdd")


def test_register_login_and_me(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@acme.io",
            "password": "Passw0rd!",
            "full_name": "New Customer",
            "company_name": "Acme Retail",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["role"] == "customer"
    token = body["token"]["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new@acme.io"

    # Same email can only ever belong to one account.
    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@acme.io",
            "password": "Passw0rd!",
            "full_name": "Impostor",
        },
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/api/v1/auth/login", json={"email": "new@acme.io", "password": "Passw0rd!"}
    )
    assert login.status_code == 200
    assert login.json()["token"]["token_type"] == "bearer"

    bad = client.post(
        "/api/v1/auth/login", json={"email": "new@acme.io", "password": "WrongPass1!"}
    )
    assert bad.status_code == 401


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@acme.io", "password": "password", "full_name": "Weak"},
    )
    assert response.status_code == 422
    message = str(response.json())
    assert "uppercase" in message


def test_forgot_and_reset_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "reset@acme.io", "password": "Passw0rd!", "full_name": "Reset Me"},
    )

    forgot = client.post("/api/v1/auth/forgot-password", json={"email": "reset@acme.io"})
    assert forgot.status_code == 200
    token = forgot.json()["reset_token"]
    assert token

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "BrandNew1!"},
    )
    assert reset.status_code == 200, reset.text

    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "reset@acme.io", "password": "BrandNew1!"},
        ).status_code
        == 200
    )
    # A token can only be used once.
    reused = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "Another1!"},
    )
    assert reused.status_code == 400


def test_unknown_email_does_not_leak(client):
    response = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@acme.io"})
    assert response.status_code == 200
    assert response.json()["reset_token"] is None


def test_only_admin_can_create_staff(client, db):
    admin = make_user(db, "admin@brightloop.io")
    staff = make_user(db, "staff@brightloop.io", role=Role.STAFF)

    payload = {
        "email": "newstaff@brightloop.io",
        "password": "Passw0rd!",
        "full_name": "New Staff",
    }
    forbidden = client.post(
        "/api/v1/users/staff", json=payload, headers=auth_headers(staff)
    )
    assert forbidden.status_code == 403

    allowed = client.post("/api/v1/users/staff", json=payload, headers=auth_headers(admin))
    assert allowed.status_code == 201
    assert allowed.json()["role"] == "staff"
