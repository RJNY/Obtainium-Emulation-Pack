"""Validate applications.json against schema and check for common issues."""

import json
import sys
from collections import defaultdict
from typing import Any

# Required fields for each app
REQUIRED_FIELDS = {"id", "url", "author", "name"}

# Valid meta keys
VALID_META_KEYS = {
    "excludeFromExport",
    "excludeFromTable",
    "nameOverride",
    "urlOverride",
    "includeInStandard",
    "includeInDualScreen",
}

# Valid variants
VARIANTS = ("standard", "dual-screen")


def validate_app(app: dict[str, Any], index: int) -> list[str]:
    """Validate a single app entry and return list of errors."""
    errors = []
    app_name = app.get("name", f"app[{index}]")

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in app:
            errors.append(f"{app_name}: missing required field '{field}'")

    # Validate meta keys if present
    meta = app.get("meta", {})
    for key in meta.keys():
        if key not in VALID_META_KEYS:
            errors.append(f"{app_name}: unknown meta key '{key}' (typo?)")

    # Check for common typos
    typo_checks = {
        "exludeFromExport": "excludeFromExport",
        "exludeFromTable": "excludeFromTable",
        "nameOveride": "nameOverride",
        "urlOveride": "urlOverride",
    }
    for typo, correct in typo_checks.items():
        if typo in meta:
            errors.append(f"{app_name}: typo in meta key '{typo}', should be '{correct}'")

    # Validate categories is a list
    categories = app.get("categories")
    if categories is not None and not isinstance(categories, list):
        errors.append(f"{app_name}: 'categories' should be a list")

    return errors


def check_duplicate_ids(apps: list[dict[str, Any]], variant: str) -> list[str]:
    """Check for duplicate app IDs within a variant."""
    errors = []
    ids_seen: dict[str, str] = {}

    for app in apps:
        meta = app.get("meta", {})

        # Skip if excluded from this variant
        if meta.get("excludeFromExport", False):
            continue
        if variant == "standard" and not meta.get("includeInStandard", True):
            continue
        if variant == "dual-screen" and not meta.get("includeInDualScreen", True):
            continue

        app_id = app.get("id", "")
        app_name = app.get("name", "unknown")

        if not app_id:
            continue  # Already caught by required field check

        if app_id in ids_seen:
            errors.append(
                f"Duplicate ID '{app_id}' in {variant} variant: "
                f"'{ids_seen[app_id]}' and '{app_name}'"
            )
        else:
            ids_seen[app_id] = app_name

    return errors


def validate_json(input_file: str) -> int:
    """Validate applications.json and return exit code (0=success, 1=errors)."""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return 1
    except FileNotFoundError:
        print(f"File not found: {input_file}")
        return 1

    if "apps" not in data:
        print("Missing 'apps' key in JSON")
        return 1

    apps = data["apps"]
    all_errors = []

    # Validate each app
    for i, app in enumerate(apps):
        errors = validate_app(app, i)
        all_errors.extend(errors)

    # Check for duplicate IDs per variant
    for variant in VARIANTS:
        errors = check_duplicate_ids(apps, variant)
        all_errors.extend(errors)

    if all_errors:
        print(f"Validation failed with {len(all_errors)} error(s):\n")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print(f"Validation passed: {len(apps)} apps checked")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate-json.py <json_file>")
        sys.exit(1)

    sys.exit(validate_json(sys.argv[1]))
