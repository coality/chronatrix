from __future__ import annotations

import ast
import calendar
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from urllib.error import URLError
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import sun
from vacances_scolaires_france import SchoolHolidayDates

LOGGER = logging.getLogger(__name__)

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
    ast.UAdd,
    ast.USub,
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

ALLOWED_CALLS: set[str] = set()


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

@dataclass(frozen=True)
class Place:
    """Represents a geographic location used to build the evaluation context."""
    name: str
    country_code: str
    country_name: str
    timezone: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class BankHoliday:
    name: str
    date: date


def _parse_api_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def fetch_bank_holidays(
    year: int,
    country_code: str,
    debug: bool = False,
) -> list[BankHoliday] | None:
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"
    try:
        if debug:
            LOGGER.debug("Requesting bank holidays: %s", url)
        with urlopen(url, timeout=10) as response:
            payload = json.load(response)
            if debug:
                LOGGER.debug(
                    "Bank holidays response: status=%s headers=%s payload=%s",
                    getattr(response, "status", "unknown"),
                    dict(response.headers),
                    payload,
                )
    except (URLError, TimeoutError, json.JSONDecodeError):
        if debug:
            LOGGER.exception("Failed to fetch bank holidays from %s", url)
        return None
    if not isinstance(payload, list):
        return None
    holidays: list[BankHoliday] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        name = entry.get("localName") or entry.get("name")
        if not isinstance(name, str):
            continue
        name = _normalize_text(name)
        holiday_date = _parse_api_date(entry.get("date"))
        if holiday_date is None:
            continue
        holidays.append(BankHoliday(name=name, date=holiday_date))
    return holidays


def bank_holiday_for(
    target_date: date,
    country_code: str | None,
    debug: bool = False,
) -> str | None:
    if country_code is None:
        return None
    holidays = fetch_bank_holidays(
        target_date.year,
        country_code.upper(),
        debug=debug,
    )
    if not holidays:
        return None
    for holiday in holidays:
        if holiday.date == target_date:
            return holiday.name
    return None


def school_holiday_status(
    target_date: date,
    zone: str | None,
) -> tuple[bool, str | None]:
    if not isinstance(zone, str):
        return False, None
    zone = zone.upper()
    if zone not in {"A", "B", "C"}:
        return False, None
    holidays = SchoolHolidayDates()
    is_holiday = _call_school_holiday_method(
        holidays,
        ("is_holiday", "isHoliday"),
        target_date,
        zone,
    )
    holiday = _call_school_holiday_method(
        holidays,
        ("get_holiday", "get_holiday_name", "getHoliday", "getHolidayName"),
        target_date,
        zone,
    )
    holiday_name = _extract_school_holiday_name(holiday)
    if is_holiday is None:
        is_holiday = holiday_name is not None
    return bool(is_holiday), holiday_name


def _call_school_holiday_method(
    holidays: SchoolHolidayDates,
    method_names: tuple[str, ...],
    target_date: date,
    zone: str,
) -> object | None:
    for name in method_names:
        method = getattr(holidays, name, None)
        if method is None:
            continue
        try:
            return method(target_date, zone)
        except TypeError:
            try:
                return method(zone, target_date)
            except TypeError:
                continue
    return None


def _extract_school_holiday_name(value: object) -> str | None:
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        for key in ("name", "label", "holiday"):
            if isinstance(value.get(key), str):
                return value[key] or None
    if isinstance(value, (list, tuple)):
        for item in value:
            name = _extract_school_holiday_name(item)
            if name:
                return name
    name_attr = getattr(value, "name", None)
    if isinstance(name_attr, str):
        return name_attr or None
    return None


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


def fetch_weather(
    latitude: float,
    longitude: float,
    debug: bool = False,
) -> tuple[str | None, float | None]:
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}&current_weather=true"
    )
    try:
        if debug:
            LOGGER.debug("Requesting weather: %s", url)
        with urlopen(url, timeout=10) as response:
            payload = json.load(response)
            if debug:
                LOGGER.debug(
                    "Weather response: status=%s headers=%s payload=%s",
                    getattr(response, "status", "unknown"),
                    dict(response.headers),
                    payload,
                )
    except (URLError, TimeoutError, json.JSONDecodeError):
        if debug:
            LOGGER.exception("Failed to fetch weather from %s", url)
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


def build_context(
    place: Place,
    custom_context: dict[str, object] | None = None,
    reference_datetime: datetime | None = None,
    debug: bool = False,
) -> dict[str, object]:
    tz = ZoneInfo(place.timezone)
    if reference_datetime is None:
        now = datetime.now(tz)
    elif reference_datetime.tzinfo is None:
        now = reference_datetime.replace(tzinfo=tz)
    else:
        now = reference_datetime.astimezone(tz)

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

    current_weather, temperature = fetch_weather(
        place.latitude,
        place.longitude,
        debug=debug,
    )
    current_date = now.date()
    last_day_of_month = date(
        now.year,
        now.month,
        calendar.monthrange(now.year, now.month)[1],
    )
    days_until_end_of_month = (last_day_of_month - current_date).days
    days_until_end_of_year = (date(now.year + 1, 1, 1) - current_date).days
    current_quarter = f"Q{((now.month - 1) // 3) + 1}"
    current_month_name = now.strftime("%B")
    week_day_name = now.strftime("%A")
    is_leap_year = calendar.isleap(now.year)
    is_last_week_of_month = (current_date + timedelta(days=7)).month != now.month
    is_morning = 5 <= now.hour < 12
    is_afternoon = 12 <= now.hour < 17
    is_evening = 17 <= now.hour <= 22
    is_night = now.hour >= 23 or now.hour < 5
    is_workday = now.weekday() < 5
    is_business_hours = is_workday and 9 <= now.hour < 17
    is_lunch_time = is_workday and 12 <= now.hour < 14
    holiday_zone = None
    if custom_context:
        holiday_zone = custom_context.get("holiday_zone")
    bank_holiday_name = None
    if place.country_code.upper() == "FR":
        holidays = fetch_bank_holidays(
            current_date.year,
            place.country_code.upper(),
            debug=debug,
        )
        if holidays:
            for holiday in holidays:
                if holiday.date == current_date:
                    bank_holiday_name = holiday.name
                    break
    is_bank_holiday = bank_holiday_name is not None
    is_school_holiday, current_school_holiday_name = school_holiday_status(
        current_date,
        holiday_zone,
    )
    context = {
        "current_time": now.time(),
        "current_date": current_date,
        "current_datetime": now,
        "current_hour": now.hour,
        "current_month": now.month,
        "current_quarter": current_quarter,
        "current_month_name": current_month_name,
        "current_year": now.year,
        "current_weekday": now.weekday(),
        "week_day_name": week_day_name,
        "is_weekend": now.weekday() >= 5,
        "is_workday": is_workday,
        "is_business_hours": is_business_hours,
        "is_lunch_time": is_lunch_time,
        "is_morning": is_morning,
        "is_afternoon": is_afternoon,
        "is_evening": is_evening,
        "is_night": is_night,
        "is_leap_year": is_leap_year,
        "is_last_week_of_month": is_last_week_of_month,
        "days_until_end_of_month": days_until_end_of_month,
        "days_until_end_of_year": days_until_end_of_year,
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
        "is_bank_holiday": is_bank_holiday,
        "current_bank_holiday_name": bank_holiday_name,
        "is_school_holiday": is_school_holiday,
        "current_school_holiday_name": current_school_holiday_name,
    }
    if custom_context:
        context |= custom_context
    return _lowercase_values(context)


def _lowercase_values(value: object) -> object:
    if isinstance(value, str):
        return _normalize_text(value)
    if isinstance(value, dict):
        return {key: _lowercase_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_lowercase_values(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_lowercase_values(item) for item in value)
    return value


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    stripped = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9_]", "_", stripped.lower())


def format_context(context: dict[str, object], place: Place | None = None) -> str:
    """Return a formatted JSON string containing all context variables."""
    payload = asdict(place) | context if place is not None else context
    payload = _lowercase_values(payload)
    return json.dumps(payload, default=str, indent=2)


def print_context(context: dict[str, object], place: Place | None = None) -> None:
    """Print the full context as formatted JSON."""
    print(format_context(context, place=place))
