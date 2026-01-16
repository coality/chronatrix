from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from chronatrix.core import Place, build_context, evaluate_condition


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Chronatrix: évalue des conditions temporelles et contextuelles "
            "en fonction d'un lieu."))
    parser.add_argument("condition", help="Expression Python à évaluer.")
    parser.add_argument("--name", default="Paris", help="Nom du lieu.")
    parser.add_argument("--country-code", default="FR", help="Code pays.")
    parser.add_argument("--country-name", default="France", help="Nom du pays.")
    parser.add_argument("--timezone", default="Europe/Paris", help="Fuseau horaire.")
    parser.add_argument("--latitude", type=float, default=48.8566, help="Latitude.")
    parser.add_argument("--longitude", type=float, default=2.3522, help="Longitude.")
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Affiche le contexte généré en JSON.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    place = Place(
        name=args.name,
        country_code=args.country_code,
        country_name=args.country_name,
        timezone=args.timezone,
        latitude=args.latitude,
        longitude=args.longitude,
    )

    context = build_context(place)
    result = evaluate_condition(args.condition, context)
    print("true" if result else "false")

    if args.show_context:
        print(json.dumps(asdict(place) | context, default=str, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
