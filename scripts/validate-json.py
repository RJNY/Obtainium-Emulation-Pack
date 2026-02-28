"""Validate applications.json against schema and check for common issues."""

import json
import re
import sys
from typing import Any
from urllib.parse import urlparse

from constants import (
    COMMON_SETTINGS_KEYS,
    DEPRECATED_SETTINGS_KEYS,
    REGEX_SETTINGS_KEYS,
    SOURCE_HOST_MAP,
    SOURCE_SPECIFIC_KEYS,
    VALID_SOURCES,
    VARIANTS,
)
from utils import should_include_app

REQUIRED_FIELDS = {"id", "url", "author", "name"}

VALID_META_KEYS = {
    "excludeFromExport",
    "excludeFromTable",
    "nameOverride",
    "urlOverride",
    "includeInStandard",
    "includeInDualScreen",
}

META_TYPO_MAP = {
    "exludeFromExport": "excludeFromExport",
    "exludeFromTable": "excludeFromTable",
    "nameOveride": "nameOverride",
    "urlOveride": "urlOverride",
}


def _check_regex(pattern: str, field_name: str, app_name: str) -> str | None:
    if not pattern:
        return None
    try:
        re.compile(pattern)
        return None
    except re.error as e:
        return f"{app_name}: invalid regex in '{field_name}': {e} (pattern: {pattern!r})"


def _detect_source_from_url(url: str) -> str | None:
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return None
    for domain, source in SOURCE_HOST_MAP.items():
        if host == domain or host.endswith(f".{domain}"):
            return source
    return None


def _valid_keys_for_source(source: str | None) -> set[str]:
    valid = set(COMMON_SETTINGS_KEYS) | set(DEPRECATED_SETTINGS_KEYS)
    if source and source in SOURCE_SPECIFIC_KEYS:
        valid |= SOURCE_SPECIFIC_KEYS[source]
    return valid


def _validate_required_fields(app: dict, app_name: str) -> list[str]:
    return [
        f"{app_name}: missing required field '{f}'"
        for f in REQUIRED_FIELDS
        if f not in app
    ]


def _validate_url(app: dict, app_name: str) -> list[str]:
    errors = []
    url = app.get("url", "")
    if not url:
        return errors
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            errors.append(f"{app_name}: URL missing scheme (http/https): {url}")
        elif parsed.scheme not in ("http", "https"):
            errors.append(f"{app_name}: URL has non-http scheme: {parsed.scheme}")
        if not parsed.netloc:
            errors.append(f"{app_name}: URL missing host: {url}")
    except Exception as e:
        errors.append(f"{app_name}: malformed URL: {e}")
    return errors


def _validate_override_source(
    app: dict, app_name: str
) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    source = app.get("overrideSource")
    url = app.get("url", "")

    if source is not None and source not in VALID_SOURCES:
        errors.append(
            f"{app_name}: unknown overrideSource '{source}' "
            f"(valid: {', '.join(sorted(VALID_SOURCES))})"
        )
    elif source is None:
        warnings.append(f"{app_name}: missing overrideSource (auto-detection may be fragile)")

    if url and source:
        detected = _detect_source_from_url(url)
        if detected and detected != source and source != "HTML" and detected != "HTML":
            warnings.append(
                f"{app_name}: URL host suggests '{detected}' but "
                f"overrideSource is '{source}'"
            )

    return errors, warnings


def _validate_apk_index(app: dict, app_name: str) -> list[str]:
    index = app.get("preferredApkIndex")
    if index is not None and (not isinstance(index, int) or index < 0):
        return [
            f"{app_name}: preferredApkIndex must be a non-negative integer, got {index!r}"
        ]
    return []


def _validate_meta(app: dict, app_name: str) -> list[str]:
    errors = []
    meta = app.get("meta", {})

    for key in meta:
        if key not in VALID_META_KEYS:
            errors.append(f"{app_name}: unknown meta key '{key}' (typo?)")

    for typo, correct in META_TYPO_MAP.items():
        if typo in meta:
            errors.append(f"{app_name}: typo in meta key '{typo}', should be '{correct}'")

    return errors


def _validate_categories(app: dict, app_name: str) -> list[str]:
    categories = app.get("categories")
    if categories is not None and not isinstance(categories, list):
        return [f"{app_name}: 'categories' should be a list"]
    return []


def _validate_additional_settings(
    app: dict, app_name: str
) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    raw = app.get("additionalSettings")
    if raw is None:
        return errors, warnings

    if not isinstance(raw, str):
        errors.append(f"{app_name}: 'additionalSettings' should be a JSON string")
        return errors, warnings

    try:
        settings = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append(f"{app_name}: 'additionalSettings' contains invalid JSON: {e}")
        return errors, warnings

    if not isinstance(settings, dict):
        return errors, warnings

    # Validate regex fields
    for key in REGEX_SETTINGS_KEYS:
        value = settings.get(key, "")
        if isinstance(value, str):
            err = _check_regex(value, key, app_name)
            if err:
                errors.append(err)

    # Validate regex in intermediate link steps
    for i, link in enumerate(settings.get("intermediateLink", [])):
        if isinstance(link, dict):
            regex_val = link.get("customLinkFilterRegex", "")
            if isinstance(regex_val, str):
                err = _check_regex(regex_val, f"intermediateLink[{i}].customLinkFilterRegex", app_name)
                if err:
                    errors.append(err)

    # Warn on deprecated keys
    for key, replacement in DEPRECATED_SETTINGS_KEYS.items():
        if key in settings:
            warnings.append(
                f"{app_name}: deprecated key '{key}', use '{replacement}' instead"
            )

    # Check for source-inappropriate keys
    url = app.get("url", "")
    effective_source = app.get("overrideSource") or _detect_source_from_url(url)
    if effective_source:
        valid_keys = _valid_keys_for_source(effective_source)
        for key in settings:
            if key not in valid_keys:
                belongs_to = [
                    s for s, keys in SOURCE_SPECIFIC_KEYS.items()
                    if key in keys and s != effective_source
                ]
                if belongs_to:
                    warnings.append(
                        f"{app_name}: additionalSettings key '{key}' "
                        f"is for {'/'.join(belongs_to)}, not {effective_source}"
                    )

    return errors, warnings


def validate_app(app: dict[str, Any], index: int) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    app_name = app.get("name", f"app[{index}]")

    errors += _validate_required_fields(app, app_name)
    errors += _validate_url(app, app_name)

    src_errors, src_warnings = _validate_override_source(app, app_name)
    errors += src_errors
    warnings += src_warnings

    errors += _validate_apk_index(app, app_name)
    errors += _validate_meta(app, app_name)
    errors += _validate_categories(app, app_name)

    settings_errors, settings_warnings = _validate_additional_settings(app, app_name)
    errors += settings_errors
    warnings += settings_warnings

    return errors, warnings


def check_duplicate_ids(apps: list[dict[str, Any]], variant: str) -> list[str]:
    errors = []
    ids_seen: dict[str, str] = {}

    for app in apps:
        if not should_include_app(app, variant):
            continue

        app_id = app.get("id", "")
        app_name = app.get("name", "unknown")
        if not app_id:
            continue

        if app_id in ids_seen:
            errors.append(
                f"Duplicate ID '{app_id}' in {variant} variant: "
                f"'{ids_seen[app_id]}' and '{app_name}'"
            )
        else:
            ids_seen[app_id] = app_name

    return errors


def validate_json(input_file: str) -> int:
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
    all_errors, all_warnings = [], []

    for i, app in enumerate(apps):
        errors, warnings = validate_app(app, i)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    for variant in VARIANTS:
        all_errors.extend(check_duplicate_ids(apps, variant))

    if all_warnings:
        print(f"Warnings ({len(all_warnings)}):\n")
        for warning in all_warnings:
            print(f"  ~ {warning}")
        print()

    if all_errors:
        print(f"Validation failed with {len(all_errors)} error(s):\n")
        for error in all_errors:
            print(f"  x {error}")
        return 1

    print(f"Validation passed: {len(apps)} apps checked", end="")
    if all_warnings:
        print(f" ({len(all_warnings)} warnings)")
    else:
        print()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate-json.py <json_file>")
        sys.exit(1)

    sys.exit(validate_json(sys.argv[1]))
