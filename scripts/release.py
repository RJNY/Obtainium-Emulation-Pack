"""Create a GitHub release with tagged JSON artifacts.

Expects `make release` to have already been run. This script only handles
the publish side: tagging, pushing, and creating the GitHub release.

Workflow:
  1. Prompt for version (suggests next based on latest tag)
  2. Copy minified JSONs to versioned filenames
  3. Create git tag
  4. Push tag to origin
  5. Create GitHub release with `gh release create`
  6. Clean up versioned copies

Usage:
  make release          # build artifacts first
  make publish          # then publish

Requires: gh (GitHub CLI), git, python3
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Release artifact paths (relative to repo root)
STANDARD_JSON = REPO_ROOT / "obtainium-emulation-pack-latest.json"
DUAL_SCREEN_JSON = REPO_ROOT / "obtainium-emulation-pack-dual-screen-latest.json"

SEMVER_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def run(cmd: list[str], capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command, optionally capturing output."""
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=capture,
        text=True,
        check=check,
    )


def check_prerequisites() -> None:
    """Verify required tools are installed."""
    for tool in ("gh", "git"):
        if shutil.which(tool) is None:
            print(f"Error: '{tool}' is not installed. Install it first.")
            sys.exit(1)

    # Verify gh is authenticated
    result = run(["gh", "auth", "status"], capture=True, check=False)
    if result.returncode != 0:
        print("Error: gh is not authenticated. Run `gh auth login` first.")
        sys.exit(1)


def get_latest_tag() -> str | None:
    """Get the most recent semver tag from git."""
    result = run(["git", "tag", "--sort=-v:refname"], capture=True, check=False)
    if result.returncode != 0:
        return None

    for line in result.stdout.strip().splitlines():
        tag = line.strip()
        if SEMVER_PATTERN.match(tag):
            return tag
    return None


def parse_semver(tag: str) -> tuple[int, int, int]:
    """Parse a semver tag into (major, minor, patch)."""
    match = SEMVER_PATTERN.match(tag)
    if not match:
        raise ValueError(f"Invalid semver tag: {tag}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def suggest_versions(latest: str | None) -> dict[str, str]:
    """Suggest next patch, minor, and major versions."""
    if latest is None:
        return {"patch": "v0.0.1", "minor": "v0.1.0", "major": "v1.0.0"}

    major, minor, patch = parse_semver(latest)
    return {
        "patch": f"v{major}.{minor}.{patch + 1}",
        "minor": f"v{major}.{minor + 1}.0",
        "major": f"v{major + 1}.0.0",
    }


def prompt_version(latest: str | None) -> str:
    """Interactively prompt for the release version."""
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


def prompt_release_notes() -> str:
    """Prompt user to write release notes, or open $EDITOR."""
    print()
    print("Release notes options:")
    print("  [1] Write inline (multi-line, end with EOF on empty line)")
    print("  [2] Open in $EDITOR")
    print("  [3] Skip (create release with auto-generated notes)")
    print()

    choice = input("Select [1/2/3]: ").strip()

    if choice == "1":
        print()
        print("Enter release notes (type a blank line to finish):")
        lines: list[str] = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        return "\n".join(lines)

    elif choice == "2":
        import os
        editor = os.environ.get("EDITOR", "vim")
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("## Summary\n\n- \n")
            tmp_path = f.name

        subprocess.run([editor, tmp_path], check=True)
        with open(tmp_path, "r") as f:
            notes = f.read().strip()
        Path(tmp_path).unlink(missing_ok=True)
        return notes

    else:
        return ""


def check_working_tree_clean() -> bool:
    """Check if the git working tree is clean."""
    result = run(["git", "status", "--porcelain"], capture=True)
    return result.stdout.strip() == ""


def create_versioned_copies(version: str) -> list[Path]:
    """Copy release JSONs to versioned filenames for upload."""
    copies: list[Path] = []

    standard_versioned = REPO_ROOT / f"obtainium-emulation-pack-{version}.json"
    dual_versioned = REPO_ROOT / f"obtainium-emulation-pack-dual-screen-{version}.json"

    shutil.copy2(STANDARD_JSON, standard_versioned)
    shutil.copy2(DUAL_SCREEN_JSON, dual_versioned)

    copies.append(standard_versioned)
    copies.append(dual_versioned)

    return copies


def create_tag(version: str) -> None:
    """Create and push a git tag."""
    print(f"Creating tag {version}...")
    run(["git", "tag", version])
    print(f"Pushing tag {version} to origin...")
    run(["git", "push", "origin", version])


def create_github_release(version: str, notes: str, assets: list[Path]) -> None:
    """Create a GitHub release via gh CLI."""
    cmd = ["gh", "release", "create", version]

    if notes:
        cmd += ["--notes", notes]
    else:
        cmd += ["--generate-notes"]

    cmd += ["--title", version]

    for asset in assets:
        cmd.append(str(asset))

    print(f"Creating GitHub release {version}...")
    run(cmd)


def cleanup(files: list[Path]) -> None:
    """Remove temporary versioned copies."""
    for f in files:
        f.unlink(missing_ok=True)


def get_app_count(json_path: Path) -> int:
    """Count apps in a release JSON file."""
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        return len(data.get("apps", []))
    except Exception:
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a GitHub release for Obtainium Emulation Pack")
    parser.add_argument("--version", "-v", help="Release version (e.g. v7.5.0). Prompts if not provided.")
    parser.add_argument("--notes", "-n", help="Release notes (markdown string). Prompts if not provided.")
    parser.add_argument("--notes-file", "-f", help="Path to a file containing release notes.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes.")
    args = parser.parse_args()

    check_prerequisites()

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

    # Determine release notes
    notes = ""
    if args.notes_file:
        notes = Path(args.notes_file).read_text().strip()
    elif args.notes:
        notes = args.notes
    elif not args.dry_run:
        notes = prompt_release_notes()

    # Dry run summary
    if args.dry_run:
        print()
        print("=== DRY RUN ===")
        print(f"  Version:     {version}")
        print(f"  Latest tag:  {latest or '(none)'}")
        print(f"  Notes:       {'(auto-generated)' if not notes else notes[:80] + '...'}")
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
            sys.exit(1)

    # Show summary before proceeding
    std_count = get_app_count(STANDARD_JSON)
    ds_count = get_app_count(DUAL_SCREEN_JSON)

    print(f"Version:        {version}")
    print(f"Standard apps:  {std_count}")
    print(f"Dual-screen:    {ds_count}")
    if notes:
        print(f"Notes preview:  {notes[:80]}{'...' if len(notes) > 80 else ''}")
    else:
        print("Notes:          (auto-generated from commits)")
    print()

    confirm = input("Proceed with release? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Aborted.")
        sys.exit(0)

    # Stage, commit any build changes if working tree is dirty
    if not check_working_tree_clean():
        print()
        print("Working tree has changes (from build). Committing...")
        run(["git", "add", "-A"])
        run(["git", "commit", "-m", f"release: {version}"])
        run(["git", "push"])

    # Create versioned copies for upload
    versioned_copies = create_versioned_copies(version)

    try:
        # Tag and release
        create_tag(version)
        create_github_release(version, notes, versioned_copies)

        print()
        print(f"Release {version} created successfully!")
        print(f"https://github.com/RJNY/Obtainium-Emulation-Pack/releases/tag/{version}")
    finally:
        # Always clean up versioned copies
        cleanup(versioned_copies)


if __name__ == "__main__":
    main()
