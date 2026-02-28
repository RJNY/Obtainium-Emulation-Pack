"""Shared utility functions for Obtainium Emulation Pack scripts."""

import copy
import json
import os
import urllib.parse
from pathlib import Path
from typing import Any

from constants import OBTAINIUM_SCHEME, REDIRECT_URL, SETTINGS_SCHEMA


def load_dotenv() -> None:
    """Load .env into os.environ. Real env vars take precedence. Blank values skipped."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and value and key not in os.environ:
                os.environ[key] = value


def should_include_app(app: dict[str, Any], variant: str) -> bool:
    meta = app.get("meta", {})
    if meta.get("excludeFromExport", False):
        return False
    if variant == "standard":
        return meta.get("includeInStandard", True)
    elif variant == "dual-screen":
        return meta.get("includeInDualScreen", True)
    return True


def get_display_name(app: dict[str, Any]) -> str:
    return app.get("meta", {}).get("nameOverride") or app.get("name", "")


def get_application_url(app: dict[str, Any]) -> str:
    return app.get("meta", {}).get("urlOverride") or app.get("url", "")


def get_additional_settings(app: dict[str, Any]) -> dict[str, Any]:
    """Return additionalSettings as a dict, whether stored as object or JSON string."""
    raw = app.get("additionalSettings", {})
    if isinstance(raw, str):
        return json.loads(raw) if raw else {}
    if isinstance(raw, dict):
        return raw
    return {}


def get_defaults_for_source(source: str | None) -> dict[str, Any]:
    """Return the full default settings dict for a given source type."""
    defaults: dict[str, Any] = {}
    for key, defn in SETTINGS_SCHEMA.items():
        if source is None or source in defn.sources:
            defaults[key] = copy.deepcopy(defn.default)
    return defaults


def hydrate_settings(sparse: dict[str, Any], source: str | None) -> dict[str, Any]:
    """Merge sparse settings with schema defaults to produce a full settings dict.

    Keys are ordered according to SETTINGS_SCHEMA insertion order.
    """
    defaults = get_defaults_for_source(source)
    defaults.update(sparse)
    return defaults


def stringify_additional_settings(
    settings: dict[str, Any],
    source: str | None = None,
) -> str:
    """Hydrate and stringify settings for Obtainium consumption."""
    hydrated = hydrate_settings(settings, source)
    return json.dumps(hydrated, separators=(",", ":"))


def make_obtainium_link(app: dict[str, Any]) -> str:
    settings = get_additional_settings(app)
    source = app.get("overrideSource")
    payload = {
        "id": app["id"],
        "url": app["url"],
        "author": app["author"],
        "name": app["name"],
        "otherAssetUrls": app.get("otherAssetUrls"),
        "apkUrls": app.get("apkUrls"),
        "preferredApkIndex": app.get("preferredApkIndex"),
        "additionalSettings": stringify_additional_settings(settings, source),
        "categories": app.get("categories"),
        "overrideSource": app.get("overrideSource"),
        "allowIdChange": app.get("allowIdChange"),
    }
    encoded = urllib.parse.quote(json.dumps(payload, separators=(",", ":")), safe="")
    return f"{REDIRECT_URL}?r={OBTAINIUM_SCHEME}{encoded}"
