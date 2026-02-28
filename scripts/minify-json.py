"""Minify and filter Obtainium JSON based on variant."""

import argparse
import json
import sys
from typing import Any

from utils import get_additional_settings, should_include_app, stringify_additional_settings


def minify_json(input_file: str, output_file: str, variant: str = "standard") -> None:
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        if "apps" in data:
            filtered_apps = []
            for app in data["apps"]:
                if should_include_app(app, variant):
                    app_copy = app.copy()
                    app_copy.pop("meta", None)
                    settings = get_additional_settings(app_copy)
                    source = app_copy.get("overrideSource")
                    app_copy["additionalSettings"] = stringify_additional_settings(settings, source)
                    filtered_apps.append(app_copy)
            data["apps"] = filtered_apps

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"), ensure_ascii=False)

        variant_label = f" ({variant})" if variant != "standard" else ""
        print(
            f"Minified JSON{variant_label} saved to {output_file} ({len(data.get('apps', []))} apps included)"
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Minify and filter Obtainium JSON based on variant"
    )
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument("output", help="Output JSON file")
    parser.add_argument(
        "--variant",
        choices=["standard", "dual-screen"],
        default="standard",
        help="Variant to build (default: standard)",
    )

    args = parser.parse_args()
    minify_json(args.input, args.output, args.variant)
