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

# Generate output files
generate *args:
    @{{ if args == "help" { "just _generate-help" } else if args == "-h" { "just _generate-help" } else if args == "--help" { "just _generate-help" } else if args == "table" { "just _generate-table" } else if args == "readme" { "just _generate-readme" } else if args == "standard" { "just _generate-standard" } else if args == "dual-screen" { "just _generate-dual-screen" } else { "just _generate-all" } }}
