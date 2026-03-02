from __future__ import annotations

import os

from fastapi.testclient import TestClient

from chronatrix.api.auth import APIKeyService
from chronatrix.api.main import app


class DummyDB:
    def __init__(self, active: bool = True) -> None:
        self.active = active

    def find_api_key(self, key_hash: bytes):
        if not self.active:
            return {"id": 1, "key_prefix": "ctx_test", "label": "test", "status": "revoked", "rate_limit_rpm": 60}
        return {"id": 1, "key_prefix": "ctx_test", "label": "test", "status": "active", "rate_limit_rpm": 60}

    def touch_api_key(self, key_id: int) -> None:
        return None

    def get_cache(self, cache_key: str):
        return None

    def set_cache(self, cache_key: str, payload, expires_at):
        return None


def _headers() -> dict[str, str]:
    key = "ctx_testing_key"
    return {"X-API-Key": key}


def _setup(active: bool = True) -> None:
    os.environ["CHRONATRIX_KEY_SECRET"] = "secret"
    app.state.api_key_service = APIKeyService(db=DummyDB(active=active))


client = TestClient(app)


def test_context_without_key_returns_401() -> None:
    _setup(active=True)
    response = client.get("/v1/context", params={"tz": "Europe/Paris"})
    assert response.status_code == 401


def test_context_with_revoked_key_returns_401() -> None:
    _setup(active=False)
    response = client.get("/v1/context", params={"tz": "Europe/Paris"}, headers=_headers())
    assert response.status_code == 401


def test_cache_hit_miss(monkeypatch) -> None:
    _setup(active=True)
    calls = {"count": 0}

    async def fake_weather(lat: float, lon: float, now):
        calls["count"] += 1
        return {"condition": "clear", "temperature_c": 20.0}, None

    monkeypatch.setattr(app.state.provider_hub, "weather", fake_weather)
    r1 = client.get(
        "/v1/context",
        params={"tz": "Europe/Paris", "lat": 48.85, "lon": 2.35},
        headers=_headers(),
    )
    r2 = client.get(
        "/v1/context",
        params={"tz": "Europe/Paris", "lat": 48.85, "lon": 2.35},
        headers=_headers(),
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert calls["count"] == 1


def test_provider_down_returns_warning_and_null_fields(monkeypatch) -> None:
    _setup(active=True)

    async def fake_weather(lat: float, lon: float, now):
        return {"condition": None, "temperature_c": None}, "weather_unavailable"

    monkeypatch.setattr(app.state.provider_hub, "weather", fake_weather)
    response = client.get(
        "/v1/context",
        params={"tz": "Europe/Paris", "lat": 48.85, "lon": 2.35},
        headers=_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert "weather_unavailable" in payload["warnings"]
    assert payload["weather"]["condition"] is None
