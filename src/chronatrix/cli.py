from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from chronatrix.core import LANGUAGE_OPTIONS, Place, build_context, evaluate_condition


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Chronatrix: evaluate temporal and contextual conditions "
            "for a given place."))
    parser.add_argument("condition", help="Python expression to evaluate.")
    parser.add_argument("--name", default="Paris", help="Place name.")
    parser.add_argument("--country-code", default="FR", help="Country code.")
    parser.add_argument("--country-name", default="France", help="Country name.")
    parser.add_argument("--timezone", default="Europe/Paris", help="Time zone.")
    parser.add_argument("--latitude", type=float, default=48.8566, help="Latitude.")
    parser.add_argument("--longitude", type=float, default=2.3522, help="Longitude.")
    parser.add_argument(
        "--language",
        default="en",
        choices=sorted(LANGUAGE_OPTIONS),
        help="Context language for textual values (en).",
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Print the generated context as JSON.",
    )
    parser.add_argument(
        "--custom-context",
        default="",
        help=(
            "JSON object of additional context variables. "
            "Example: '{\"temperature\": 18, \"user\": \"alice\"}'."
        ),
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

    custom_context: dict[str, object] | None = None
    if args.custom_context:
        try:
            parsed_custom = json.loads(args.custom_context)
        except json.JSONDecodeError as exc:
            parser.error(f"Invalid JSON for --custom-context: {exc}")
        if not isinstance(parsed_custom, dict):
            parser.error("--custom-context must be a JSON object")
        custom_context = parsed_custom

    context = build_context(place, language=args.language, custom_context=custom_context)
    result = evaluate_condition(args.condition, context)
    print("true" if result else "false")

    if args.show_context:
        print(json.dumps(asdict(place) | context, default=str, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
