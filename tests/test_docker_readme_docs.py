"""Property-based test: README documents all Docker Makefile targets and variables."""

import os
import re

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
MAKEFILE_PATH = os.path.join(PROJECT_ROOT, "Makefile")
README_PATH = os.path.join(PROJECT_ROOT, "README.md")


def _read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _extract_docker_targets(makefile_text: str) -> list[str]:
    """Extract all docker-* target names from the Makefile."""
    # Match lines like: docker-build: ## Build the Docker container image
    return re.findall(r"^(docker-\w+)\s*:", makefile_text, re.MULTILINE)


def _extract_docker_variables(makefile_text: str) -> list[str]:
    """Extract all DOCKER_* variable names from the Makefile."""
    # Match lines like: DOCKER_IMAGE_NAME ?= securitycam-processor
    return re.findall(r"^(DOCKER_\w+)\s*\??=", makefile_text, re.MULTILINE)


# Pre-compute the lists once so Hypothesis can sample from them.
_makefile_text = _read_file(MAKEFILE_PATH)
DOCKER_TARGETS = _extract_docker_targets(_makefile_text)
DOCKER_VARIABLES = _extract_docker_variables(_makefile_text)
ALL_DOCKER_ITEMS = DOCKER_TARGETS + DOCKER_VARIABLES

assert len(DOCKER_TARGETS) > 0, "No docker-* targets found in Makefile"
assert len(DOCKER_VARIABLES) > 0, "No DOCKER_* variables found in Makefile"


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

# Feature: docker-containerization, Property 7: README documents all Docker Makefile targets and configurable variables

@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(target=st.sampled_from(DOCKER_TARGETS))
def test_readme_documents_all_docker_targets(target: str) -> None:
    """Property 7 (targets): For any docker-* target in the Makefile, the
    README contains that target name with a non-empty description.

    Validates: Requirements 8.2
    """
    readme = _read_file(README_PATH)

    assert target in readme, (
        f"Docker target '{target}' not found in README.\n"
        f"All docker targets from Makefile: {DOCKER_TARGETS}"
    )

    # Verify the target appears in a context with descriptive text (not just
    # a bare mention).  Look for the target followed by text on the same line
    # or in a table cell.
    pattern = re.compile(
        rf"{re.escape(target)}"   # target name
        r"[`\s|]*"                # optional backtick, whitespace, or pipe
        r"\S+",                   # at least one non-whitespace char after
    )
    assert pattern.search(readme), (
        f"Docker target '{target}' appears in README but has no "
        f"accompanying description text."
    )


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(variable=st.sampled_from(DOCKER_VARIABLES))
def test_readme_documents_all_docker_variables(variable: str) -> None:
    """Property 7 (variables): For any DOCKER_* variable in the Makefile, the
    README contains that variable name with a non-empty description.

    Validates: Requirements 8.5
    """
    readme = _read_file(README_PATH)

    assert variable in readme, (
        f"Docker variable '{variable}' not found in README.\n"
        f"All docker variables from Makefile: {DOCKER_VARIABLES}"
    )

    # Verify the variable appears with descriptive text nearby.
    pattern = re.compile(
        rf"{re.escape(variable)}"
        r"[`\s|]*"
        r"\S+",
    )
    assert pattern.search(readme), (
        f"Docker variable '{variable}' appears in README but has no "
        f"accompanying description text."
    )
