DEFAULT_VENV_NAME := .venv
PYTHON := $(DEFAULT_VENV_NAME)/bin/python3
PIP := $(DEFAULT_VENV_NAME)/bin/pip
MAIN := fly-in.py
DEFAULT_MAP := maps/easy/01_linear_path.txt
MAP_ORIGIN := $(origin MAP)
MAP ?= $(DEFAULT_MAP)
FLAGS ?=

.PHONY: help install run debug clean lint lint-strict

help:
	@echo "Available targets:"
	@echo "  make install      Detect or create a virtualenv and install dependencies"
	@echo "  make run          Run the project"
	@echo "  make run FLAGS=--gui  Open the GUI viewer"
	@echo "  make debug        Run the project with pdb"
	@echo "  make clean        Remove caches and temporary files"
	@echo "  make lint         Run flake8 and required mypy checks"
	@echo "  make lint-strict  Run flake8 and mypy --strict"
	@echo "  make test         Run the test program"

install:
	@set -eu; \
	find . -type d -name $(DEFAULT_VENV_NAME) -prune -exec rm -rf {} +; \
	echo "Creating clean virtual environment..."; \
	python3 -m venv --system-site-packages $(DEFAULT_VENV_NAME); \
	echo "Installing dependencies..."; \
	$(PIP) install -r requirements.txt; \
	echo "Install to virtualenv $(DEFAULT_VENV_NAME) Successful."

run:
	@set -eu; \
	if [ ! -f $(PYTHON) ]; then \
		echo "Error: no valid virtualenv found. Run 'make install' first." >&2; \
		exit 1; \
	fi; \
	if [ "$(MAP_ORIGIN)" = "undefined" ]; then \
		echo "No MAP specified; using default easy map: $(MAP)"; \
	fi; \
	$(PYTHON) "$(MAIN)" $(FLAGS) "$(MAP)"

debug:
	@set -eu; \
	if [ ! -f $(PYTHON) ]; then \
		echo "Error: no valid virtualenv found. Run 'make install' first." >&2; \
		exit 1; \
	fi; \
	$(PYTHON) -m pdb "$(MAIN)" $(FLAGS) "$(MAP)"

clean:
	@set -eu; \
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +; \
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +; \
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +; \
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +; \
	find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete; \
	find . -type f -name "uv.lock" -delete;

lint:
	@set -eu; \
	if [ ! -f $(PYTHON) ]; then \
		echo "Error: no valid virtualenv found. Run 'make install' first." >&2; \
		exit 1; \
	fi; \
	$(PYTHON) -m flake8 .; \
	$(PYTHON) -m mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	@set -eu; \
	if [ ! -f $(PYTHON) ]; then \
		echo "Error: no valid virtualenv found. Run 'make install' first." >&2; \
		exit 1; \
	fi; \
	$(PYTHON) -m flake8 .; \
	$(PYTHON) -m mypy . --strict
