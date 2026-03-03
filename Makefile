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

# --- Docker ---

DOCKER_IMAGE_NAME ?= securitycam-processor
DOCKER_CONFIG_PATH ?= $(CURDIR)/settings.yml
DOCKER_INPUT_DIR ?= $(CURDIR)/input
DOCKER_OUTPUT_DIR ?= $(CURDIR)/output

.PHONY: docker-build docker-test docker-run docker-debug

docker-build: ## Build the Docker container image
	docker build -t $(DOCKER_IMAGE_NAME) .

docker-test: ## Run tests inside the Docker container
	docker run --rm \
		-v $(CURDIR)/tests:/app/tests:ro \
		-v $(CURDIR)/main.py:/app/main.py:ro \
		-v $(CURDIR)/scanner.py:/app/scanner.py:ro \
		-v $(CURDIR)/metadata.py:/app/metadata.py:ro \
		-v $(CURDIR)/mover.py:/app/mover.py:ro \
		-v $(CURDIR)/gifmaker.py:/app/gifmaker.py:ro \
		-v $(CURDIR)/summarizer.py:/app/summarizer.py:ro \
		-v $(CURDIR)/tagger.py:/app/tagger.py:ro \
		--entrypoint python \
		$(DOCKER_IMAGE_NAME) -m pytest tests/ -v

docker-run: ## Run the processor inside the Docker container
	docker run --rm \
		-v $(DOCKER_CONFIG_PATH):/app/settings.yml:ro \
		-v $(DOCKER_INPUT_DIR):/media/input:ro \
		-v $(DOCKER_OUTPUT_DIR):/media/output \
		$(DOCKER_IMAGE_NAME) /media/input /media/output $(ARGS)

docker-debug: ## Launch an interactive bash shell in the Docker container
	docker run --rm -it \
		-v $(DOCKER_CONFIG_PATH):/app/settings.yml:ro \
		-v $(DOCKER_INPUT_DIR):/media/input:ro \
		-v $(DOCKER_OUTPUT_DIR):/media/output \
		--entrypoint /bin/bash \
		$(DOCKER_IMAGE_NAME)
