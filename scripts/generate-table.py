import json
import urllib.parse
import sys
from collections import defaultdict


def make_obtainium_link(app):
    payload = {
        "id": app["id"],
        "url": app["url"],
        "author": app["author"],
        "name": app["name"],
        "categories": app["categories"],
        "preferredApkIndex": app.get("preferredApkIndex", 0),
        "additionalSettings": app.get("additionalSettings", ""),
    }
    encoded = urllib.parse.quote(json.dumps(payload), safe="")
    return f"http://apps.obtainium.imranr.dev/redirect.html?r=obtainium://app/{encoded}"


def get_display_name(app):
    return app.get("meta", {}).get("nameOverride") or app.get("name", "")


def get_application_url(app):
    return app.get("meta", {}).get("urlOverride") or app.get("url", "")


def generate_category_tables(apps):
    # Categorize apps
    categorized = defaultdict(list)
    for app in apps:
        categories = app.get("categories", [])
        for category in categories:
            categorized[category].append(app)

    markdown_sections = ["## Applications\n"]

    for category in sorted(categorized.keys()):
        markdown_sections.append(f"### {category}\n")
        markdown_sections.append(
            "| Application Name | Add to Obtainium | Included in export json? |"
        )
        markdown_sections.append(
            "|------------------|------------------|---------------------------|"
        )

        apps_in_category = sorted(categorized[category], key=get_display_name)

        for app in apps_in_category:
            meta = app.get("meta", {})
            if meta.get("excludeFromTable", False):
                continue

            display_name = (
                f'<a href="{get_application_url(app)}">{get_display_name(app)}</a>'
            )
            obtainium_link = make_obtainium_link(app)
            badge_md = f'<a href="{obtainium_link}">Add to Obtainium!</a>'
            include_json = (
                "❌" if app.get("meta", {}).get("excludeFromExport") else "✅"
            )

            markdown_sections.append(
                f"| {display_name} | {badge_md} | {include_json} |"
            )

        markdown_sections.append("")  # blank line between sections

    return "\n".join(markdown_sections)


def main(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    apps = data.get("apps", [])
    markdown = generate_category_tables(apps)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"✅ Category-based markdown table written to {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python json_to_markdown_by_category.py input.json output.md")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
