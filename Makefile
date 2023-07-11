.DEFAULT_GOAL := test

NAME=src

ifeq ($(OS), Windows_NT)
 VENV_BIN = $(VENV_PATH)/Scripts
 PYTHON_BIN = python
else
 VENV_BIN = $(VENV_PATH)/bin
 PYTHON_BIN = python3
endif

POETRY_PATH := $(shell poetry env info --path)
CURRENT_PATH := $(shell pwd)
POETRY_PATH_BIN := $(POETRY_PATH)/bin
BROWSER := $(PYTHON) -c "import os,sys,webbrowser;webbrowser.open('file://' + os.path.realpath(sys.argv[1]))"

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

.PHONY: poetry  # A shortcut for "$(VENV_PATH)/pip-status"
poetry: ## Install (upgrade) all development requirements
 poetry install

.PHONY: shell
shell: ## poetry shell
 poetry shell  ## Activate poetry shell

.PHONY: ruff
ruff: ## ruff
 poetry run ruff check ./$(NAME)

.PHONY: bandit
bandit:  # find common security issues in code
 poetry run bandit -r ./$(NAME)

.PHONY: pip-audit
pip-audit: # checks your installed dependencies for known security vulnerabilities
 poetry run pip-audit

.PHONY: mypy
mypy: ## static type check
 poetry run mypy $(NAME)

.PHONY: isort
isort: ## sorted imports
 poetry run isort ./$(NAME) ./tests

.PHONY: lint
lint: isort ruff bandit mypy pip-audit ## lint

.PHONY: doc
docs: venv clean-docs  ## Make documentation and open it in browser
 $(VENV_BIN)/sphinx-apidoc -o docs/source/ $(NAME)
 $(VENV_ACTIVATE) && $(MAKE) -C docs html
ifndef CI
 $(BROWSER) docs/build/html/index.html
endif

.PHONY: help
help:  ## Show this help message and exit
 @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-23s\033[0m %s\n", $$1, $$2}'