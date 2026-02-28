# These targets exist for CI (GitHub Actions) only.
# For local development, use the justfile: run `just` to see all commands.

.PHONY: help validate test build normalize table readme minify minify-dual-screen
.DEFAULT_GOAL := help

help: ## Show available targets
	@echo "CI-only build targets. For local development, run 'just' to see all commands."
	@echo ""
	@grep -E '^[a-z].*:.*##' Makefile | sed 's/:.*## /\t/' | while IFS=$$'\t' read -r target desc; do \
		printf "\033[1;32m%-20s\033[0m %s\n" "$$target" "$$desc"; \
	done

validate: ## Validate applications.json for errors
	@python scripts/validate-json.py src/applications.json

test: ## Live-test all app configs resolve to downloadable APKs
	@python scripts/test-apps.py

build: validate normalize readme minify minify-dual-screen ## Build all artifacts

normalize: ## Normalize key order and add missing defaults
	@python scripts/normalize-json.py src/applications.json

table: ## Generate markdown table for the README
	@python scripts/generate-table.py src/applications.json ./pages/table.md

readme: table ## Generate the README from page sections
	@python scripts/generate-readme.py \
		./pages/header.md \
		./pages/table.md \
		./pages/faq.md \
		./pages/footer.md

minify: ## Generate standard release JSON
	@python scripts/minify-json.py src/applications.json obtainium-emulation-pack-latest.json --variant standard

minify-dual-screen: ## Generate dual-screen release JSON
	@python scripts/minify-json.py src/applications.json obtainium-emulation-pack-dual-screen-latest.json --variant dual-screen
