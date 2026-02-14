"""Shared utility functions for Obtainium Emulation Pack scripts."""

import json
import os
import urllib.parse
from pathlib import Path
from typing import Any

from constants import OBTAINIUM_SCHEME, REDIRECT_URL


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


def make_obtainium_link(app: dict[str, Any]) -> str:
    payload = {
        "id": app["id"],
        "url": app["url"],
        "author": app["author"],
        "name": app["name"],
        "otherAssetUrls": app.get("otherAssetUrls"),
        "apkUrls": app.get("apkUrls"),
        "preferredApkIndex": app.get("preferredApkIndex"),
        "additionalSettings": app.get("additionalSettings"),
        "categories": app.get("categories"),
        "overrideSource": app.get("overrideSource"),
        "allowIdChange": app.get("allowIdChange"),
    }
    encoded = urllib.parse.quote(json.dumps(payload, separators=(",", ":")), safe="")
    return f"{REDIRECT_URL}?r={OBTAINIUM_SCHEME}{encoded}"
