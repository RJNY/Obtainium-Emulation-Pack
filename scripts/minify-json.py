import json
import sys


def minify_json(input_file, output_file):
    try:
        # Read JSON data from input file
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Filter out apps with meta.exclude_from_json = true
        if "apps" in data:
            filtered_apps = []
            for app in data["apps"]:
                meta = app.get("meta", {})
                if not meta.get("excludeFromExport", False):
                    filtered_apps.append(app)
            data["apps"] = filtered_apps

        # Minify JSON and write to output file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"), ensure_ascii=False)

        print(
            f"Minified JSON saved to {output_file} ({len(data.get('apps', []))} apps included)"
        )
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python minify_json.py input.json output.json")
    else:
        minify_json(sys.argv[1], sys.argv[2])
