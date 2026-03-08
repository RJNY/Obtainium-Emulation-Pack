import 'utility.just'

[private]
default:
    @echo '{{YELLOW}}Tip:{{NORMAL}} Recipes with {{BOLD}}*args{{NORMAL}} accept {{BOLD}}-h{{NORMAL}} for help.'
    @just --list

# Interactive CLI to add a new app
[group('CLI Tools')]
add-app:
    @python scripts/add-app.py

# Test, validate, normalize, and generate all output files
[group('Release')]
build: test validate normalize generate

# Tag, push, and create a GitHub release
[group('Release')]
release *args:
    @python scripts/release.py {{ args }}

# Validate applications.json for errors (structure, regex syntax, source types)
[group('Formatting')]
validate:
    @python scripts/validate-json.py src/applications.json

# Normalize key order and add missing defaults in applications.json
[group('Formatting')]
normalize:
    @python scripts/normalize-json.py src/applications.json

# Live-test app configs
test *args:
    @python scripts/test-apps.py {{ args }}

# Dry-run the scheduled test workflow (no issues created)
test-cron *args:
    @{{ if args == "-h" { "python scripts/test-apps.py -h" } else if args == "--help" { "python scripts/test-apps.py -h" } else { "python scripts/test-apps.py --json " + args + " > /tmp/test-results.json && python scripts/process-test-results.py /tmp/test-results.json --dry-run --run-url local" } }}

# Type text into the focused input field on a connected Android device
[group('ADB')]
adb-type text:
    @adb shell input text '{{ text }}'

# Take a screenshot from the connected Android device and open it
[group('ADB')]
adb-screenshot:
    @adb exec-out screencap -p > /tmp/adb-screenshot.png && open /tmp/adb-screenshot.png

# Push a release JSON to the connected Android device's Downloads folder
[group('ADB')]
adb-push variant="json":
    @{{ if variant == "json" { "adb push obtainium-emulation-pack-latest.json /sdcard/Download/obtainium-emulation-pack-latest.json" } else if variant == "ds" { "adb push obtainium-emulation-pack-dual-screen-latest.json /sdcard/Download/obtainium-emulation-pack-dual-screen-latest.json" } else { "echo 'Unknown variant: " + variant + ". Use json (default) or ds.'; exit 1" } }}

# Generate output files
generate *args:
    @{{ if args == "help" { "just _generate-help" } else if args == "-h" { "just _generate-help" } else if args == "--help" { "just _generate-help" } else if args == "table" { "just _generate-table" } else if args == "readme" { "just _generate-readme" } else if args == "standard" { "just _generate-standard" } else if args == "dual-screen" { "just _generate-dual-screen" } else { "just _generate-all" } }}
