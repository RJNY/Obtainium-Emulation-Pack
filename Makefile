.PHONY: help all readme validate add-app normalize publish publish/dry-run publish/from-file
default: help

help: # Show help for each of the makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; \
		do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------

add-app: # Interactive CLI to add a new app
	@python scripts/add-app.py

validate: # Validate applications.json for errors
	@python scripts/validate-json.py src/applications.json

normalize: # Normalize key order and add missing defaults in applications.json
	@python scripts/normalize-json.py src/applications.json

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

release: validate normalize readme minify minify-dual-screen # Run all Make targets related to cutting a release.

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
		./pages/init.md \
		./pages/table.md \
		./pages/faq.md \
		./pages/development.md

links: # Generate links for all obtainium packages
	@python scripts/generate-obtainium-urls.py src/applications.json > scripts/links.md

# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

publish: # Tag, push, and create a GitHub release (opens $EDITOR for notes)
	@python scripts/release.py

publish/dry-run: # Preview release notes as a markdown file without publishing
	@python scripts/release.py --dry-run

publish/from-file: # Publish using a previously edited release notes file (e.g. from publish-dry)
	@python scripts/release.py --notes-file $(FILE)
