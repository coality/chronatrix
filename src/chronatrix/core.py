from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import sun


ALLOWED_AST_NODES: tuple[type[ast.AST], ...] = (
    ast.Expression,
    ast.BoolOp,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Call,
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

ALLOWED_CALLS: set[str] = {"market_quotation"}


WEATHER_CODE_LABELS: dict[int, str] = {
    0: "clear",
    1: "mainly_clear",
    2: "partly_cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing_rime_fog",
    51: "light_drizzle",
    53: "moderate_drizzle",
    55: "dense_drizzle",
    56: "light_freezing_drizzle",
    57: "dense_freezing_drizzle",
    61: "light_rain",
    63: "moderate_rain",
    65: "heavy_rain",
    66: "light_freezing_rain",
    67: "heavy_freezing_rain",
    71: "light_snow",
    73: "moderate_snow",
    75: "heavy_snow",
    77: "snow_grains",
    80: "light_rain_showers",
    81: "moderate_rain_showers",
    82: "violent_rain_showers",
    85: "light_snow_showers",
    86: "heavy_snow_showers",
    95: "thunderstorm",
    96: "thunderstorm_with_light_hail",
    99: "thunderstorm_with_heavy_hail",
}

LANGUAGE_OPTIONS: set[str] = {"en", "fr"}

SEASON_TRANSLATIONS: dict[str, dict[str, str]] = {
    "fr": {
        "winter": "hiver",
        "spring": "printemps",
        "summer": "été",
        "autumn": "automne",
    },
    "en": {},
}

WEATHER_TRANSLATIONS: dict[str, dict[str, str]] = {
    "fr": {
        "clear": "ciel_dégagé",
        "mainly_clear": "principalement_dégagé",
        "partly_cloudy": "partiellement_nuageux",
        "overcast": "couvert",
        "fog": "brouillard",
        "depositing_rime_fog": "brouillard_givrant",
        "light_drizzle": "bruine_faible",
        "moderate_drizzle": "bruine_modérée",
        "dense_drizzle": "bruine_dense",
        "light_freezing_drizzle": "bruine_givrante_faible",
        "dense_freezing_drizzle": "bruine_givrante_dense",
        "light_rain": "pluie_faible",
        "moderate_rain": "pluie_modérée",
        "heavy_rain": "forte_pluie",
        "light_freezing_rain": "pluie_givrante_faible",
        "heavy_freezing_rain": "forte_pluie_givrante",
        "light_snow": "neige_faible",
        "moderate_snow": "neige_modérée",
        "heavy_snow": "forte_neige",
        "snow_grains": "grains_de_neige",
        "light_rain_showers": "averses_faibles",
        "moderate_rain_showers": "averses_modérées",
        "violent_rain_showers": "averses_violentes",
        "light_snow_showers": "averses_de_neige_faibles",
        "heavy_snow_showers": "averses_de_neige_fortes",
        "thunderstorm": "orage",
        "thunderstorm_with_light_hail": "orage_avec_grêle_faible",
        "thunderstorm_with_heavy_hail": "orage_avec_forte_grêle",
        "unknown": "inconnu",
    },
    "en": {},
}

MARKET_DATA_API_URL = "https://api.twelvedata.com/quote"


def _translate_value(value: str, translations: dict[str, dict[str, str]], language: str) -> str:
    if language == "en":
        return value
    return translations.get(language, {}).get(value, value)


def localize_context(context: dict[str, object], language: str) -> dict[str, object]:
    if language not in LANGUAGE_OPTIONS:
        raise ValueError(f"Unsupported language: {language}")

    localized = dict(context)
    season = context.get("current_season")
    if isinstance(season, str):
        localized["current_season"] = _translate_value(season, SEASON_TRANSLATIONS, language)
    weather = context.get("current_weather")
    if isinstance(weather, str):
        localized["current_weather"] = _translate_value(weather, WEATHER_TRANSLATIONS, language)
    return localized


@dataclass(frozen=True)
class Place:
    """Represents a geographic location used to build the evaluation context."""
    name: str
    country_code: str
    country_name: str
    timezone: str
    latitude: float
    longitude: float


def evaluate_condition(condition: str, context: dict[str, object]) -> bool:
    """Evaluate a Python boolean expression against a constrained context."""
    try:
        tree = ast.parse(condition, mode="eval")

        for node in ast.walk(tree):
            if not isinstance(node, ALLOWED_AST_NODES):
                raise ValueError("Expression not allowed")
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    raise ValueError("Expression not allowed")
                if node.func.id not in ALLOWED_CALLS:
                    raise ValueError("Expression not allowed")
                if node.keywords:
                    raise ValueError("Expression not allowed")
                if (
                    len(node.args) != 1
                    or not isinstance(node.args[0], ast.Constant)
                    or not isinstance(node.args[0].value, str)
                ):
                    raise ValueError("Expression not allowed")

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


def fetch_weather(latitude: float, longitude: float) -> tuple[str | None, float | None]:
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}&current_weather=true"
    )
    try:
        with urlopen(url, timeout=10) as response:
            payload = json.load(response)
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None, None

    current = payload.get("current_weather")
    if not isinstance(current, dict):
        return None, None

    weather_code = current.get("weathercode")
    temperature = current.get("temperature")
    label = None
    if isinstance(weather_code, int):
        label = WEATHER_CODE_LABELS.get(weather_code, "unknown")
    temp_value = temperature if isinstance(temperature, (int, float)) else None
    return label, temp_value


def fetch_market_quotation(isin: str) -> float | None:
    if not isin:
        return None
    api_key = os.getenv("TWELVEDATA_API_KEY")
    if not api_key:
        return None
    query = urlencode({"isin": isin, "apikey": api_key})
    url = f"{MARKET_DATA_API_URL}?{query}"
    try:
        with urlopen(url, timeout=10) as response:
            payload = json.load(response)
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("status") == "error":
        return None
    price = payload.get("price")
    if isinstance(price, (int, float)):
        return float(price)
    if isinstance(price, str):
        try:
            return float(price)
        except ValueError:
            return None
    return None


def build_context(
    place: Place,
    language: str = "en",
    custom_context: dict[str, object] | None = None,
) -> dict[str, object]:
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

    current_weather, temperature = fetch_weather(place.latitude, place.longitude)
    def market_quotation(isin: str) -> float | None:
        return fetch_market_quotation(isin)

    context = {
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
        "current_weather": current_weather or "unknown",
        "temperature": temperature,
        "market_quotation": market_quotation,
    }
    if custom_context:
        context |= custom_context
    return localize_context(context, language)
