"""Shared utility functions for Obtainium Emulation Pack scripts."""

from typing import Any


def should_include_app(app: dict[str, Any], variant: str) -> bool:
    """Determine if an app should be included based on variant and meta fields.

    Args:
        app: Application dictionary from applications.json
        variant: One of 'standard' or 'dual-screen'

    Returns:
        True if the app should be included in the specified variant
    """
    meta = app.get("meta", {})

    # HIGHEST PRIORITY: Global exclusion overrides everything
    if meta.get("excludeFromExport", False):
        return False

    # SECOND PRIORITY: Variant-specific inclusion/exclusion
    if variant == "standard":
        # Default: include in standard
        return meta.get("includeInStandard", True)
    elif variant == "dual-screen":
        # Default: include in dual screen
        return meta.get("includeInDualScreen", True)

    return True


def get_display_name(app: dict[str, Any]) -> str:
    """Get the display name for an app, respecting nameOverride."""
    return app.get("meta", {}).get("nameOverride") or app.get("name", "")


def get_application_url(app: dict[str, Any]) -> str:
    """Get the URL for an app, respecting urlOverride."""
    return app.get("meta", {}).get("urlOverride") or app.get("url", "")
