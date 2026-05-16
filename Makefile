# meta-data-mcp Makefile.
#
# Thin wrappers around the most-frequently-typed commands so a
# half-remembered shell history doesn't become a footgun. See each
# target's underlying invocation for the real source of truth.

.PHONY: help test test-smoke lint format check pr-check

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

test: ## Run the regular test suite (excludes live + smoke).
	uv run pytest tests/ --ignore=tests/live --ignore=tests/smoke

test-smoke: ## Run the headless-browser smoke tests (requires the smoke dep group).
	uv run pytest -m smoke tests/smoke/ -v

lint: ## Run ruff check + format check.
	uv run ruff check .
	uv run ruff format --check .

format: ## Apply ruff format in-place.
	uv run ruff format .

check: lint test ## Lint + test (the local pre-merge smoke).

pr-check: ## Run the merge gate against a PR. Usage: make pr-check N=<pr_number>
	@if [ -z "$(N)" ]; then \
		echo "usage: make pr-check N=<pr_number>" >&2; \
		exit 2; \
	fi
	@scripts/pr_check.sh "$(N)"
