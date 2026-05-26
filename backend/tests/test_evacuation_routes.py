from __future__ import annotations

from app.models.evacuation import EvacuationAssessment
from app.routes import evacuation


def test_assess_requires_admin_key(client):
    response = client.post(
        "/evacuation/assess",
        json={"stadium_id": "test_stadium", "reason": "smoke"},
    )

    assert response.status_code == 422


def test_assess_without_sensor_data_returns_no_hazard(client, admin_headers):
    response = client.post(
        "/evacuation/assess",
        headers=admin_headers,
        json={"stadium_id": "test_stadium", "reason": "routine"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stadium_id"] == "test_stadium"
    assert body["should_evacuate"] is False
    assert body["evacuation_message"] == "No sensor data provided for assessment."


def test_assess_with_sensor_data_uses_evacunet_without_live_services(
    client,
    admin_headers,
    monkeypatch,
):
    calls: dict[str, object] = {}

    def fake_assess_stadium(stadium_id, sensor_vectors, zone_ids):
        calls["stadium_id"] = stadium_id
        calls["zone_ids"] = zone_ids
        calls["sensor_count"] = len(sensor_vectors)
        return EvacuationAssessment(
            stadium_id=stadium_id,
            overall_probability=0.2,
            should_evacuate=False,
            evacuation_message="All clear.",
        )

    monkeypatch.setattr(evacuation, "assess_stadium", fake_assess_stadium)

    response = client.post(
        "/evacuation/assess",
        headers=admin_headers,
        json={
            "stadium_id": "test_stadium",
            "reason": "sensor check",
            "sensor_data": {
                "zone_a": {
                    "temperature": 31.5,
                    "humidity": 70,
                    "co2": 410,
                }
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["evacuation_message"] == "All clear."
    assert calls == {
        "stadium_id": "test_stadium",
        "zone_ids": ["zone_a"],
        "sensor_count": 1,
    }


def test_trigger_evacuation_writes_state(client, admin_headers, monkeypatch):
    writes: list[tuple[str, dict]] = []

    def fake_update_evacuation_state(stadium_id, state):
        writes.append((stadium_id, state))

    monkeypatch.setattr(
        evacuation.firestore_service,
        "update_evacuation_state",
        fake_update_evacuation_state,
    )

    response = client.post(
        "/evacuation/trigger",
        headers=admin_headers,
        json={
            "stadium_id": "test_stadium",
            "reason": "verified hazard",
            "affected_zones": ["zone_a"],
            "override_authority": "security_chief",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evacuation"] == "TRIGGERED"
    assert writes[0][0] == "test_stadium"
    assert writes[0][1]["state"] == "EVACUATING"
    assert writes[0][1]["affected_zones"] == ["zone_a"]
