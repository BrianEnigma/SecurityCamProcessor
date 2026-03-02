.PHONY: help venv test lint typecheck docs clean

VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
SRC_MODULES := main.py scanner.py metadata.py mover.py gifmaker.py summarizer.py tagger.py

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

venv: ## Create virtual environment and install dependencies
	bash setup_venv.sh

test: ## Run tests with pytest
	$(PYTHON) -m pytest tests/ -v

lint: ## Run flake8 linting
	$(PYTHON) -m flake8 $(SRC_MODULES) tests/

typecheck: ## Run mypy type checking
	$(PYTHON) -m mypy $(SRC_MODULES)

docs: ## Generate HTML documentation with pydoc
	mkdir -p docs
	@for mod in $(basename $(SRC_MODULES)); do \
		$(PYTHON) -m pydoc -w $$mod; \
		mv $$mod.html docs/ 2>/dev/null || true; \
	done
	@echo "Docs generated in docs/"

clean: ## Remove generated artifacts
	rm -rf docs/ __pycache__ tests/__pycache__ .pytest_cache .mypy_cache
