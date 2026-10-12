"""Minify applications.json into the release JSON."""

import argparse
import json
from typing import Any

from utils import get_additional_settings, should_include_app, stringify_additional_settings


def minify_json(input_file: str, output_file: str) -> None:
    with open(input_file, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    if "apps" in data:
        filtered_apps = []
        for app in data["apps"]:
            if should_include_app(app):
                app_copy = app.copy()
                app_copy.pop("meta", None)
                settings = get_additional_settings(app_copy)
                source = app_copy.get("overrideSource")
                app_copy["additionalSettings"] = stringify_additional_settings(settings, source)
                filtered_apps.append(app_copy)
        data["apps"] = filtered_apps

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)

    print(
        f"Minified JSON saved to {output_file} ({len(data.get('apps', []))} apps included)"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Minify applications.json into the release JSON"
    )
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument("output", help="Output JSON file")

    args = parser.parse_args()
    minify_json(args.input, args.output)
