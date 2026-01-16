# Chronatrix

Chronatrix is a contextual engine that evaluates logical conditions in real time based on a location (time zone, latitude/longitude) and environmental information (sunrise/sunset, seasons, and current weather).

## Features

- Time context aligned with the geographic area.
- Sunrise/sunset via `astral`.
- Seasons computed from latitude (north/south hemisphere).
- Current weather from Open-Meteo.
- Controlled evaluation of simple Python expressions (including limited helper calls).
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

### CLI arguments

Each argument supports a default and has an expected type. Examples show typical values.

- `condition` (`str`)
  - Description: Python expression evaluated against the context.
  - Possible values: any expression using the documented context keys (e.g., logical comparisons and arithmetic).
  - Example: `"current_hour >= 18 and is_weekend"`.
- `--name` (`str`, default `"Paris"`)
  - Description: Place name.
  - Possible values: any string describing a location.
  - Example: `"Tokyo"`.
- `--country-code` (`str`, default `"FR"`)
  - Description: ISO country code.
  - Possible values: two-letter ISO 3166-1 alpha-2 code.
  - Example: `"JP"`.
- `--country-name` (`str`, default `"France"`)
  - Description: Country name.
  - Possible values: any country name.
  - Example: `"Japan"`.
- `--timezone` (`str`, default `"Europe/Paris"`)
  - Description: IANA time zone identifier.
  - Possible values: any valid IANA time zone.
  - Example: `"Asia/Tokyo"`.
- `--latitude` (`float`, default `48.8566`)
  - Description: Latitude in decimal degrees.
  - Possible values: `-90.0` to `90.0`.
  - Example: `35.6762`.
- `--longitude` (`float`, default `2.3522`)
  - Description: Longitude in decimal degrees.
  - Possible values: `-180.0` to `180.0`.
  - Example: `139.6503`.
- `--show-context` (`bool` flag, default `false`)
  - Description: Print the full context as JSON after evaluation.
  - Possible values: `true`/`false`.
  - Example: `--show-context`.
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

## Available context keys

Each key below is always present in the context returned by `build_context`.

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
- `current_year` (`int`)
  - Description: Current local year.
  - Possible values: any four-digit year.
  - Example: `2024`.
- `current_weekday` (`int`)
  - Description: Current local weekday.
  - Possible values: `0` to `6`, where `0 = Monday` and `6 = Sunday`.
  - Example: `2`.
- `is_weekend` (`bool`)
  - Description: Whether the current day is Saturday or Sunday.
  - Possible values: `true` or `false`.
  - Example: `false`.

### Location

- `location_name` (`str`)
  - Description: Place name.
  - Possible values: any string supplied in `Place.name`.
  - Example: `"Paris"`.
- `country_code` (`str`)
  - Description: ISO country code.
  - Possible values: any string supplied in `Place.country_code`.
  - Example: `"FR"`.
- `country_name` (`str`)
  - Description: Country name.
  - Possible values: any string supplied in `Place.country_name`.
  - Example: `"France"`.
- `timezone` (`str`)
  - Description: IANA time zone identifier.
  - Possible values: any valid IANA time zone (e.g., `Europe/Paris`).
  - Example: `"Europe/Paris"`.
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
