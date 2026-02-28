#!/usr/bin/env python3
"""Interactive CLI to quickly add new apps to applications.json."""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from utils import load_dotenv

CATEGORIES = [
    "Emulator",
    "Frontend",
    "Utilities",
    "PC Emulation",
    "Streaming",
    "Track Only",
]

VARIANT_OPTIONS = [
    "Both",
    "Standard only",
    "Dual-screen only",
    "README only",
]

SOURCE_DETECTION = {
    "github.com": "GitHub",
    "gitlab.com": "GitLab",
    "codeberg.org": "Codeberg",
    "f-droid.org": "F-Droid",
}


def detect_source(url: str):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    for domain, source in SOURCE_DETECTION.items():
        if domain in host:
            return source
    return None


def extract_github_info(url: str) -> tuple[str, str] | None:
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", url)
    if match:
        return match.group(1), match.group(2)
    return None


def prompt(message: str, default: str = "") -> str:
    if default:
        result = input(f"{message} [{default}]: ").strip()
        return result if result else default
    return input(f"{message}: ").strip()


def prompt_yes_no(message: str, default: bool = True) -> bool:
    default_str = "Y/n" if default else "y/N"
    result = input(f"{message} [{default_str}]: ").strip().lower()
    if not result:
        return default
    return result in ("y", "yes")


def select_menu(title: str, choices: list[str], default: int = 0) -> str:
    # Only use curses if we have a real terminal
    if not sys.stdin.isatty():
        return _select_menu_fallback(title, choices, default)

    try:
        import curses

        return _select_menu_curses(title, choices, default)
    except Exception:
        # Fallback to simple input if curses fails
        return _select_menu_fallback(title, choices, default)


def _select_menu_curses(title: str, choices: list[str], default: int = 0) -> str:

    def menu(stdscr):
        curses.curs_set(0)
        current = default

        while True:
            stdscr.clear()
            stdscr.addstr(0, 0, title)
            stdscr.addstr(1, 0, "(Use arrow keys, Enter to select)")

            for i, choice in enumerate(choices):
                y = i + 3
                if i == current:
                    stdscr.attron(curses.A_REVERSE)
                    stdscr.addstr(y, 2, f" {choice} ")
                    stdscr.attroff(curses.A_REVERSE)
                else:
                    stdscr.addstr(y, 2, f" {choice} ")

            stdscr.refresh()
            key = stdscr.getch()

            if key == curses.KEY_UP and current > 0:
                current -= 1
            elif key == curses.KEY_DOWN and current < len(choices) - 1:
                current += 1
            elif key in (curses.KEY_ENTER, 10, 13):
                return choices[current]
            elif key == 27:
                return choices[default]

    import curses

    return curses.wrapper(menu)


def _select_menu_fallback(title: str, choices: list[str], default: int = 0) -> str:
    print(f"\n{title}")
    for i, choice in enumerate(choices):
        marker = ">" if i == default else " "
        print(f"  {marker} {i + 1}. {choice}")

    while True:
        result = input(f"Enter number [{default + 1}]: ").strip()
        if not result:
            return choices[default]
        try:
            idx = int(result) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        print("Invalid choice, try again.")


def generate_app_entry(
    app_id: str,
    url: str,
    author: str,
    name: str,
    categories: list[str],
    source: str,
    variant: str,
    include_prereleases: bool = False,
    verify_latest_tag: bool = False,
    allow_id_change: bool = False,
    app_name_override: str | None = None,
    url_override: str | None = None,
) -> dict:
    settings: dict[str, object] = {}
    if "Track Only" in categories:
        settings["trackOnly"] = True
    if include_prereleases:
        settings["includePrereleases"] = True
    if verify_latest_tag:
        settings["verifyLatestTag"] = True
    if app_name_override:
        settings["appName"] = app_name_override

    app = {
        "id": app_id,
        "url": url,
        "author": author,
        "name": name,
        "preferredApkIndex": 0,
        "additionalSettings": settings,
        "categories": categories,
        "allowIdChange": allow_id_change,
        "overrideSource": source,
    }

    meta = {}
    if variant == "Standard only":
        meta["includeInDualScreen"] = False
    elif variant == "Dual-screen only":
        meta["includeInStandard"] = False
    elif variant == "README only":
        meta["excludeFromExport"] = True

    if app_name_override:
        meta["nameOverride"] = app_name_override
    if url_override:
        meta["urlOverride"] = url_override

    if meta:
        app["meta"] = meta

    return app


def main() -> int:
    print("=" * 50)
    print("  Add New App to Obtainium Emulation Pack")
    print("=" * 50)

    # Get URL first - we can auto-detect a lot from it
    url = prompt("\nApp URL (GitHub/GitLab/etc.)")
    if not url:
        print("URL is required.")
        return 1

    # Detect source
    source = detect_source(url)
    if source:
        print(f"  Detected source: {source}")
    else:
        source = prompt("Source type", "GitHub")

    # Try to extract info from GitHub URL
    author = ""
    name = ""
    github_info = extract_github_info(url)
    if github_info:
        author, repo_name = github_info
        # Clean up name (replace hyphens with spaces, title case)
        name = repo_name.replace("-", " ").replace("_", " ").title()
        print(f"  Detected author: {author}")
        print(f"  Detected name: {name}")

    # Confirm or override detected values
    author = prompt("Author", author)
    name = prompt("App name", name)

    # App ID
    app_id = prompt("Android package ID (e.g., com.example.app)")
    if not app_id:
        print("Package ID is required.")
        return 1

    # Category - interactive menu
    category = select_menu("Select category:", CATEGORIES)
    print(f"  Selected: {category}")

    # Variant - interactive menu
    variant = select_menu("Include in which release(s):", VARIANT_OPTIONS)
    print(f"  Selected: {variant}")

    # Pre-releases
    include_prereleases = prompt_yes_no("Include pre-releases?", False)
    print(f"  Include pre-releases: {'Yes' if include_prereleases else 'No'}")

    # Verify latest tag
    verify_latest_tag = prompt_yes_no("Verify latest tag?", False)
    print(f"  Verify latest tag: {'Yes' if verify_latest_tag else 'No'}")

    # Allow ID change
    allow_id_change = prompt_yes_no("Allow ID change?", False)
    print(f"  Allow ID change: {'Yes' if allow_id_change else 'No'}")

    # Optional overrides
    print("")
    app_name_override = input(
        "App name override - leave blank to skip (sets display name in both Obtainium & README): "
    ).strip()
    if app_name_override:
        print(f"  Will set additionalSettings.appName and meta.nameOverride")

    url_override = input("Homepage URL override - leave blank to skip: ").strip()

    # Generate the entry
    app_entry = generate_app_entry(
        app_id=app_id,
        url=url,
        author=author,
        name=name,
        categories=[category],
        source=source,
        variant=variant,
        include_prereleases=include_prereleases,
        verify_latest_tag=verify_latest_tag,
        allow_id_change=allow_id_change,
        app_name_override=app_name_override or None,
        url_override=url_override or None,
    )

    # Show preview
    print("\n" + "=" * 50)
    print("  Generated Entry Preview")
    print("=" * 50)
    print(json.dumps(app_entry, indent=2))

    # Confirm and save
    if not prompt_yes_no("\nAdd this app to applications.json?", True):
        print("Cancelled.")
        return 0

    # Load existing file
    apps_file = Path("src/applications.json")
    if not apps_file.exists():
        print(f"Error: {apps_file} not found. Run from repo root.")
        return 1

    with open(apps_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check for duplicate ID
    existing_ids = {app["id"] for app in data.get("apps", [])}
    if app_id in existing_ids:
        print(f"\nWarning: App with ID '{app_id}' already exists!")
        if not prompt_yes_no("Add anyway?", False):
            print("Cancelled.")
            return 0

    # Add the new app
    data["apps"].append(app_entry)

    # Write back
    with open(apps_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nApp added to {apps_file}")

    # Offer to live-test the new app config
    if prompt_yes_no("\nRun live test on this app?", True):
        load_dotenv()
        # Import here to avoid circular deps and keep startup fast
        from importlib import import_module

        test_mod = import_module("test-apps")
        print()
        result = test_mod.test_app(app_entry)
        test_mod.print_result(result, verbose=True)
        if not result.passed:
            print("\nThe app config failed the live test.")
            print("The entry has been saved - you may want to fix the config and re-test.")
        print()

    print("Next steps:")
    print("  1. Run 'just build' to regenerate all files")
    print("  2. Review the diff before committing")

    return 0


if __name__ == "__main__":
    sys.exit(main())
