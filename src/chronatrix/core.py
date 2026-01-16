from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import sun


ALLOWED_AST_NODES: tuple[type[ast.AST], ...] = (
    ast.Expression,
    ast.BoolOp,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Constant,
    ast.Gt,
    ast.GtE,
    ast.Lt,
    ast.LtE,
    ast.Eq,
    ast.NotEq,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
)


@dataclass(frozen=True)
class Place:
    name: str
    country_code: str
    country_name: str
    timezone: str
    latitude: float
    longitude: float


def evaluate_condition(condition: str, context: dict[str, object]) -> bool:
    """
    Évalue une condition logique Python avec un contexte contrôlé.
    """
    try:
        tree = ast.parse(condition, mode="eval")

        for node in ast.walk(tree):
            if not isinstance(node, ALLOWED_AST_NODES):
                raise ValueError("Expression non autorisée")

        return bool(eval(compile(tree, "<condition>", "eval"), {}, context))
    except Exception:
        return False


def season_for(target_date: date, latitude: float) -> str:
    month = target_date.month
    north = latitude >= 0
    if month in (12, 1, 2):
        season = "winter"
    elif month in (3, 4, 5):
        season = "spring"
    elif month in (6, 7, 8):
        season = "summer"
    else:
        season = "autumn"
    if north:
        return season
    return {
        "winter": "summer",
        "spring": "autumn",
        "summer": "winter",
        "autumn": "spring",
    }[season]


def build_context(place: Place) -> dict[str, object]:
    tz = ZoneInfo(place.timezone)
    now = datetime.now(tz)

    loc = LocationInfo(
        name=place.name,
        region=place.country_code,
        timezone=place.timezone,
        latitude=place.latitude,
        longitude=place.longitude,
    )

    solar = sun(loc.observer, date=now.date(), tzinfo=tz)
    sunrise = solar["sunrise"].time()
    sunset = solar["sunset"].time()
    is_daytime = sunrise <= now.time() <= sunset

    return {
        "current_time": now.time(),
        "current_date": now.date(),
        "current_datetime": now,
        "current_hour": now.hour,
        "current_month": now.month,
        "current_year": now.year,
        "current_weekday": now.weekday(),
        "is_weekend": now.weekday() >= 5,
        "location_name": place.name,
        "country_code": place.country_code,
        "country_name": place.country_name,
        "timezone": place.timezone,
        "latitude": place.latitude,
        "longitude": place.longitude,
        "sunrise_time": sunrise,
        "sunset_time": sunset,
        "is_daytime": is_daytime,
        "current_season": season_for(now.date(), place.latitude),
        "current_weather": "unknown",
        "temperature": None,
    }
