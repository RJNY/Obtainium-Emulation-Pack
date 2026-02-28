#!/usr/bin/env python3
"""Process test-apps.py JSON output and manage GitHub issues.

Creates issues for newly failing apps, closes issues for recovered apps.
Designed to run in GitHub Actions as part of the scheduled test workflow.
"""

import argparse
import json
import subprocess
import sys
from typing import Any

from help_formatter import StyledHelpFormatter

ISSUE_LABEL = "automated-test-failure"
TITLE_PREFIX = "[Automated Test Failure]"


def _run_gh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )


def _parse_gh_json(result: subprocess.CompletedProcess) -> list | None:
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _ensure_label_exists() -> None:
    result = _run_gh(["label", "list", "--search", ISSUE_LABEL, "--json", "name"])
    labels = _parse_gh_json(result)
    if labels is None:
        _run_gh([
            "label", "create", ISSUE_LABEL,
            "--description", "Automatically created when a scheduled app test fails",
            "--color", "d93f0b",
        ])
        return
    if not any(label["name"] == ISSUE_LABEL for label in labels):
        _run_gh([
            "label", "create", ISSUE_LABEL,
            "--description", "Automatically created when a scheduled app test fails",
            "--color", "d93f0b",
        ])


def _find_open_issue(app_name: str) -> int | None:
    """Search for an open issue matching this app. Returns issue number or None."""
    search_title = f"{TITLE_PREFIX} {app_name}"
    result = _run_gh([
        "issue", "list",
        "--label", ISSUE_LABEL,
        "--state", "open",
        "--search", f"{search_title} in:title",
        "--json", "number,title",
    ])
    issues = _parse_gh_json(result)
    if issues is None:
        return None
    for issue in issues:
        if app_name in issue.get("title", ""):
            return issue["number"]
    return None


def _create_issue(app: dict[str, Any], run_url: str) -> None:
    title = f"{TITLE_PREFIX} {app['app_name']}"
    body = (
        f"The scheduled test run detected a failure for **{app['app_name']}**.\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| App ID | `{app['app_id']}` |\n"
        f"| Source | {app['source']} |\n"
        f"| URL | {app['url']} |\n"
        f"| Error | {app.get('error', 'unknown')} |\n\n"
    )
    if app.get("warnings"):
        body += "**Warnings:**\n"
        for w in app["warnings"]:
            body += f"- {w}\n"
        body += "\n"
    body += f"[Workflow run]({run_url})\n"

    _run_gh([
        "issue", "create",
        "--title", title,
        "--body", body,
        "--label", ISSUE_LABEL,
    ])
    print(f"  Created issue: {title}")


def _close_issue(issue_number: int, app_name: str, run_url: str) -> None:
    comment = (
        f"**{app_name}** is passing again in the latest scheduled test run.\n\n"
        f"[Workflow run]({run_url})"
    )
    _run_gh(["issue", "close", str(issue_number), "--comment", comment])
    print(f"  Closed issue #{issue_number}: {app_name} recovered")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process test results JSON and manage GitHub issues.",
        formatter_class=StyledHelpFormatter,
    )
    parser.add_argument(
        "results_file",
        help="Path to test-results.json from test-apps.py --json",
    )
    parser.add_argument(
        "--run-url",
        default="",
        help="URL of the GitHub Actions workflow run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without creating or closing issues",
    )
    args = parser.parse_args()

    try:
        with open(args.results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading results file: {e}")
        return 1

    if "error" in data:
        print(f"Test run error: {data['error']}")
        return 1

    results = data.get("results", [])
    if not results:
        print("No test results to process.")
        return 0

    dry_run = args.dry_run

    if dry_run:
        print("DRY RUN: no issues will be created or closed\n")
    else:
        _ensure_label_exists()

    failed = [r for r in results if not r["passed"]]
    passed = [r for r in results if r["passed"]]

    summary = data.get("summary", {})
    print(
        f"Processing {summary.get('total', len(results))} results: "
        f"{summary.get('passed', len(passed))} passed, "
        f"{summary.get('failed', len(failed))} failed"
    )

    for app in failed:
        if dry_run:
            print(f"  Would create issue: {TITLE_PREFIX} {app['app_name']}")
            print(f"    Error: {app.get('error', 'unknown')}")
        else:
            existing = _find_open_issue(app["app_name"])
            if existing:
                print(f"  Skipped {app['app_name']}: open issue #{existing} already exists")
            else:
                _create_issue(app, args.run_url)

    for app in passed:
        if dry_run:
            print(f"  Would check/close issue for: {app['app_name']} (passing)")
        else:
            existing = _find_open_issue(app["app_name"])
            if existing:
                _close_issue(existing, app["app_name"], args.run_url)

    return 0


if __name__ == "__main__":
    sys.exit(main())
