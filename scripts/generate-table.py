import json
import urllib.parse
import sys


def make_obtainium_link(app):
    payload = {
        "id": app["id"],
        "url": app["url"],
        "author": app["author"],
        "name": app["name"],
        "preferredApkIndex": app.get("preferredApkIndex", 0),
        "additionalSettings": app.get("additionalSettings", ""),
    }
    encoded = urllib.parse.quote(json.dumps(payload), safe="")
    return f"http://apps.obtainium.imranr.dev/redirect.html?r=obtainium://app/{encoded}"


def generate_markdown_table(apps):
    rows = []
    header = "| Application Name | Category | Add to Obtainium |"
    divider = "|------------------|----------|-------------------|"
    rows.append(header)
    rows.append(divider)

    for app in apps:
        meta = app.get("meta", {})
        if meta.get("excludeFromTable", False):
            continue

        name = app.get("name", "")
        category = ", ".join(app.get("categories", []))
        obtainium_link = make_obtainium_link(app)
        badge_md = f'<a href="{obtainium_link}">Add to Obtainium!</a>'
        rows.append(f"| {name} | {category} | {badge_md} |")

    return "\n".join(rows)


def main(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    apps = data.get("apps", [])
    markdown = generate_markdown_table(apps)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"✅ Markdown table written to {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python json_to_markdown.py input.json output.md")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
