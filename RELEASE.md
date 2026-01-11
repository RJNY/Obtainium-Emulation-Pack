# v7.0.0

## Why v7?

This release represents a significant shift in how the project is maintained. Previously, adding a new app meant manually editing `applications.json`, copying boilerplate Obtainium settings, and hoping you didn't introduce a typo that would silently break things.

With v7, the tooling does the heavy lifting:

- **`make add-app`** turns a 5-minute manual process into a 30-second interactive prompt. Paste a URL, pick a category, done. No more copy-pasting JSON blocks or remembering which meta fields control which behavior.
- **`make validate`** catches mistakes before they ship. Typos in meta keys, missing required fields, duplicate app IDs—all caught at build time instead of discovered by users.
- **Refactored codebase** means less duplicated logic across scripts, making future changes easier and less error-prone.

The jump from v6 to v7 reflects that this isn't just a patch—it's a foundation for faster, more reliable releases going forward.

## Summary

- Refactored Python scripts to reduce duplication and improve maintainability
- Added `make add-app` interactive CLI for quickly adding new apps
- Added `make validate` to catch schema errors and typos before release
- Rewrote developer documentation with step-by-step guides
- Added PICO-8 Android to the app list

## New Features

### `make add-app` - Interactive CLI

Quickly add new apps without manually editing JSON:

- Auto-detects source type (GitHub, GitLab, Codeberg) from URL
- Auto-fills author and app name from GitHub URLs
- Arrow-key navigation for category and variant selection
- Variant options: Both, Standard only, Dual-screen only, README only

### `make validate` - JSON Validation

Catches common mistakes before they hit production:

- Schema validation (required fields, correct types)
- Typo detection in meta keys (e.g., `exludeFromExport` → `excludeFromExport`)
- Duplicate app ID detection per variant

## Code Changes

### New Files

- `scripts/utils.py` - Shared functions (`should_include_app`, `get_display_name`, `get_application_url`)
- `scripts/constants.py` - Centralized paths and Obtainium settings
- `scripts/validate-json.py` - Validation script
- `scripts/add-app.py` - Interactive CLI tool

### Refactored

- All Python scripts now have type hints
- All scripts have `if __name__ == "__main__"` guards (importable as modules)
- Removed duplicated logic across scripts

### Documentation

- Complete rewrite of `pages/development.md`
- Added project structure diagram
- Added meta field and categories reference tables
- Added pre-commit checklist

## New App

| Application Name                                                    | Add to Obtainium                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Included in export json? | Included in DS json? |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ | -------------------- |
| <a href="https://github.com/Macs75/pico8-android">Pico8 Android</a> | <a href="http://apps.obtainium.imranr.dev/redirect.html?r=obtainium://app/%7B%22id%22%3A%22io.wip.pico8%22%2C%22url%22%3A%22https%3A%2F%2Fgithub.com%2FMacs75%2Fpico8-android%22%2C%22author%22%3A%22Macs75%22%2C%22name%22%3A%22Pico8%20Android%22%2C%22otherAssetUrls%22%3Anull%2C%22apkUrls%22%3Anull%2C%22preferredApkIndex%22%3A0%2C%22additionalSettings%22%3A%22%7B%5C%22includePrereleases%5C%22%3Afalse%2C%5C%22fallbackToOlderReleases%5C%22%3Atrue%2C%5C%22filterReleaseTitlesByRegEx%5C%22%3A%5C%22%5C%22%2C%5C%22filterReleaseNotesByRegEx%5C%22%3A%5C%22%5C%22%2C%5C%22verifyLatestTag%5C%22%3Afalse%2C%5C%22sortMethodChoice%5C%22%3A%5C%22date%5C%22%2C%5C%22useLatestAssetDateAsReleaseDate%5C%22%3Afalse%2C%5C%22releaseTitleAsVersion%5C%22%3Afalse%2C%5C%22trackOnly%5C%22%3Afalse%2C%5C%22versionExtractionRegEx%5C%22%3A%5C%22%5C%22%2C%5C%22matchGroupToUse%5C%22%3A%5C%22%5C%22%2C%5C%22versionDetection%5C%22%3Atrue%2C%5C%22releaseDateAsVersion%5C%22%3Afalse%2C%5C%22useVersionCodeAsOSVersion%5C%22%3Afalse%2C%5C%22apkFilterRegEx%5C%22%3A%5C%22%5C%22%2C%5C%22invertAPKFilter%5C%22%3Afalse%2C%5C%22autoApkFilterByArch%5C%22%3Atrue%2C%5C%22appName%5C%22%3A%5C%22%5C%22%2C%5C%22appAuthor%5C%22%3A%5C%22%5C%22%2C%5C%22shizukuPretendToBeGooglePlay%5C%22%3Afalse%2C%5C%22allowInsecure%5C%22%3Afalse%2C%5C%22exemptFromBackgroundUpdates%5C%22%3Afalse%2C%5C%22skipUpdateNotifications%5C%22%3Afalse%2C%5C%22about%5C%22%3A%5C%22%5C%22%2C%5C%22refreshBeforeDownload%5C%22%3Afalse%7D%22%2C%22categories%22%3A%5B%22Emulator%22%5D%2C%22overrideSource%22%3A%22GitHub%22%2C%22allowIdChange%22%3Anull%7D">Add to Obtainium!</a> | ✅                       | ✅                   |
