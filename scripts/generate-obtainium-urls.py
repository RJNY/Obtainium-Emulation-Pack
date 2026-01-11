"""Generate click-to-install Obtainium URLs for all apps."""

import json
import sys
import urllib.parse
from typing import Any


def generate_obtainium_url(app: dict[str, Any]) -> str:
    """Generate an Obtainium deep-link URL for an app."""
    obtainium_base = "http://apps.obtainium.imranr.dev/redirect.html?r=obtainium://app/"
    app_json = json.dumps(app, separators=(",", ":"))
    encoded_json = urllib.parse.quote(app_json)
    return f"{obtainium_base}{encoded_json}"


def main(json_file: str) -> None:
    """Print Obtainium URLs for all apps in the JSON file."""
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "apps" not in data:
        print("Invalid JSON format: Missing 'apps' key.")
        sys.exit(1)

    for app in data["apps"]:
        obtainium_url = generate_obtainium_url(app)
        print(f"{app['name']}: {obtainium_url}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_obtainium_urls.py <json_file>")
        sys.exit(1)

    main(sys.argv[1])
