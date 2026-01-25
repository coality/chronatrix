from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import chronatrix.core as core


PLACE = core.Place(
    name="Paris",
    country_code="FR",
    country_name="France",
    timezone="Europe/Paris",
    latitude=48.8566,
    longitude=2.3522,
)


def _freeze_weather(monkeypatch: object) -> None:
    def _fake_weather(latitude: float, longitude: float, debug: bool = False) -> tuple[str, float]:
        return "clear", 20.0

    monkeypatch.setattr(core, "fetch_weather", _fake_weather)


def _freeze_bank_holidays(monkeypatch: object, holiday_date: date, name: str) -> None:
    def _fake_holidays(year: int, country_code: str, debug: bool = False) -> list[core.BankHoliday]:
        return [core.BankHoliday(name=name, date=holiday_date)]

    monkeypatch.setattr(core, "fetch_bank_holidays", _fake_holidays)


def _freeze_school_holidays(monkeypatch: object, expected_zone: str, name: str) -> None:
    def _fake_school_status(target_date: date, zone: str | None) -> tuple[bool, str | None]:
        assert zone == expected_zone
        return True, name

    monkeypatch.setattr(core, "school_holiday_status", _fake_school_status)


def test_build_context_weekday_morning(monkeypatch: object) -> None:
    _freeze_weather(monkeypatch)
    _freeze_bank_holidays(monkeypatch, date(2024, 6, 3), "Test Holiday")
    _freeze_school_holidays(monkeypatch, "A", "Summer Break")

    reference_datetime = datetime(2024, 6, 3, 10, 30, tzinfo=ZoneInfo("Europe/Paris"))
    context = core.build_context(
        PLACE,
        custom_context={"holiday_zone": "A"},
        reference_datetime=reference_datetime,
    )

    assert context["is_weekend"] is False
    assert context["is_workday"] is True
    assert context["is_business_hours"] is True
    assert context["is_lunch_time"] is False
    assert context["is_morning"] is True
    assert context["is_afternoon"] is False
    assert context["is_evening"] is False
    assert context["is_night"] is False
    assert context["is_leap_year"] is True
    assert context["is_last_week_of_month"] is False
    assert context["is_bank_holiday"] is True
    assert context["current_bank_holiday_name"] == "test_holiday"
    assert context["is_school_holiday"] is True
    assert context["current_school_holiday_name"] == "summer_break"


def test_build_context_lunch_time(monkeypatch: object) -> None:
    _freeze_weather(monkeypatch)
    _freeze_bank_holidays(monkeypatch, date(2024, 6, 3), "Lunch Holiday")
    _freeze_school_holidays(monkeypatch, "B", "Midday Break")

    reference_datetime = datetime(2024, 6, 3, 12, 30, tzinfo=ZoneInfo("Europe/Paris"))
    context = core.build_context(
        PLACE,
        custom_context={"holiday_zone": "B"},
        reference_datetime=reference_datetime,
    )

    assert context["is_morning"] is False
    assert context["is_afternoon"] is True
    assert context["is_lunch_time"] is True
    assert context["is_business_hours"] is True


def test_build_context_evening_weekend(monkeypatch: object) -> None:
    _freeze_weather(monkeypatch)
    _freeze_bank_holidays(monkeypatch, date(2024, 6, 8), "Weekend Holiday")
    _freeze_school_holidays(monkeypatch, "C", "Weekend Break")

    reference_datetime = datetime(2024, 6, 8, 20, 30, tzinfo=ZoneInfo("Europe/Paris"))
    context = core.build_context(
        PLACE,
        custom_context={"holiday_zone": "C"},
        reference_datetime=reference_datetime,
    )

    assert context["is_weekend"] is True
    assert context["is_workday"] is False
    assert context["is_evening"] is True
    assert context["is_night"] is False


def test_build_context_night(monkeypatch: object) -> None:
    _freeze_weather(monkeypatch)
    _freeze_bank_holidays(monkeypatch, date(2024, 12, 15), "Night Holiday")
    _freeze_school_holidays(monkeypatch, "A", "Night Break")

    reference_datetime = datetime(2024, 12, 15, 23, 30, tzinfo=ZoneInfo("Europe/Paris"))
    context = core.build_context(
        PLACE,
        custom_context={"holiday_zone": "A"},
        reference_datetime=reference_datetime,
    )

    assert context["is_evening"] is False
    assert context["is_night"] is True
