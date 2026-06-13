from __future__ import annotations

import os

from fastapi.testclient import TestClient

from chronatrix.api.auth import APIKeyService
from chronatrix.api.cache import MultiLevelCache
from chronatrix.api.main import app
from chronatrix.api.providers.external import ProviderHub


class DummyDB:
    """In-memory stand-in for the MySQL-backed DBClient (no network/DB)."""

    def __init__(self, active: bool = True) -> None:
        self.active = active

    def find_api_key(self, key_hash: bytes):
        status = "active" if self.active else "revoked"
        return {"id": 1, "key_prefix": "ctx_test", "label": "test", "status": status, "rate_limit_rpm": 60}

    def touch_api_key(self, key_id: int) -> None:
        return None

    def get_cache(self, cache_key: str):
        return None

    def set_cache(self, cache_key: str, payload, expires_at):
        return None


def _headers() -> dict[str, str]:
    return {"X-API-Key": "ctx_testing_key"}


def _setup(active: bool = True) -> None:
    """Reset all shared app state so every test runs in isolation."""
    os.environ["CHRONATRIX_KEY_SECRET"] = "secret"
    app.state.api_key_service = APIKeyService(db=DummyDB(active=active))
    app.state.cache = MultiLevelCache(db=DummyDB(active=active))
    app.state.provider_hub = ProviderHub()


def _mock_providers(monkeypatch, *, weather=("clear", 20.0), bank=(True, "bastille_day"), school=(False, None)) -> None:
    hub = app.state.provider_hub

    async def fake_weather(lat, lon, now):
        return {"condition": weather[0], "temperature_c": weather[1]}, None

    async def fake_bank(target_date, country, now):
        return {"is_bank_holiday": bank[0], "name": bank[1]}, None

    async def fake_school(target_date, now, zone="A"):
        return {"is_school_holiday": school[0], "name": school[1]}, None

    monkeypatch.setattr(hub, "weather", fake_weather)
    monkeypatch.setattr(hub, "bank_holiday", fake_bank)
    monkeypatch.setattr(hub, "school_holiday", fake_school)


client = TestClient(app)


def test_context_without_key_returns_401() -> None:
    _setup(active=True)
    response = client.get("/v1/context", params={"tz": "Europe/Paris"})
    assert response.status_code == 401


def test_context_with_revoked_key_returns_401() -> None:
    _setup(active=False)
    response = client.get("/v1/context", params={"tz": "Europe/Paris"}, headers=_headers())
    assert response.status_code == 401


def test_invalid_timezone_returns_422() -> None:
    _setup(active=True)
    response = client.get("/v1/context", params={"tz": "Not/AZone"}, headers=_headers())
    assert response.status_code == 422


def test_full_context_structure(monkeypatch) -> None:
    _setup(active=True)
    _mock_providers(monkeypatch, weather=("clear", 21.5), bank=(True, "bastille_day"), school=(False, None))
    response = client.get(
        "/v1/context",
        params={"tz": "Europe/Paris", "lat": 48.85, "lon": 2.35, "country": "FR", "at": "2024-07-14T10:00:00"},
        headers=_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    for section in ("meta", "time", "business", "astro", "calendar", "weather", "warnings"):
        assert section in body
    assert body["meta"]["schema_version"] == "v1"
    assert body["weather"]["condition"] == "clear"
    assert body["weather"]["temperature_c"] == 21.5
    assert body["calendar"]["is_bank_holiday"] is True
    assert body["calendar"]["current_bank_holiday_name"] == "bastille_day"
    assert body["time"]["current_hour"] == 10
    assert body["warnings"] == []


def test_missing_coordinates_warning(monkeypatch) -> None:
    _setup(active=True)
    _mock_providers(monkeypatch)
    response = client.get("/v1/context", params={"tz": "Europe/Paris", "country": "FR"}, headers=_headers())
    assert response.status_code == 200
    body = response.json()
    assert "missing_coordinates" in body["warnings"]
    assert body["weather"]["condition"] is None


def test_cache_hit_miss(monkeypatch) -> None:
    _setup(active=True)
    _mock_providers(monkeypatch)
    calls = {"count": 0}

    async def fake_weather(lat, lon, now):
        calls["count"] += 1
        return {"condition": "clear", "temperature_c": 20.0}, None

    monkeypatch.setattr(app.state.provider_hub, "weather", fake_weather)
    params = {"tz": "Europe/Paris", "lat": 48.85, "lon": 2.35}
    r1 = client.get("/v1/context", params=params, headers=_headers())
    r2 = client.get("/v1/context", params=params, headers=_headers())
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert calls["count"] == 1  # second call served from cache


def test_provider_down_returns_warning_and_null_fields(monkeypatch) -> None:
    _setup(active=True)
    _mock_providers(monkeypatch)

    async def fake_weather(lat, lon, now):
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


def test_weather_failure_not_cached(monkeypatch) -> None:
    """A transient weather failure must not be cached for the whole TTL."""
    _setup(active=True)
    _mock_providers(monkeypatch)
    calls = {"count": 0}

    async def flaky_weather(lat, lon, now):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"condition": None, "temperature_c": None}, "weather_unavailable"
        return {"condition": "clear", "temperature_c": 19.0}, None

    monkeypatch.setattr(app.state.provider_hub, "weather", flaky_weather)
    params = {"tz": "Europe/Paris", "lat": 48.85, "lon": 2.35}
    r1 = client.get("/v1/context", params=params, headers=_headers())
    r2 = client.get("/v1/context", params=params, headers=_headers())
    assert r1.json()["weather"]["condition"] is None
    assert r2.json()["weather"]["condition"] == "clear"
    assert calls["count"] == 2  # failure was not cached, so it retried
