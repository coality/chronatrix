from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from chronatrix.core import Place, build_context

from .auth import APIKeyPrincipal, APIKeyService, require_api_key
from .cache import MultiLevelCache
from .models import ContextResponse
from .providers.external import ProviderHub

LOGGER = logging.getLogger("chronatrix.api")

app = FastAPI(title="Chronatrix API", version="1.0.0")
app.state.cache = MultiLevelCache()
app.state.provider_hub = ProviderHub()
app.state.api_key_service = APIKeyService(default_rpm=60)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    LOGGER.exception("unhandled_error", extra={"path": request.url.path})
    return JSONResponse(status_code=500, content={"detail": "internal_error"})


def _parse_reference_at(value: str | None, tz: str) -> datetime:
    zone = ZoneInfo(tz)
    if value is None:
        return datetime.now(zone)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid_at") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=zone)
    return parsed.astimezone(zone)


def _flat_to_nested(flat: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        "time": {
            "current_datetime": str(flat.get("current_datetime")),
            "current_date": str(flat.get("current_date")),
            "current_time": str(flat.get("current_time")),
            "timezone": flat.get("timezone"),
            "current_hour": flat.get("current_hour"),
            "current_weekday": flat.get("current_weekday"),
            "week_day_name": flat.get("week_day_name"),
            "is_weekend": flat.get("is_weekend"),
            "is_morning": flat.get("is_morning"),
            "is_afternoon": flat.get("is_afternoon"),
            "is_evening": flat.get("is_evening"),
            "is_night": flat.get("is_night"),
        },
        "business": {
            "is_workday": flat.get("is_workday"),
            "is_business_hours": flat.get("is_business_hours"),
            "is_lunch_time": flat.get("is_lunch_time"),
        },
        "astro": {
            "sunrise_time": str(flat.get("sunrise_time")),
            "sunset_time": str(flat.get("sunset_time")),
            "is_daytime": flat.get("is_daytime"),
            "current_season": flat.get("current_season"),
        },
        "calendar": {
            "is_bank_holiday": flat.get("is_bank_holiday"),
            "current_bank_holiday_name": flat.get("current_bank_holiday_name"),
            "is_school_holiday": flat.get("is_school_holiday"),
            "current_school_holiday_name": flat.get("current_school_holiday_name"),
            "current_month": flat.get("current_month"),
            "current_month_name": flat.get("current_month_name"),
            "current_quarter": flat.get("current_quarter"),
            "days_until_end_of_month": flat.get("days_until_end_of_month"),
            "days_until_end_of_year": flat.get("days_until_end_of_year"),
        },
        "weather": {
            "condition": flat.get("current_weather"),
            "temperature_c": flat.get("temperature"),
        },
    }


@app.get("/v1/context", response_model=ContextResponse)
async def get_context(
    tz: str = Query(...),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    country: str | None = Query(default=None, min_length=2, max_length=2),
    at: str | None = Query(default=None),
    _principal: APIKeyPrincipal = Depends(require_api_key),
) -> dict[str, object]:
    try:
        ZoneInfo(tz)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid_tz") from exc

    ref_at = _parse_reference_at(at, tz)
    warnings: list[str] = []
    place = Place(
        name="api_place",
        country_code=(country or "XX").upper(),
        country_name=(country or "unknown").upper(),
        timezone=tz,
        latitude=lat if lat is not None else 0.0,
        longitude=lon if lon is not None else 0.0,
    )

    flat = build_context(place=place, reference_datetime=ref_at)

    hub: ProviderHub = app.state.provider_hub
    cache: MultiLevelCache = app.state.cache

    weather = {"condition": None, "temperature_c": None}
    cache_hit = False
    cache_age = None

    if lat is None or lon is None:
        warnings.append("missing_coordinates")
        flat["current_weather"] = None
        flat["temperature"] = None
    else:
        key = f"weather:{round(lat, 2):.2f}:{round(lon, 2):.2f}:{ref_at.strftime('%Y-%m-%dT%H:%M')}"

        async def fetch_weather() -> dict[str, object]:
            payload, warning = await hub.weather(lat, lon, datetime.utcnow())
            if warning:
                warnings.append(warning)
            return payload

        weather, cache_hit, cache_age = await cache.get_or_set(key, 600, fetch_weather)
        flat["current_weather"] = weather.get("condition")
        flat["temperature"] = weather.get("temperature_c")

    h_key = f"holidays:{(country or 'xx').lower()}:{ref_at.date().isoformat()}"

    async def fetch_holidays() -> dict[str, object]:
        payload, warning = await hub.bank_holiday(ref_at.date(), country, datetime.utcnow())
        if warning:
            warnings.append(warning)
        return payload

    holi, _, _ = await cache.get_or_set(h_key, 86400 * 7, fetch_holidays)
    flat["is_bank_holiday"] = holi["is_bank_holiday"]
    flat["current_bank_holiday_name"] = holi["name"]

    s_key = f"school:fr:{ref_at.date().isoformat()}"

    async def fetch_school() -> dict[str, object]:
        payload, warning = await hub.school_holiday(ref_at.date(), datetime.utcnow())
        if warning:
            warnings.append(warning)
        return payload

    school, _, _ = await cache.get_or_set(s_key, 86400 * 180, fetch_school)
    flat["is_school_holiday"] = school["is_school_holiday"]
    flat["current_school_holiday_name"] = school["name"]

    nested = _flat_to_nested(flat)
    computed_at = datetime.utcnow()
    return {
        "meta": {
            "ref_at": ref_at,
            "computed_at": computed_at,
            "place": {"tz": tz, "lat": lat, "lon": lon, "country": country},
            "cache": {"hit": cache_hit, "age_s": cache_age},
            "schema_version": "v1",
        },
        **nested,
        "warnings": sorted(set(warnings)),
    }
