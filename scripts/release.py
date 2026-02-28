"""Create a GitHub release with tagged JSON artifacts.

Expects `make build` to have already been run. This script only handles
the publish side: tagging, pushing, and creating the GitHub release.

Workflow:
  1. Prompt for version (suggests next based on latest tag)
  2. Detect changed apps since last tag
  3. Generate release notes with summary + app update table
  4. Open in $EDITOR for final edits
  5. Copy minified JSONs to versioned filenames
  6. Create git tag, push, and create GitHub release

Usage:
  make build            # build artifacts first
  make publish          # then publish

Requires: gh (GitHub CLI), git, python3
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from constants import GITHUB_NOREPLY_SUFFIX
from help_formatter import StyledHelpFormatter
from utils import get_application_url, get_display_name, load_dotenv, make_obtainium_link, should_include_app

REPO_ROOT = Path(__file__).resolve().parent.parent

# Release artifact paths (relative to repo root)
STANDARD_JSON = REPO_ROOT / "obtainium-emulation-pack-latest.json"
DUAL_SCREEN_JSON = REPO_ROOT / "obtainium-emulation-pack-dual-screen-latest.json"
APPLICATIONS_JSON = REPO_ROOT / "src" / "applications.json"

SEMVER_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def load_owner_emails() -> set[str]:
    raw = os.environ.get("OWNER_EMAILS", "")
    if not raw.strip():
        return set()
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


def run(
    cmd: list[str],
    capture: bool = False,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=capture,
        text=True,
        check=check,
        env=env,
    )


def check_prerequisites() -> None:
    for tool in ("gh", "git"):
        if shutil.which(tool) is None:
            print(f"Error: '{tool}' is not installed. Install it first.")
            sys.exit(1)

    result = run(["gh", "auth", "status"], capture=True, check=False, env=_gh_env())
    if result.returncode != 0:
        print("Error: gh is not authenticated. Run `gh auth login` first.")
        sys.exit(1)


def get_latest_tag() -> str | None:
    result = run(["git", "tag", "--sort=-v:refname"], capture=True, check=False)
    if result.returncode != 0:
        return None

    for line in result.stdout.strip().splitlines():
        tag = line.strip()
        if SEMVER_PATTERN.match(tag):
            return tag
    return None


def parse_semver(tag: str) -> tuple[int, int, int]:
    match = SEMVER_PATTERN.match(tag)
    if not match:
        raise ValueError(f"Invalid semver tag: {tag}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def suggest_versions(latest: str | None) -> dict[str, str]:
    if latest is None:
        return {"patch": "v0.0.1", "minor": "v0.1.0", "major": "v1.0.0"}

    major, minor, patch = parse_semver(latest)
    return {
        "patch": f"v{major}.{minor}.{patch + 1}",
        "minor": f"v{major}.{minor + 1}.0",
        "major": f"v{major + 1}.0.0",
    }


def prompt_version(latest: str | None) -> str:
    suggestions = suggest_versions(latest)

    print()
    if latest:
        print(f"Latest tag: {latest}")
    else:
        print("No existing tags found.")

    print()
    print("Suggested versions:")
    print(f"  [1] patch  - {suggestions['patch']}")
    print(f"  [2] minor  - {suggestions['minor']}")
    print(f"  [3] major  - {suggestions['major']}")
    print(f"  [4] custom")
    print()

    while True:
        choice = input("Select version [1/2/3/4]: ").strip()
        if choice == "1":
            return suggestions["patch"]
        elif choice == "2":
            return suggestions["minor"]
        elif choice == "3":
            return suggestions["major"]
        elif choice == "4":
            custom = input("Enter version (e.g. v1.2.3): ").strip()
            if not custom.startswith("v"):
                custom = f"v{custom}"
            if not SEMVER_PATTERN.match(custom):
                print(f"Invalid semver format: {custom}")
                continue
            return custom
        else:
            print("Invalid choice. Enter 1, 2, 3, or 4.")


def load_apps_from_ref(ref: str) -> dict[str, dict[str, Any]]:
    result = run(
        ["git", "show", f"{ref}:src/applications.json"],
        capture=True,
        check=False,
    )
    if result.returncode != 0:
        return {}

    data = json.loads(result.stdout)
    return {app["id"]: app for app in data.get("apps", [])}


def load_apps_from_file() -> dict[str, dict[str, Any]]:
    with open(APPLICATIONS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {app["id"]: app for app in data.get("apps", [])}


def normalize_app_for_comparison(app: dict[str, Any]) -> dict[str, Any]:
    """Parse additionalSettings and strip meta so formatting-only changes are ignored."""
    normalized = {k: v for k, v in app.items() if k != "meta"}

    settings = normalized.get("additionalSettings")
    if isinstance(settings, str):
        try:
            normalized["additionalSettings"] = json.loads(settings)
        except json.JSONDecodeError:
            pass

    return normalized


def diff_apps(
    old_apps: dict[str, dict[str, Any]],
    new_apps: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (added, changed, removed) app lists. Removed entries use the old version."""
    old_ids = set(old_apps.keys())
    new_ids = set(new_apps.keys())

    added = [new_apps[id] for id in sorted(new_ids - old_ids)]

    removed = [old_apps[id] for id in sorted(old_ids - new_ids)]

    changed = []
    for id in sorted(old_ids & new_ids):
        old_norm = normalize_app_for_comparison(old_apps[id])
        new_norm = normalize_app_for_comparison(new_apps[id])
        if json.dumps(old_norm, sort_keys=True) != json.dumps(new_norm, sort_keys=True):
            changed.append(new_apps[id])

    return added, changed, removed


# Table rendering for release notes

def make_app_table_row(app: dict[str, Any]) -> str:
    display_name = f'<a href="{get_application_url(app)}">{get_display_name(app)}</a>'
    obtainium_link = make_obtainium_link(app)
    badge = f'<a href="{obtainium_link}">Add to Obtainium!</a>'
    std = "✅" if should_include_app(app, "standard") else "❌"
    ds = "✅" if should_include_app(app, "dual-screen") else "❌"
    return f"| {display_name} | {badge} | {std} | {ds} |"


TABLE_HEADER = (
    "| Application Name | Add to Obtainium | Included in export json? | Included in DS json? |\n"
    "|------------------|------------------|---------------------------|----------------------|"
)


def generate_app_table(apps: list[dict[str, Any]], group_by_category: bool = False) -> str:
    if not apps:
        return ""

    if not group_by_category:
        lines = [TABLE_HEADER]
        for app in sorted(apps, key=lambda a: get_display_name(a).lower()):
            lines.append(make_app_table_row(app))
        return "\n".join(lines)

    # Group by category
    categorized: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for app in apps:
        for cat in app.get("categories", ["Other"]):
            categorized[cat].append(app)

    sections: list[str] = []
    for category in sorted(categorized.keys()):
        sections.append(f"### {category}\n")
        sections.append(TABLE_HEADER)
        for app in sorted(categorized[category], key=lambda a: get_display_name(a).lower()):
            sections.append(make_app_table_row(app))
        sections.append("")

    return "\n".join(sections)


def _git_log_lines(since_tag: str | None, pretty_format: str) -> list[str]:
    cmd = ["git", "log"]
    if since_tag:
        cmd.append(f"{since_tag}..HEAD")
    cmd += ["--pretty=format:" + pretty_format]

    result = run(cmd, capture=True, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return result.stdout.strip().splitlines()


def extract_github_username(email: str) -> str | None:
    if not email.endswith(GITHUB_NOREPLY_SUFFIX):
        return None
    # Noreply format: "id+username" or just "username"
    local_part = email[: -len(GITHUB_NOREPLY_SUFFIX)]
    if "+" in local_part:
        return local_part.split("+", 1)[1]
    return local_part


def format_contributor(name: str, email: str) -> str:
    username = extract_github_username(email)
    if username:
        return f"@{username}"
    return name


def get_contributors(since_tag: str | None) -> list[str]:
    owner_emails = load_owner_emails()
    seen: set[str] = set()
    contributors: list[str] = []

    for line in _git_log_lines(since_tag, "%an%x00%ae"):
        if "\x00" not in line:
            continue
        name, email = line.split("\x00", 1)
        name, email = name.strip(), email.strip()

        if email.lower() in owner_emails:
            continue

        formatted = format_contributor(name, email)
        if formatted not in seen:
            seen.add(formatted)
            contributors.append(formatted)

    return sorted(contributors, key=str.lower)


def get_commit_summaries(since_tag: str | None) -> list[str]:
    return [line.strip() for line in _git_log_lines(since_tag, "%s") if line.strip()]


def generate_release_notes(
    latest_tag: str | None,
    added: list[dict[str, Any]],
    changed: list[dict[str, Any]],
    removed: list[dict[str, Any]],
) -> str:
    lines: list[str] = []

    lines.append("## Summary\n")
    commits = get_commit_summaries(latest_tag)
    if commits:
        for msg in commits:
            if msg.startswith("Merge ") or msg.startswith("release:"):
                continue
            lines.append(f"- {msg}")
    else:
        lines.append("- ")
    lines.append("")

    contributors = get_contributors(latest_tag)
    if contributors:
        lines.append("## Contributors\n")
        lines.append("Thanks to the following people for their contributions to this release:\n")
        for contributor in contributors:
            lines.append(f"- {contributor}")
        lines.append("")

    if added:
        lines.append("## New Apps\n")
        lines.append(generate_app_table(added, group_by_category=True))
        lines.append("")

    if changed:
        lines.append("## App Updates\n")
        lines.append(generate_app_table(changed, group_by_category=False))
        lines.append("")

    if removed:
        lines.append("## Removed Apps\n")
        for app in sorted(removed, key=lambda a: get_display_name(a).lower()):
            lines.append(f"- {get_display_name(app)}")
        lines.append("")

    return "\n".join(lines)


def edit_release_notes(notes: str) -> str:
    editor = os.environ.get("EDITOR", "vim")

    with tempfile.NamedTemporaryFile(
        suffix="-release-notes.md", mode="w", delete=False, prefix="obtainium-"
    ) as f:
        f.write(notes)
        tmp_path = f.name

    print(f"\nOpening release notes in {editor}...")
    print("Edit the notes, save, and close to continue.\n")
    subprocess.run([editor, tmp_path], check=True)

    with open(tmp_path, "r") as f:
        edited = f.read().strip()
    Path(tmp_path).unlink(missing_ok=True)
    return edited


def check_working_tree_clean() -> bool:
    result = run(["git", "status", "--porcelain"], capture=True)
    return result.stdout.strip() == ""


def create_versioned_copies(version: str) -> list[Path]:
    copies: list[Path] = []

    standard_versioned = REPO_ROOT / f"obtainium-emulation-pack-{version}.json"
    dual_versioned = REPO_ROOT / f"obtainium-emulation-pack-dual-screen-{version}.json"

    shutil.copy2(STANDARD_JSON, standard_versioned)
    shutil.copy2(DUAL_SCREEN_JSON, dual_versioned)

    copies.append(standard_versioned)
    copies.append(dual_versioned)
    return copies


def create_tag(version: str) -> None:
    print(f"Creating tag {version}...")
    run(["git", "tag", version])
    print(f"Pushing tag {version} to origin...")
    run(["git", "push", "origin", version])


def _gh_env() -> dict[str, str] | None:
    """Build env for gh CLI, preferring GITHUB_TOKEN from .env over global gh auth."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return None
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    return env


def create_github_release(version: str, notes: str, assets: list[Path]) -> None:
    cmd = ["gh", "release", "create", version]

    if notes:
        cmd += ["--notes", notes]
    else:
        cmd += ["--generate-notes"]

    cmd += ["--title", version]

    for asset in assets:
        cmd.append(str(asset))

    print(f"Creating GitHub release {version}...")
    run(cmd, env=_gh_env())


def cleanup(files: list[Path]) -> None:
    for f in files:
        f.unlink(missing_ok=True)


def get_app_count(json_path: Path) -> int:
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        return len(data.get("apps", []))
    except Exception:
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a GitHub release for Obtainium Emulation Pack",
        formatter_class=StyledHelpFormatter,
    )
    parser.add_argument(
        "--version", "-v",
        help="Release version (e.g. v7.5.0). Prompts if not provided.",
    )
    parser.add_argument(
        "--notes", "-n",
        help="Release notes markdown string. Skips generation and editor.",
    )
    parser.add_argument(
        "--notes-file", "-f",
        help="Path to a file containing release notes. Skips generation and editor.",
    )
    parser.add_argument(
        "--dry-run", "--dryrun",
        action="store_true",
        help="Show what would happen without making changes.",
    )
    args = parser.parse_args()

    load_dotenv()
    check_prerequisites()

    print("Fetching tags from remote...")
    run(["git", "fetch", "--tags"])

    latest = get_latest_tag()

    # Determine version
    if args.version:
        version = args.version
        if not version.startswith("v"):
            version = f"v{version}"
        if not SEMVER_PATTERN.match(version):
            print(f"Error: Invalid semver format: {version}")
            sys.exit(1)
    else:
        version = prompt_version(latest)

    # Check if tag already exists
    result = run(["git", "tag", "-l", version], capture=True)
    if version in result.stdout.strip().splitlines():
        print(f"Error: Tag {version} already exists.")
        sys.exit(1)

    # Detect changed apps
    print("\nDetecting app changes...")
    old_apps = load_apps_from_ref(latest) if latest else {}
    new_apps = load_apps_from_file()
    added, changed, removed = diff_apps(old_apps, new_apps)

    print(f"  Added:   {len(added)}")
    print(f"  Changed: {len(changed)}")
    print(f"  Removed: {len(removed)}")

    # Determine release notes
    if args.notes_file:
        notes = Path(args.notes_file).read_text().strip()
    elif args.notes:
        notes = args.notes
    else:
        # Auto-generate and open in editor
        notes = generate_release_notes(latest, added, changed, removed)

        if args.dry_run:
            tmp_dir = REPO_ROOT / "tmp"
            tmp_dir.mkdir(exist_ok=True)
            preview_path = tmp_dir / f"release-notes-{version}.md"
            with open(preview_path, "w") as f:
                f.write(notes)
            print(f"\nRelease notes written to tmp/{preview_path.name}")
        else:
            notes = edit_release_notes(notes)

    if not notes.strip():
        print("Warning: Release notes are empty. Using auto-generated notes.")
        notes = ""

    # Dry run summary
    if args.dry_run:
        print()
        print("=== DRY RUN ===")
        print(f"  Version:     {version}")
        print(f"  Latest tag:  {latest or '(none)'}")
        print()
        print("  Would run:")
        print(f"    1. git tag {version}")
        print(f"    2. git push origin {version}")
        print(f"    3. gh release create {version} --title {version} <assets>")
        print()
        print("  Assets:")
        print(f"    - obtainium-emulation-pack-{version}.json")
        print(f"    - obtainium-emulation-pack-dual-screen-{version}.json")
        print()
        return

    # Verify artifacts exist
    for f in (STANDARD_JSON, DUAL_SCREEN_JSON):
        if not f.exists():
            print(f"Error: Expected artifact not found: {f}")
            print("Did you run `make build` first?")
            sys.exit(1)

    # Show summary before proceeding
    std_count = get_app_count(STANDARD_JSON)
    ds_count = get_app_count(DUAL_SCREEN_JSON)

    print()
    print(f"Version:        {version}")
    print(f"Standard apps:  {std_count}")
    print(f"Dual-screen:    {ds_count}")
    if notes:
        preview = notes.split("\n")[0]
        print(f"Notes preview:  {preview[:80]}{'...' if len(preview) > 80 else ''}")
    else:
        print("Notes:          (auto-generated from commits)")
    print()

    confirm = input("Proceed with release? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Aborted.")
        sys.exit(0)

    # Commit any uncommitted changes (e.g. from `make build`)
    if not check_working_tree_clean():
        print()
        print("Working tree has changes. Committing...")
        run(["git", "add", "-A"])
        run(["git", "commit", "-m", f"release: {version}"])
        run(["git", "push"])

    # Create versioned copies for upload
    versioned_copies = create_versioned_copies(version)

    try:
        create_tag(version)
        create_github_release(version, notes, versioned_copies)

        print()
        print(f"Release {version} created successfully!")
        print(f"https://github.com/RJNY/Obtainium-Emulation-Pack/releases/tag/{version}")
    finally:
        cleanup(versioned_copies)


if __name__ == "__main__":
    main()
