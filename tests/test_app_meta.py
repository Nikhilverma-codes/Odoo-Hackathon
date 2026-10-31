from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_SECRET, Settings
from app.main import SERVE_FRONTEND


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_api_route_stays_json(client):
    response = client.get("/api/v1/definitely-not-a-route")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.skipif(not SERVE_FRONTEND, reason="frontend build is not present")
def test_spa_entry_and_client_route_fallback(client):
    for path in ("/", "/invoices", "/portal"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")


def test_production_rejects_default_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key=DEFAULT_SECRET, _env_file=None)
