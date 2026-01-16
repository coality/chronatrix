# Chronatrix

Chronatrix is a contextual engine that evaluates logical conditions in real time based on a location (time zone, latitude/longitude) and environmental information (sunrise/sunset, seasons, and current weather).

## Features

- Time context aligned with the geographic area.
- Sunrise/sunset via `astral`.
- Seasons computed from latitude (north/south hemisphere).
- Current weather from Open-Meteo.
- Controlled evaluation of simple Python expressions (including limited helper calls).
- Simple Python library (no CLI).

## Installation (PyPI)

```bash
pip install chronatrix
```

## Installation (from Git)

```bash
git clone https://github.com/coality/chronatrix.git
cd chronatrix
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage (Python)

```python
from chronatrix import Place, build_context, evaluate_condition, print_context

place = Place(
    name="Paris",
    country_code="FR",
    country_name="France",
    timezone="Europe/Paris",
    latitude=48.8566,
    longitude=2.3522,
)

context = build_context(
    place,
    custom_context={"temperature": 12, "user_role": "admin"},
    debug=True,
)
condition = "current_hour >= 18 and is_weekend"
result = evaluate_condition(condition, context)
print(result)
print_context(context, place=place)
```

### Debugging API calls

Enable debug logging to see detailed API requests, responses, and errors for
weather and holiday lookups. Chronatrix uses the standard Python logging
system, so configure logging in your application and pass `debug=True` to
`build_context`:

```python
import logging
from chronatrix import Place, build_context

logging.basicConfig(level=logging.DEBUG)

place = Place(
    name="Paris",
    country_code="FR",
    country_name="France",
    timezone="Europe/Paris",
    latitude=48.8566,
    longitude=2.3522,
)

context = build_context(place, debug=True)
```

### Place fields

Each `Place` field is required and used to compute the context.

- `name` (`str`)
  - Description: Human-friendly place name.
  - Possible values: any string.
  - Example: `"Paris"`.
- `country_code` (`str`)
  - Description: ISO country code.
  - Possible values: two-letter ISO 3166-1 alpha-2 codes.
  - Example: `"FR"`.
- `country_name` (`str`)
  - Description: Country name.
  - Possible values: any country name.
  - Example: `"France"`.
- `timezone` (`str`)
  - Description: IANA time zone identifier.
  - Possible values: valid IANA time zone values.
  - Example: `"Europe/Paris"`.
- `latitude` (`float`)
  - Description: Latitude in decimal degrees.
  - Possible values: `-90.0` to `90.0`.
  - Example: `48.8566`.
- `longitude` (`float`)
  - Description: Longitude in decimal degrees.
  - Possible values: `-180.0` to `180.0`.
  - Example: `2.3522`.

## Static vs. dynamic variables

Chronatrix builds the context from two sources:

### Static variables (provided by the user)

- `Place` fields (`name`, `country_code`, `country_name`, `timezone`, `latitude`, `longitude`).
- `custom_context` passed to `build_context` (e.g., `{"temperature": 12, "user_role": "admin"}`).
- `reference_datetime` passed to `build_context` to override the current date/time.
- `holiday_zone` in `custom_context` (`"A"`, `"B"`, or `"C"`).

These variables are entered by the user and remain unchanged unless you update them.
If a `custom_context` key has the same name as a computed key, it overrides it.
String values from `custom_context` are returned in lowercase to match the rest of the context.

### Dynamic variables (computed by Chronatrix)

- Local date/time (`current_time`, `current_date`, `current_datetime`, `current_hour`, etc.).
- Calendar indicators (`is_weekend`, `current_season`).
- Solar data (`sunrise_time`, `sunset_time`, `is_daytime`).
- Weather (`current_weather`, `temperature`) via Open-Meteo.
- French bank holiday flags for `country_code="FR"`.
- French school holiday flags using `holiday_zone` and `vacances-scolaires-france`.

These values change automatically based on time and location.

### Overriding the current date/time

Use `reference_datetime` to evaluate the context for a specific moment. If the datetime
is naive (no timezone), Chronatrix assumes the place time zone.

```python
from datetime import datetime

context = build_context(
    place,
    reference_datetime=datetime(2024, 4, 12, 9, 30),
)
```

## Available context keys

Each key below is always present in the context returned by `build_context`.
All string values returned in the context are normalized to lowercase (including values from `custom_context`).

### Date and time

- `current_time` (`datetime.time`)
  - Description: Current local time.
  - Possible values: `00:00:00` to `23:59:59.999999`.
  - Example: `14:37:05`.
- `current_date` (`datetime.date`)
  - Description: Current local date.
  - Possible values: any calendar date.
  - Example: `2024-04-12`.
- `current_datetime` (`datetime.datetime`)
  - Description: Current local date-time (timezone-aware).
  - Possible values: any timezone-aware datetime for the configured time zone.
  - Example: `2024-04-12 14:37:05+02:00`.
- `current_hour` (`int`)
  - Description: Current local hour.
  - Possible values: `0` to `23`.
  - Example: `14`.
- `current_month` (`int`)
  - Description: Current local month.
  - Possible values: `1` to `12`.
  - Example: `4`.
- `current_quarter` (`str`)
  - Description: Calendar quarter of the current month.
  - Possible values: `"q1"`, `"q2"`, `"q3"`, `"q4"`.
  - Example: `"q2"`.
- `current_month_name` (`str`)
  - Description: Month name in the configured locale.
  - Possible values: any month name in lowercase.
  - Example: `"april"`.
- `current_year` (`int`)
  - Description: Current local year.
  - Possible values: any four-digit year.
  - Example: `2024`.
- `current_weekday` (`int`)
  - Description: Current local weekday.
  - Possible values: `0` to `6`, where `0 = Monday` and `6 = Sunday`.
  - Example: `2`.
- `week_day_name` (`str`)
  - Description: Weekday name.
  - Possible values: any weekday name in lowercase.
  - Example: `"tuesday"`.
- `is_weekend` (`bool`)
  - Description: Whether the current day is Saturday or Sunday.
  - Possible values: `true` or `false`.
  - Example: `false`.

- `is_bank_holiday` (`bool`)
  - Description: Whether the current date is a French bank holiday.
  - Possible values: `true` or `false`.
  - Example: `true`.
- `current_bank_holiday_name` (`str | None`)
  - Description: The current French bank holiday name, if any.
  - Possible values: any bank holiday name in lowercase, or `null`.
  - Example: `"bastille_day"`.
- `is_school_holiday` (`bool`)
  - Description: Whether the current date is within French school holidays for the provided zone.
  - Possible values: `true` or `false`.
  - Example: `false`.
- `current_school_holiday_name` (`str | None`)
  - Description: The current French school holiday name for the provided zone, if any.
  - Possible values: any school holiday name in lowercase, or `null`.
  - Example: `"vacances_d_hiver"`.
- `is_workday` (`bool`)
  - Description: Whether the current day is Monday through Friday.
  - Possible values: `true` or `false`.
  - Example: `true`.
- `is_business_hours` (`bool`)
  - Description: Whether the time is within 09:00 to 16:59 on a workday.
  - Possible values: `true` or `false`.
  - Example: `false`.
- `is_lunch_time` (`bool`)
  - Description: Whether the time is within 12:00 to 13:59 on a workday.
  - Possible values: `true` or `false`.
  - Example: `true`.
- `is_morning` (`bool`)
  - Description: Whether the time is within 05:00 to 11:59.
  - Possible values: `true` or `false`.
  - Example: `true`.
- `is_afternoon` (`bool`)
  - Description: Whether the time is within 12:00 to 16:59.
  - Possible values: `true` or `false`.
  - Example: `false`.
- `is_evening` (`bool`)
  - Description: Whether the time is within 17:00 to 22:00.
  - Possible values: `true` or `false`.
  - Example: `true`.
- `is_night` (`bool`)
  - Description: Whether the time is within 23:00 to 04:59.
  - Possible values: `true` or `false`.
  - Example: `false`.
- `is_leap_year` (`bool`)
  - Description: Whether the current year is a leap year.
  - Possible values: `true` or `false`.
  - Example: `false`.
- `is_last_week_of_month` (`bool`)
  - Description: Whether the current date is in the last week of the month.
  - Possible values: `true` or `false`.
  - Example: `false`.
- `days_until_end_of_month` (`int`)
  - Description: Number of days remaining until the end of the current month.
  - Possible values: `0` to `30` (depends on month length).
  - Example: `12`.
- `days_until_end_of_year` (`int`)
  - Description: Number of days remaining until the end of the current year.
  - Possible values: `0` to `365` (or `366` in leap years).
  - Example: `256`.

### Location

- `location_name` (`str`)
  - Description: Place name.
  - Possible values: any string supplied in `Place.name`, returned in lowercase.
  - Example: `"paris"`.
- `country_code` (`str`)
  - Description: ISO country code.
  - Possible values: any string supplied in `Place.country_code`, returned in lowercase.
  - Example: `"fr"`.
- `country_name` (`str`)
  - Description: Country name.
  - Possible values: any string supplied in `Place.country_name`, returned in lowercase.
  - Example: `"france"`.
- `timezone` (`str`)
  - Description: IANA time zone identifier.
  - Possible values: any valid IANA time zone (e.g., `Europe/Paris`), returned in lowercase.
  - Example: `"europe/paris"`.
- `latitude` (`float`)
  - Description: Latitude in decimal degrees.
  - Possible values: `-90.0` to `90.0`.
  - Example: `48.8566`.
- `longitude` (`float`)
  - Description: Longitude in decimal degrees.
  - Possible values: `-180.0` to `180.0`.
  - Example: `2.3522`.

### Sun and seasons

- `sunrise_time` (`datetime.time`)
  - Description: Local sunrise time.
  - Possible values: `00:00:00` to `23:59:59.999999` (depends on location and date).
  - Example: `06:42:18`.
- `sunset_time` (`datetime.time`)
  - Description: Local sunset time.
  - Possible values: `00:00:00` to `23:59:59.999999` (depends on location and date).
  - Example: `20:15:43`.
- `is_daytime` (`bool`)
  - Description: Whether it is between sunrise and sunset (inclusive).
  - Possible values: `true` or `false`.
  - Example: `true`.
- `current_season` (`str`)
  - Description: Season name computed from the date and latitude.
  - Possible values: `"spring"`, `"summer"`, `"autumn"`, `"winter"`.
  - Example: `"spring"`.
  - Note: For the southern hemisphere, seasons are inverted.

### Weather

- `current_weather` (`str`)
  - Description: Weather label mapped from Open-Meteo codes.
  - Possible values: `"clear"`, `"mainly_clear"`, `"partly_cloudy"`, `"overcast"`, `"fog"`, `"depositing_rime_fog"`,
    `"light_drizzle"`, `"moderate_drizzle"`, `"dense_drizzle"`, `"light_freezing_drizzle"`,
    `"dense_freezing_drizzle"`, `"light_rain"`, `"moderate_rain"`, `"heavy_rain"`,
    `"light_freezing_rain"`, `"heavy_freezing_rain"`, `"light_snow"`, `"moderate_snow"`, `"heavy_snow"`,
    `"snow_grains"`, `"light_rain_showers"`, `"moderate_rain_showers"`, `"violent_rain_showers"`,
    `"light_snow_showers"`, `"heavy_snow_showers"`, `"thunderstorm"`,
    `"thunderstorm_with_light_hail"`, `"thunderstorm_with_heavy_hail"`, or `"unknown"`.
  - Example: `"partly_cloudy"`.
- `temperature` (`float | None`)
  - Description: Current air temperature from Open-Meteo (°C).
  - Possible values: any real number, or `null` if unavailable.
  - Example: `12.4`.

## Expression safety

The evaluator limits the AST to logical operations, comparisons, and simple arithmetic.
Any disallowed expression returns `false`.

## Roadmap

- Adjust weather descriptors if needed.
- Support public holidays per country.
- Add place presets.

## Publishing to PyPI

1. Update the version in `pyproject.toml`.
2. Build the distributions:

   ```bash
   python -m build
   ```

3. Verify the artifacts:

   ```bash
   python -m twine check dist/*
   ```

4. Publish:

   ```bash
   python -m twine upload dist/*
   ```
