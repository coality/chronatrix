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

## Installation (depuis Git)

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

context = build_context(place, custom_context={"temperature": 12, "user_role": "admin"})
condition = "current_hour >= 18 and is_weekend"
result = evaluate_condition(condition, context)
print(result)
print_context(context, place=place)
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

## Variables statiques vs dynamiques

Chronatrix construit le contexte à partir de deux sources :

### Variables statiques (fournies par l'utilisateur)

- Champs `Place` (`name`, `country_code`, `country_name`, `timezone`, `latitude`, `longitude`).
- `custom_context` passé à `build_context` (ex : `{"temperature": 12, "user_role": "admin"}`).

Ces variables sont saisies par l'utilisateur et restent inchangées tant que vous ne les modifiez pas.
Si une clé de `custom_context` a le même nom qu'une clé calculée, elle la remplace.

### Variables dynamiques (calculées par Chronatrix)

- Date/heure locale (`current_time`, `current_date`, `current_datetime`, `current_hour`, etc.).
- Indicateurs calendaires (`is_weekend`, `current_season`).
- Données solaires (`sunrise_time`, `sunset_time`, `is_daytime`).
- Météo (`current_weather`, `temperature`) via Open-Meteo.

Ces valeurs changent automatiquement en fonction de l'heure et de la localisation.

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

## Publication sur PyPI

1. Mettre à jour la version dans `pyproject.toml`.
2. Construire les distributions :

   ```bash
   python -m build
   ```

3. Vérifier les artefacts :

   ```bash
   python -m twine check dist/*
   ```

4. Publier :

   ```bash
   python -m twine upload dist/*
   ```
