.DEFAULT_GOAL := test

NAME=src

ifeq ($(OS), Windows_NT)
	PYTHON_BIN = python
else
	PYTHON_BIN = python3
endif

CURRENT_PATH := $(shell pwd)
BROWSER := $(PYTHON_BIN) -c "import os,sys,webbrowser;webbrowser.open('file://' + os.path.realpath(sys.argv[1]))"

.PHONY: clean
clean: clean-pyc clean-test clean-venv clean-docs clean-install clean-mypy ## remove all build, test, coverage and Python artifacts

.PHONY: clean-pyc
clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-test
clean-test: ## remove test and coverage artifacts
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .tox/
	rm -rf .pytest_cache/
	rm -rf .cache/

.PHONY: clean-install
clean-install:
	find $(PACKAGES) -name '*.pyc' -delete
	find $(PACKAGES) -name '__pycache__' -delete
	rm -rf *.egg-info

.PHONY: clean-docs
clean-docs:
	rm -rf docs/build
	rm -rf docs/source/$(NAME)*.rst
	rm -rf docs/source/modules.rst

.PHONY: clean-mypy
clean-mypy:
	rm -rf .mypy_cache

.PHONY: clean-venv
clean-venv:
	rm -rf .venv

.PHONY: install
install: ## Install all dependencies with uv
	uv sync

.PHONY: lock
lock: ## Update lock file
	uv lock

.PHONY: shell
shell: ## Activate virtual environment (print activation command)
	@echo "Run: source .venv/bin/activate"

.PHONY: ruff
ruff: ## ruff check and fix
	uv run ruff check ./$(NAME) ./tests --fix

.PHONY: ruff-format
ruff-format: ## ruff format
	uv run ruff format ./$(NAME) ./tests

.PHONY: pip-audit
pip-audit: ## checks dependencies for known security vulnerabilities
	uv run pip-audit

.PHONY: mypy
mypy: ## static type check
	uv run mypy $(NAME)

.PHONY: isort
isort: ## sorted imports
	uv run isort ./$(NAME) ./tests

.PHONY: lint
lint: ruff mypy pip-audit ## run all linters

.PHONY: format
format: isort ruff-format ## format code

.PHONY: test
test: ## run tests
	uv run pytest

.PHONY: test-unit
test-unit: ## run unit tests
	uv run pytest tests/unit/

.PHONY: test-integration
test-integration: ## run integration tests
	uv run pytest tests/integration/

.PHONY: test-contract
test-contract: ## run contract tests
	uv run pytest tests/contract/

.PHONY: run
run: ## run application
	uv run python -m src

.PHONY: doc
docs: clean-docs ## Make documentation and open it in browser
	uv run sphinx-apidoc -o docs/source/ $(NAME)
	$(MAKE) -C docs html
	ifndef CI
		$(BROWSER) docs/build/html/index.html
	endif

.PHONY: help
help: ## Show this help message and exit
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-23s\033[0m %s\n", $$1, $$2}'