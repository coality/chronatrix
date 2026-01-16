# Chronatrix

Chronatrix is a contextual engine that evaluates logical conditions in real time based on a location (time zone, latitude/longitude) and environmental information (sunrise/sunset, season, etc.).

## Features

- Time context aligned with the geographic area.
- Sunrise/sunset via `astral`.
- Seasons computed from latitude (north/south hemisphere).
- Controlled evaluation of simple Python expressions.
- Ready-to-use CLI.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage (CLI)

```bash
chronatrix "(current_hour >= 18 and is_weekend) or (temperature is not None and temperature < 5)" \
  --name Paris \
  --country-code FR \
  --country-name France \
  --timezone Europe/Paris \
  --latitude 48.8566 \
  --longitude 2.3522 \
  --show-context
```

The command returns `true` or `false` and, with `--show-context`, prints the full context as JSON.

## Usage (Python)

```python
from chronatrix import Place, build_context, evaluate_condition

place = Place(
    name="Paris",
    country_code="FR",
    country_name="France",
    timezone="Europe/Paris",
    latitude=48.8566,
    longitude=2.3522,
)

context = build_context(place)
condition = "current_hour >= 18 and is_weekend"
result = evaluate_condition(condition, context)
print(result)
```

## Available context keys

Each key below is always present in the context returned by `build_context`.

### Date and time

- `current_time`: Current local time (`datetime.time`).
  - Possible values: `00:00:00` to `23:59:59.999999`.
- `current_date`: Current local date (`datetime.date`).
  - Possible values: any calendar date.
- `current_datetime`: Current local date-time (`datetime.datetime`).
  - Possible values: any timezone-aware datetime for the configured time zone.
- `current_hour`: Current local hour (`int`).
  - Possible values: `0` to `23`.
- `current_month`: Current local month (`int`).
  - Possible values: `1` to `12`.
- `current_year`: Current local year (`int`).
  - Possible values: any four-digit year.
- `current_weekday`: Current local weekday (`int`).
  - Possible values: `0` to `6`, where `0 = Monday` and `6 = Sunday`.
- `is_weekend`: Whether the current day is Saturday or Sunday (`bool`).
  - Possible values: `true` or `false`.

### Location

- `location_name`: Place name (`str`).
  - Possible values: any string supplied in `Place.name`.
- `country_code`: ISO country code (`str`).
  - Possible values: any string supplied in `Place.country_code`.
- `country_name`: Country name (`str`).
  - Possible values: any string supplied in `Place.country_name`.
- `timezone`: IANA time zone identifier (`str`).
  - Possible values: any valid IANA time zone (e.g., `Europe/Paris`).
- `latitude`: Latitude (`float`).
  - Possible values: `-90.0` to `90.0`.
- `longitude`: Longitude (`float`).
  - Possible values: `-180.0` to `180.0`.

### Sun and seasons

- `sunrise_time`: Local sunrise time (`datetime.time`).
  - Possible values: `00:00:00` to `23:59:59.999999` (depends on location and date).
- `sunset_time`: Local sunset time (`datetime.time`).
  - Possible values: `00:00:00` to `23:59:59.999999` (depends on location and date).
- `is_daytime`: Whether it is between sunrise and sunset (`bool`).
  - Possible values: `true` or `false`.
- `current_season`: Season name (`str`).
  - Possible values: `"spring"`, `"summer"`, `"autumn"`, `"winter"`.
  - Note: For the southern hemisphere, seasons are inverted.

### Weather placeholders

- `current_weather`: Placeholder string for future weather integration (`str`).
  - Possible values: currently always `"unknown"`.
- `temperature`: Placeholder temperature value (`float | None`).
  - Possible values: currently always `null` (`None` in Python).

## Expression safety

The evaluator limits the AST to logical operations/comparisons and simple arithmetic. Any disallowed expression returns `false`.

## Roadmap

- Connect to a weather API.
- Support public holidays per country.
- Add place presets.
