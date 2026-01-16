# Chronatrix

Chronatrix est un moteur contextuel qui évalue des conditions logiques en temps réel à partir d'un lieu (fuseau horaire, latitude/longitude) et d'informations environnementales (lever/coucher du soleil, saison, etc.).

## Fonctionnalités

- Contexte temporel aligné sur la zone géographique.
- Lever/coucher du soleil via `astral`.
- Saisons calculées selon la latitude (hémisphère nord/sud).
- Évaluation contrôlée d'expressions Python simples.
- CLI prête à l'emploi.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Utilisation (CLI)

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

La commande retourne `true` ou `false` et, avec `--show-context`, affiche le contexte complet en JSON.

## Utilisation (Python)

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

## Clés de contexte disponibles

- `current_time`, `current_date`, `current_datetime`
- `current_hour`, `current_month`, `current_year`, `current_weekday`, `is_weekend`
- `location_name`, `country_code`, `country_name`, `timezone`, `latitude`, `longitude`
- `sunrise_time`, `sunset_time`, `is_daytime`, `current_season`
- `current_weather`, `temperature` (placeholders)

## Sécurité des expressions

L'évaluation limite l'AST aux opérations logiques/comparaisons et à l'arithmétique simple. Toute expression non autorisée retourne `false`.

## Roadmap

- Connexion à une API météo.
- Support des jours fériés par pays.
- Ajout de presets de lieux.
