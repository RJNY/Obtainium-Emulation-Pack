import json
import sys
import argparse


def should_include_app(app, variant):
    """Determine if an app should be included based on variant and meta fields."""
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


def minify_json(input_file, output_file, variant="standard"):
    try:
        # Read JSON data from input file
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Filter apps based on variant
        if "apps" in data:
            filtered_apps = []
            for app in data["apps"]:
                if should_include_app(app, variant):
                    # Remove meta key from export
                    app_copy = app.copy()
                    app_copy.pop("meta", None)
                    filtered_apps.append(app_copy)
            data["apps"] = filtered_apps

        # Minify JSON and write to output file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"), ensure_ascii=False)

        variant_label = f" ({variant})" if variant != "standard" else ""
        print(
            f"Minified JSON{variant_label} saved to {output_file} ({len(data.get('apps', []))} apps included)"
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Minify and filter Obtainium JSON based on variant"
    )
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument("output", help="Output JSON file")
    parser.add_argument(
        "--variant",
        choices=["standard", "dual-screen"],
        default="standard",
        help="Variant to build (default: standard)",
    )

    args = parser.parse_args()
    minify_json(args.input, args.output, args.variant)
