from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_app_state(monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"X-API-Key": "test-admin-key"}
