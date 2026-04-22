.DEFAULT_GOAL := help

.PHONY: help install install-dev install-demo sync lint format typecheck test coverage check fix pre-commit docs docs-serve clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install package (runtime deps only)
	uv sync

install-dev: ## Install package with dev dependencies
	uv sync --group dev

install-demo: ## Install package with dev + demo dependencies
	uv sync --group dev --group demo

sync: ## Install all extras and dependency groups (for local development)
	uv sync --all-extras --all-groups

lint: ## Run ruff linter (check only)
	uv run ruff check src tests demo

format: ## Run ruff formatter (check only)
	uv run ruff format --check src tests demo

typecheck: ## Run ty type checker
	uv run ty check

test: ## Run pytest
	uv run pytest tests/ -q

coverage: ## Run pytest with coverage report
	uv run pytest tests/ -q --cov=evalwire --cov-report=term-missing --cov-fail-under=85

check: lint format typecheck test ## Run all checks (lint, format, typecheck, test)

fix: ## Auto-fix lint and format issues
	uv run ruff check --fix src tests demo
	uv run ruff format src tests demo

pre-commit: ## Run all pre-commit hooks against all files
	uv run pre-commit run --all-files

clean: ## Remove build artifacts and caches
	rm -rf dist .pytest_cache .ruff_cache site
	find . -type d -name __pycache__ -exec rm -rf {} +

docs: ## Build HTML documentation into site/
	uv run mkdocs build --strict

docs-serve: ## Serve docs locally with live reload (http://localhost:8000)
	uv run mkdocs serve
