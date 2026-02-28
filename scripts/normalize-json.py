#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Any

from constants import SRC_FILE

# Canonical key order - matches the output of generate_app_entry() in add-app.py
KEY_ORDER = [
    "id",
    "url",
    "author",
    "name",
    "preferredApkIndex",
    "additionalSettings",
    "categories",
    "allowIdChange",
    "overrideSource",
    "meta",
]

# Canonical key order for additionalSettings - source-specific keys first,
# then common keys, grouped logically. Matches DEFAULT_ADDITIONAL_SETTINGS
# in add-app.py with source-specific keys prepended.
SETTINGS_KEY_ORDER = [
    # GitHub/Codeberg source-specific
    "includePrereleases",
    "fallbackToOlderReleases",
    "filterReleaseTitlesByRegEx",
    "filterReleaseNotesByRegEx",
    "verifyLatestTag",
    "sortMethodChoice",
    "useLatestAssetDateAsReleaseDate",
    "releaseTitleAsVersion",
    "github-creds",
    "GHReqPrefix",
    # HTML source-specific
    "intermediateLink",
    "customLinkFilterRegex",
    "filterByLinkText",
    "matchLinksOutsideATags",
    "skipSort",
    "reverseSort",
    "sortByLastLinkSegment",
    "versionExtractWholePage",
    "requestHeader",
    "defaultPseudoVersioningMethod",
    # Common keys
    "trackOnly",
    "versionExtractionRegEx",
    "matchGroupToUse",
    "versionDetection",
    "releaseDateAsVersion",
    "useVersionCodeAsOSVersion",
    "apkFilterRegEx",
    "invertAPKFilter",
    "autoApkFilterByArch",
    "appName",
    "appAuthor",
    "shizukuPretendToBeGooglePlay",
    "allowInsecure",
    "exemptFromBackgroundUpdates",
    "skipUpdateNotifications",
    "about",
    "refreshBeforeDownload",
    "includeZips",
    "zippedApkFilterRegEx",
]

# Fields to backfill with defaults when missing
DEFAULTS: dict[str, object] = {
    "allowIdChange": False,
}


def _order_dict(d: dict[str, Any], key_order: list[str]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in key_order:
        if key in d:
            ordered[key] = d[key]
    # Preserve any unexpected keys at the end (safety net)
    for key in d:
        if key not in ordered:
            ordered[key] = d[key]
    return ordered


def normalize_app(app: dict) -> dict:
    for key, default in DEFAULTS.items():
        if key not in app:
            app[key] = default

    # Normalize additionalSettings key order if it's a dict
    settings = app.get("additionalSettings")
    if isinstance(settings, dict):
        app["additionalSettings"] = _order_dict(settings, SETTINGS_KEY_ORDER)

    return _order_dict(app, KEY_ORDER)


def normalize(input_path: str) -> int:
    path = Path(input_path)
    if not path.exists():
        print(f"Error: {path} not found.")
        return 1

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    apps = data.get("apps", [])
    if not apps:
        print("No apps found in file.")
        return 1

    changes = 0
    for i, app in enumerate(apps):
        normalized = normalize_app(app)

        # Check if anything changed (key order or new defaults)
        if list(app.keys()) != list(normalized.keys()) or app != normalized:
            changes += 1

        apps[i] = normalized

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if changes:
        print(f"Normalized {changes} app(s) in {path}")
    else:
        print(f"All {len(apps)} apps already normalized")

    return 0


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else SRC_FILE
    sys.exit(normalize(input_file))
