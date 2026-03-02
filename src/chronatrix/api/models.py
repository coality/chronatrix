from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PlaceModel(BaseModel):
    tz: str
    lat: float | None
    lon: float | None
    country: str | None


class CacheMeta(BaseModel):
    hit: bool
    age_s: int | None = None


class MetaModel(BaseModel):
    ref_at: datetime
    computed_at: datetime
    place: PlaceModel
    cache: CacheMeta
    schema_version: str


class ContextResponse(BaseModel):
    meta: MetaModel
    time: dict[str, object]
    business: dict[str, object]
    astro: dict[str, object]
    calendar: dict[str, object]
    weather: dict[str, object]
    warnings: list[str]
