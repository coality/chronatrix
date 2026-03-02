from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from chronatrix import core


@dataclass
class CircuitBreaker:
    failures: int = 0
    open_until: datetime | None = None

    def allows(self, now: datetime) -> bool:
        return self.open_until is None or now >= self.open_until

    def on_failure(self, now: datetime) -> None:
        self.failures += 1
        if self.failures >= 2:
            self.open_until = now + timedelta(seconds=30)

    def on_success(self) -> None:
        self.failures = 0
        self.open_until = None


class ProviderHub:
    def __init__(self) -> None:
        self.breakers = {
            "weather": CircuitBreaker(),
            "holidays": CircuitBreaker(),
            "school": CircuitBreaker(),
        }

    async def weather(self, lat: float, lon: float, now: datetime) -> tuple[dict[str, object], str | None]:
        breaker = self.breakers["weather"]
        if not breaker.allows(now):
            return {"condition": None, "temperature_c": None}, "weather_unavailable"
        try:
            label, temp = await asyncio.to_thread(core.fetch_weather, lat, lon, False)
            breaker.on_success()
            return {"condition": label, "temperature_c": temp}, None
        except Exception:
            breaker.on_failure(now)
            return {"condition": None, "temperature_c": None}, "weather_unavailable"

    async def bank_holiday(self, target_date: date, country: str | None, now: datetime) -> tuple[dict[str, object], str | None]:
        if not country:
            return {"is_bank_holiday": None, "name": None}, None
        breaker = self.breakers["holidays"]
        if not breaker.allows(now):
            return {"is_bank_holiday": None, "name": None}, "holidays_unavailable"
        try:
            name = await asyncio.to_thread(core.bank_holiday_for, target_date, country, False)
            breaker.on_success()
            return {"is_bank_holiday": name is not None, "name": name}, None
        except Exception:
            breaker.on_failure(now)
            return {"is_bank_holiday": None, "name": None}, "holidays_unavailable"

    async def school_holiday(self, target_date: date, now: datetime) -> tuple[dict[str, object], str | None]:
        breaker = self.breakers["school"]
        if not breaker.allows(now):
            return {"is_school_holiday": None, "name": None}, "school_holidays_unavailable"
        try:
            is_holiday, name = await asyncio.to_thread(core.school_holiday_status, target_date, "A")
            breaker.on_success()
            return {"is_school_holiday": is_holiday, "name": name}, None
        except Exception:
            breaker.on_failure(now)
            return {"is_school_holiday": None, "name": None}, "school_holidays_unavailable"
