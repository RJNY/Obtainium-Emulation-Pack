.PHONY: help all readme
default: help

help: # Show help for each of the makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; \
		do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

release: readme minify # Run all Make targets related to cutting a release.

links: # Generate links for all obtainium packages
	@python scripts/generate-obtainium-urls.py src/applications.json > scripts/links.md

minify: # Obtainium historically expects a minified json. This allows humans to edit the readable and easily update the minified one.
	@python scripts/minify-json.py src/applications.json obtainium-emulation-pack-latest.json

table: # Generate a table of obtainium links for the README.
	@python scripts/generate-table.py src/applications.json ./pages/table.md

readme: table # Generate the readme file. Why? Because editing that table every change is tedious.
	@python scripts/generate-readme.py \
		./pages/init.md \
		./pages/table.md \
		./pages/faq.md \
		./pages/development.md
