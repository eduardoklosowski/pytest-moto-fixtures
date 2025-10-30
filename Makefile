# Project

SRC_DIR := src
TESTS_DIR := tests
DOCS_DIR := docs
DOCS_SRC_DIR := $(DOCS_DIR)/source
DOCS_OUTPUT_DIR := $(DOCS_DIR)/build


# Build

.PHONY: build

build:
	poetry build


# Init

.PHONY: init

init:
	poetry sync --extras=pytest --with=docs


# Format

.PHONY: fmt

fmt:
	poetry run ruff check --select I001 --fix $(SRC_DIR) $(TESTS_DIR)
	poetry run ruff format $(SRC_DIR) $(TESTS_DIR)


# Lint

.PHONY: lint lint-poetry lint-ruff-format lint-ruff-check lint-mypy lint-docs

lint: lint-poetry lint-ruff-format lint-ruff-check lint-mypy lint-docs

lint-poetry:
	poetry check

lint-ruff-format:
	poetry run ruff format --diff $(SRC_DIR) $(TESTS_DIR)

lint-ruff-check:
	poetry run ruff check $(SRC_DIR) $(TESTS_DIR)

lint-mypy:
	poetry run mypy --show-error-context --pretty $(SRC_DIR) $(TESTS_DIR)

lint-docs:
ifneq ($(shell poetry run which sphinx-build),)
	poetry run sphinx-apidoc --remove-old -f -o $(DOCS_SRC_DIR)/src $(SRC_DIR)
	poetry run sphinx-build -b dummy $(DOCS_SRC_DIR) $(DOCS_OUTPUT_DIR)
endif


# Tests

.PHONY: test test-pytest test-coverage-report

test: test-pytest

test-pytest .coverage:
	poetry run coverage run -m pytest $(TESTS_DIR)
	poetry run coverage report -m

test-coverage-report: .coverage
	poetry run coverage html


# Docs

.PHONY: docs docs-serve

docs $(DOCS_DIR)/build:
	poetry run sphinx-apidoc --remove-old -f -o $(DOCS_SRC_DIR)/src $(SRC_DIR)
	(cd $(DOCS_DIR) && poetry run make html)

docs-serve: $(DOCS_DIR)/build
	poetry run python -m http.server -d $(DOCS_DIR)/build/html 8010


# Clean

.PHONY: clean clean-build clean-pycache clean-python-tools clean-docs clean-lock dist-clean

clean: clean-build clean-pycache clean-python-tools clean-docs

clean-build:
	rm -rf dist

clean-pycache:
	find $(SRC_DIR) $(TESTS_DIR) -name '__pycache__' -exec rm -rf {} +
	find $(SRC_DIR) $(TESTS_DIR) -type d -empty -delete

clean-python-tools:
	rm -rf .ruff_cache .mypy_cache .pytest_cache .coverage .coverage.* htmlcov

clean-docs:
	rm -rf $(DOCS_SRC_DIR)/src $(DOCS_OUTPUT_DIR)

clean-lock:
	rm -rf poetry.lock

dist-clean: clean clean-lock
	rm -rf .venv
