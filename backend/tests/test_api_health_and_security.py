from __future__ import annotations

from app.config import settings


def test_health_check_includes_security_headers(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_admin_endpoint_rejects_missing_key(client):
    response = client.post(
        "/gates/gate_a/signage",
        json={"gate_id": "gate_a", "message": "Use Gate B"},
    )

    assert response.status_code == 422


def test_admin_endpoint_rejects_bad_key(client):
    response = client.post(
        "/gates/gate_a/signage",
        headers={"X-API-Key": "wrong"},
        json={"gate_id": "gate_a", "message": "Use Gate B"},
    )

    assert response.status_code == 401


def test_admin_endpoint_fails_closed_when_key_unconfigured(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "")

    response = client.post(
        "/gates/gate_a/signage",
        headers={"X-API-Key": "anything"},
        json={"gate_id": "gate_a", "message": "Use Gate B"},
    )

    assert response.status_code == 503
