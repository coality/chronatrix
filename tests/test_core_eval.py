from __future__ import annotations

import io
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

import chronatrix.core as core


PLACE = core.Place(
    name="Paris",
    country_code="FR",
    country_name="France",
    timezone="Europe/Paris",
    latitude=48.8566,
    longitude=2.3522,
)


# --------------------------------------------------------------------------- #
# evaluate_condition
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "condition, context, expected",
    [
        ("is_weekend", {"is_weekend": True}, True),
        ("not is_weekend", {"is_weekend": True}, False),
        ("current_hour >= 9 and current_hour < 17", {"current_hour": 10}, True),
        ("current_hour == 9 or is_weekend", {"current_hour": 8, "is_weekend": True}, True),
        ("current_season == 'summer'", {"current_season": "summer"}, True),
        ("(current_hour + 1) >= 18", {"current_hour": 17}, True),
        ("current_month % 2 == 0", {"current_month": 6}, True),
        ("-days_until_end_of_month <= 0", {"days_until_end_of_month": 3}, True),
    ],
)
def test_evaluate_basic(condition, context, expected) -> None:
    assert core.evaluate_condition(condition, context) is expected


@pytest.mark.parametrize(
    "condition, value, expected",
    [
        ("temperature is None", None, True),
        ("temperature is None", 20.0, False),
        ("temperature is not None", 20.0, True),
        ("temperature is not None", None, False),
        ("temperature is not None and temperature >= 20", 25.0, True),
        ("temperature is not None and temperature >= 20", None, False),
        ("temperature is not None and temperature >= 20", 5.0, False),
    ],
)
def test_evaluate_none_checks(condition, value, expected) -> None:
    # Regression: `is` / `is not` were missing from the AST allow-list, so every
    # documented None-check silently returned False.
    assert core.evaluate_condition(condition, {"temperature": value}) is expected


@pytest.mark.parametrize(
    "condition",
    [
        "current_weather in ['clear', 'partly_cloudy']",  # `in` not allowed
        "len(current_weather) > 0",                       # function calls not allowed
        "current_weather.startswith('clear')",            # attribute access not allowed
        "a if is_daytime else b",                         # conditional expr not allowed
        '{"x": 1}',                                       # dict literal not allowed
        "abs(current_hour) > 0",                          # builtins not callable
        "__import__('os')",                               # no builtins access
        "unknown_variable > 5",                           # undefined name -> error -> False
        "1/0 == 0",                                       # runtime error -> False
    ],
)
def test_evaluate_unsupported_returns_false(condition) -> None:
    ctx = {"current_weather": "clear", "current_hour": 10, "is_daytime": True}
    assert core.evaluate_condition(condition, ctx) is False


# --------------------------------------------------------------------------- #
# season_for
# --------------------------------------------------------------------------- #

def test_season_northern_hemisphere() -> None:
    assert core.season_for(date(2024, 6, 21), 48.0) == "summer"
    assert core.season_for(date(2024, 1, 15), 48.0) == "winter"


def test_season_southern_hemisphere_inverted() -> None:
    assert core.season_for(date(2024, 6, 21), -33.0) == "winter"
    assert core.season_for(date(2024, 12, 21), -33.0) == "summer"


# --------------------------------------------------------------------------- #
# _normalize_text
# --------------------------------------------------------------------------- #

def test_normalize_text_strips_accents_and_specials() -> None:
    assert core._normalize_text("Été 2024 !") == "ete_2024__"
    assert core._normalize_text("Bastille Day") == "bastille_day"


# --------------------------------------------------------------------------- #
# fetch_weather (parsing, with urlopen mocked)
# --------------------------------------------------------------------------- #

class _FakeResponse(io.BytesIO):
    status = 200
    headers: dict = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_urlopen_factory(payload):
    def _fake(url, timeout=10):
        return _FakeResponse(json.dumps(payload).encode("utf-8"))
    return _fake


def test_fetch_weather_maps_code(monkeypatch) -> None:
    monkeypatch.setattr(core, "urlopen", _fake_urlopen_factory({"current_weather": {"weathercode": 61, "temperature": 12.3}}))
    label, temp = core.fetch_weather(48.85, 2.35)
    assert label == "light_rain"
    assert temp == 12.3


def test_fetch_weather_unknown_code(monkeypatch) -> None:
    monkeypatch.setattr(core, "urlopen", _fake_urlopen_factory({"current_weather": {"weathercode": 12345, "temperature": 1}}))
    label, _ = core.fetch_weather(48.85, 2.35)
    assert label == "unknown"


def test_fetch_weather_missing_block(monkeypatch) -> None:
    monkeypatch.setattr(core, "urlopen", _fake_urlopen_factory({"foo": "bar"}))
    assert core.fetch_weather(48.85, 2.35) == (None, None)


# --------------------------------------------------------------------------- #
# build_context (fetch_external + polar)
# --------------------------------------------------------------------------- #

def test_build_context_no_external_skips_network(monkeypatch) -> None:
    def _boom(*args, **kwargs):
        raise AssertionError("network must not be called when fetch_external=False")

    monkeypatch.setattr(core, "fetch_weather", _boom)
    monkeypatch.setattr(core, "fetch_bank_holidays", _boom)
    monkeypatch.setattr(core, "school_holiday_status", _boom)

    ctx = core.build_context(
        PLACE,
        reference_datetime=datetime(2024, 6, 3, 10, 30, tzinfo=ZoneInfo("Europe/Paris")),
        fetch_external=False,
    )
    assert ctx["temperature"] is None
    assert ctx["is_bank_holiday"] is False
    assert ctx["current_bank_holiday_name"] is None
    assert ctx["is_school_holiday"] is False
    assert ctx["current_weekday"] == 0  # 2024-06-03 is a Monday


def test_build_context_polar_no_crash(monkeypatch) -> None:
    def _no_sun(*args, **kwargs):
        raise ValueError("Sun never sets / rises at this location")

    monkeypatch.setattr(core, "sun", _no_sun)
    ctx = core.build_context(
        core.Place(
            name="Svalbard",
            country_code="NO",
            country_name="Norway",
            timezone="Arctic/Longyearbyen",
            latitude=78.0,
            longitude=15.0,
        ),
        reference_datetime=datetime(2024, 6, 21, 12, 0, tzinfo=ZoneInfo("Arctic/Longyearbyen")),
        fetch_external=False,
    )
    assert ctx["sunrise_time"] is None
    assert ctx["sunset_time"] is None
    assert ctx["is_daytime"] is None
