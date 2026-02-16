.PHONY: help readme validate add-app normalize build publish publish-dry-run publish-from-file test test-app test-apks test-verbose
default: help

help: # Show help for each of the makefile recipes.
	@width=$$(grep -E '^[a-zA-Z0-9 -]+:.*#' Makefile | cut -f1 -d':' | awk '{print length}' | sort -rn | head -1); \
		grep -E '^[a-zA-Z0-9 -]+:.*#' Makefile | sort | while read -r l; \
		do printf "\033[1;32m%-$${width}s\033[00m  %s\n" "$$(echo $$l | cut -f 1 -d':')" "$$(echo $$l | cut -f 2- -d'#')"; done

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------

add-app: # Interactive CLI to add a new app
	@python scripts/add-app.py

validate: # Validate applications.json for errors (structure, regex syntax, source types)
	@python scripts/validate-json.py src/applications.json

normalize: # Normalize key order and add missing defaults in applications.json
	@python scripts/normalize-json.py src/applications.json

test: # Live-test that all app configs can resolve to downloadable APKs
	@python scripts/test-apps.py src/applications.json

test-app: # Live-test a single app by name (e.g. make test-app APP=Dolphin)
	@python scripts/test-apps.py src/applications.json --verbose --apks $(APP)

test-apks: # Live-test all apps and show numbered APK list for index selection
	@python scripts/test-apps.py src/applications.json --apks

test-verbose: # Live-test with APK URL details shown
	@python scripts/test-apps.py src/applications.json --verbose

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

build: validate normalize readme minify minify-dual-screen # Build all artifacts: validate, normalize, readme, and both release JSONs.

minify: # Generate standard release JSON
	@python scripts/minify-json.py src/applications.json obtainium-emulation-pack-latest.json --variant standard

minify-dual-screen: # Generate dual screen release JSON
	@python scripts/minify-json.py src/applications.json obtainium-emulation-pack-dual-screen-latest.json --variant dual-screen

# ---------------------------------------------------------------------------
# Docs
# ---------------------------------------------------------------------------

table: # Generate a table of obtainium links for the README.
	@python scripts/generate-table.py src/applications.json ./pages/table.md

readme: table # Generate the readme file. Why? Because editing that table every change is tedious.
	@python scripts/generate-readme.py \
		./pages/header.md \
		./pages/table.md \
		./pages/faq.md \
		./pages/footer.md

# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

publish: # Tag, push, and create a GitHub release (opens $EDITOR for notes)
	@python scripts/release.py

publish-dry-run: # Preview release notes as a markdown file without publishing
	@python scripts/release.py --dry-run

publish-from-file: # Publish using a previously edited release notes file (e.g. from publish-dry)
	@python scripts/release.py --notes-file $(FILE)
