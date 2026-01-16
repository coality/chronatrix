from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, date
from zoneinfo import ZoneInfo

# pip install astral
from astral import LocationInfo
from astral.sun import sun


def evaluate_condition(condition: str, context: dict) -> bool:
    """
    Évalue une condition logique Python avec un contexte contrôlé.
    """
    try:
        tree = ast.parse(condition, mode="eval")

        for node in ast.walk(tree):
            if not isinstance(node, (
                ast.Expression, ast.BoolOp, ast.Compare,
                ast.Name, ast.Load, ast.And, ast.Or,
                ast.UnaryOp, ast.Not,
                ast.Constant, ast.Gt, ast.GtE, ast.Lt, ast.LtE,
                ast.Eq, ast.NotEq,
                # arithmétique simple (optionnel)
                ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
            )):
                raise ValueError("Expression non autorisée")

        return bool(eval(compile(tree, "<condition>", "eval"), {}, context))
    except Exception:
        return False


@dataclass(frozen=True)
class Place:
    name: str
    country_code: str
    country_name: str
    timezone: str
    latitude: float
    longitude: float


def season_for(d: date, latitude: float) -> str:
    m = d.month
    north = latitude >= 0
    if m in (12, 1, 2):
        s = "winter"
    elif m in (3, 4, 5):
        s = "spring"
    elif m in (6, 7, 8):
        s = "summer"
    else:
        s = "autumn"
    if north:
        return s
    return {"winter": "summer", "spring": "autumn", "summer": "winter", "autumn": "spring"}[s]


def build_context(place: Place) -> dict:
    tz = ZoneInfo(place.timezone)
    now = datetime.now(tz)  # <-- calculé selon le lieu

    loc = LocationInfo(
        name=place.name,
        region=place.country_code,
        timezone=place.timezone,
        latitude=place.latitude,
        longitude=place.longitude,
    )

    s = sun(loc.observer, date=now.date(), tzinfo=tz)
    sunrise = s["sunrise"].time()
    sunset = s["sunset"].time()
    is_daytime = sunrise <= now.time() <= sunset

    return {
        # Temps (selon le lieu)
        "current_time": now.time(),
        "current_date": now.date(),
        "current_datetime": now,
        "current_hour": now.hour,
        "current_month": now.month,
        "current_year": now.year,
        "current_weekday": now.weekday(),
        "is_weekend": now.weekday() >= 5,

        # Lieu
        "location_name": place.name,
        "country_code": place.country_code,
        "country_name": place.country_name,
        "timezone": place.timezone,
        "latitude": place.latitude,
        "longitude": place.longitude,

        # Environnement (selon lieu)
        "sunrise_time": sunrise,
        "sunset_time": sunset,
        "is_daytime": is_daytime,
        "current_season": season_for(now.date(), place.latitude),

        # Météo (placeholder, branche une API si besoin)
        "current_weather": "unknown",
        "temperature": None,
    }


# ----- Exemple Paris -----
paris = Place(
    name="Paris",
    country_code="FR",
    country_name="France",
    timezone="Europe/Paris",
    latitude=48.8566,
    longitude=2.3522,
)

context = build_context(paris)

condition = "(current_hour >= 18 and is_weekend) or (temperature is not None and temperature < 5)"
result = evaluate_condition(condition, context)
print(result)
