# Makefile for easy development workflows.
# Note GitHub Actions call uv directly, not this Makefile.

.DEFAULT_GOAL := help

SRC_PATHS := src tests recipes
DOC_PATHS := README.md CLAUDE.md AGENTS.md openspec/

ifeq ($(shell uname),Darwin)
  NATIVE_LIB_NAME := libpg_query.dylib
else
  NATIVE_LIB_NAME := libpg_query.so
endif
NATIVE_LIB := src/postgast/$(NATIVE_LIB_NAME)

##@ Development

all: install lint test ## Install, lint, and test (full check)

install: ## Install dependencies
	uv sync --all-extras

build-native: ## Build libpg_query and copy into src for local dev
	$(MAKE) -C vendor/libpg_query build_shared
	cp vendor/libpg_query/$(NATIVE_LIB_NAME) $(NATIVE_LIB)

# File target: auto-build native lib when missing (used by test targets).
$(NATIVE_LIB):
	$(MAKE) build-native

fmt: ## Run autoformatters and autofixers
	uv run mdformat $(DOC_PATHS)
	uv run codespell --write-changes $(SRC_PATHS) $(DOC_PATHS)
	uv run ruff check --fix $(SRC_PATHS)
	uv run ruff format $(SRC_PATHS)

lint: fmt ## Format, then type-check (basedpyright)
	uv run basedpyright --stats $(SRC_PATHS)

test: $(NATIVE_LIB) ## Run tests
	uv run pytest -m "not fuzz"

fuzz: $(NATIVE_LIB) ## Run fuzz tests (property-based, Hypothesis)
	uv run pytest -m fuzz

coverage: $(NATIVE_LIB) ## Run tests with coverage and generate HTML report
	uv run pytest -m "not fuzz" --cov --cov-report=html --cov-report=term

proto: ## Regenerate Python protobuf bindings from vendored pg_query.proto
	uv run python -m grpc_tools.protoc --python_out=src/postgast --pyi_out=src/postgast --proto_path=vendor/libpg_query/protobuf pg_query.proto

docs: ## Build Sphinx documentation
	uv run --extra docs sphinx-build -b html docs docs/_build/html

##@ Build & Release

build: ## Build package
	uv build

##@ Maintenance

upgrade: ## Upgrade all dependencies
	uv sync --upgrade --all-extras --dev

clean: ## Remove build artifacts, caches, .venv
	-rm -rf dist/
	-rm -rf *.egg-info/
	-rm -rf .pytest_cache/
	-rm -rf .mypy_cache/
	-rm -rf htmlcov/
	-rm -rf docs/_build/
	-rm -f .coverage
	-rm -rf .venv/
	-rm -f $(NATIVE_LIB)
	-find . -type d -name "__pycache__" -exec rm -rf {} +

##@ Help

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } \
		/^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo

.PHONY: all install fmt lint test fuzz coverage docs build build-native proto upgrade clean help
