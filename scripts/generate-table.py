"""Generate markdown tables for Obtainium Emulation Pack README."""

import json
import sys
from collections import defaultdict
from typing import Any

from utils import get_application_url, get_display_name, make_obtainium_link, should_include_app


def generate_category_tables(apps: list[dict[str, Any]]) -> str:
    categorized: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for app in apps:
        categories = app.get("categories", [])
        for category in categories:
            categorized[category].append(app)

    markdown_sections = ["## Applications\n"]

    for category in sorted(categorized.keys()):
        markdown_sections.append(f"### {category}\n")
        markdown_sections.append(
            "| Application Name | Add to Obtainium | Included in export json? | Included in DS json? |"
        )
        markdown_sections.append(
            "|------------------|------------------|---------------------------|----------------------|"
        )

        apps_in_category = sorted(
            categorized[category], key=lambda app: get_display_name(app).lower()
        )

        for app in apps_in_category:
            meta = app.get("meta", {})
            if meta.get("excludeFromTable", False):
                continue

            display_name = (
                f'<a href="{get_application_url(app)}">{get_display_name(app)}</a>'
            )
            obtainium_link = make_obtainium_link(app)
            badge_md = f'<a href="{obtainium_link}">Add to Obtainium!</a>'
            include_standard = "✅" if should_include_app(app, "standard") else "❌"
            include_dual_screen = (
                "✅" if should_include_app(app, "dual-screen") else "❌"
            )

            markdown_sections.append(
                f"| {display_name} | {badge_md} | {include_standard} | {include_dual_screen} |"
            )

        markdown_sections.append("")  # blank line between sections

    return "\n".join(markdown_sections)


def main(input_file: str, output_file: str) -> None:
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    apps = data.get("apps", [])
    markdown = generate_category_tables(apps)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Category-based markdown table written to {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate-table.py input.json output.md")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
