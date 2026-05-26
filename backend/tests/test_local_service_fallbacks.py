from __future__ import annotations

import pytest
from google.auth import exceptions as auth_exceptions

from app.config import settings
from app.services import bigquery_service, firestore_service


@pytest.fixture(autouse=True)
def reset_service_state(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")

    monkeypatch.setattr(firestore_service, "_client", None)
    monkeypatch.setattr(firestore_service, "_client_unavailable", False)
    firestore_service._local_store.clear()

    monkeypatch.setattr(bigquery_service, "_client", None)
    monkeypatch.setattr(bigquery_service, "_client_unavailable", False)


def test_firestore_uses_in_memory_store_when_credentials_are_missing(monkeypatch):
    def fail_client(*args, **kwargs):
        raise auth_exceptions.DefaultCredentialsError("missing adc")

    monkeypatch.setattr(firestore_service.firestore, "Client", fail_client)

    firestore_service.update_gate_status("test_stadium", "gate_a", {"density": 0.8})
    firestore_service.update_strict_protocol("test_stadium", "gate_a", True, banned_items=["bags"])
    firestore_service.add_report("test_stadium", {"message": "Queue building"})
    firestore_service.update_evacuation_state("test_stadium", {"state": "ALERT"})

    gate = firestore_service.get_gate("test_stadium", "gate_a")
    assert gate["density"] == 0.8
    assert gate["strict_protocol"]["active"] is True
    assert gate["strict_protocol"]["banned_items"] == ["bags"]
    assert firestore_service.get_all_gates("test_stadium")[0]["gate_id"] == "gate_a"
    assert firestore_service.get_recent_reports("test_stadium")[0]["message"] == "Queue building"
    assert firestore_service.get_evacuation_state("test_stadium")["state"] == "ALERT"


def test_firestore_still_fails_closed_in_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")

    def fail_client(*args, **kwargs):
        raise auth_exceptions.DefaultCredentialsError("missing adc")

    monkeypatch.setattr(firestore_service.firestore, "Client", fail_client)

    with pytest.raises(auth_exceptions.DefaultCredentialsError):
        firestore_service.get_all_gates("test_stadium")


def test_bigquery_disables_analytics_when_credentials_are_missing(monkeypatch):
    def fail_client(*args, **kwargs):
        raise auth_exceptions.DefaultCredentialsError("missing adc")

    monkeypatch.setattr(bigquery_service.bigquery, "Client", fail_client)

    bigquery_service.ensure_dataset_and_table()
    bigquery_service.insert_telemetry_row({"stadium_id": "test_stadium"})

    assert bigquery_service.query_gate_history("test_stadium", "gate_a") == []
    assert bigquery_service.query_density_summary("test_stadium") == []


def test_bigquery_still_fails_closed_in_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")

    def fail_client(*args, **kwargs):
        raise auth_exceptions.DefaultCredentialsError("missing adc")

    monkeypatch.setattr(bigquery_service.bigquery, "Client", fail_client)

    with pytest.raises(auth_exceptions.DefaultCredentialsError):
        bigquery_service.ensure_dataset_and_table()
