"""Unit tests for Makefile Docker targets.

These tests verify:
- docker-debug uses --entrypoint /bin/bash (Req 6.2)
- All docker targets declared .PHONY (Req 7.3)
- Makefile variables have documented defaults (Req 7.4)
"""

import os
import re

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
MAKEFILE_PATH = os.path.join(PROJECT_ROOT, "Makefile")

DOCKER_TARGETS = ["docker-build", "docker-test", "docker-run", "docker-debug"]

EXPECTED_VARIABLES = {
    "DOCKER_IMAGE_NAME": "securitycam-processor",
    "DOCKER_CONFIG_PATH": "$(CURDIR)/settings.yml",
    "DOCKER_INPUT_DIR": "$(CURDIR)/input",
    "DOCKER_OUTPUT_DIR": "$(CURDIR)/output",
}


@pytest.fixture()
def makefile_content() -> str:
    with open(MAKEFILE_PATH) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Req 6.2 – docker-debug uses --entrypoint /bin/bash
# ---------------------------------------------------------------------------


class TestDockerDebugEntrypoint:
    def test_debug_target_uses_bash_entrypoint(self, makefile_content: str):
        """docker-debug must override the entrypoint to /bin/bash."""
        # Find the docker-debug recipe block
        match = re.search(
            r"docker-debug:.*?\n((?:\t.*\n)*)", makefile_content
        )
        assert match is not None, "docker-debug target not found in Makefile"
        recipe = match.group(1)
        assert "--entrypoint /bin/bash" in recipe or "--entrypoint=/bin/bash" in recipe, (
            "docker-debug recipe does not use --entrypoint /bin/bash"
        )


# ---------------------------------------------------------------------------
# Req 7.3 – All docker targets declared .PHONY
# ---------------------------------------------------------------------------


class TestPhonyDeclarations:
    def test_all_docker_targets_are_phony(self, makefile_content: str):
        """Every docker-* target must be declared .PHONY."""
        # Collect all tokens from .PHONY lines
        phony_tokens: set[str] = set()
        for line in makefile_content.splitlines():
            stripped = line.strip()
            if stripped.startswith(".PHONY"):
                # Extract everything after the colon
                _, _, targets = stripped.partition(":")
                phony_tokens.update(targets.split())

        for target in DOCKER_TARGETS:
            assert target in phony_tokens, (
                f"Target '{target}' is not declared .PHONY in the Makefile"
            )


# ---------------------------------------------------------------------------
# Req 7.4 – Makefile variables have documented defaults
# ---------------------------------------------------------------------------


class TestMakefileVariableDefaults:
    def test_all_docker_variables_defined_with_defaults(self, makefile_content: str):
        """Each DOCKER_* variable must be defined with its expected default."""
        for var_name, default_value in EXPECTED_VARIABLES.items():
            # Match either ?= or := assignment
            pattern = rf"^{re.escape(var_name)}\s*\?=\s*(.+)$"
            match = re.search(pattern, makefile_content, re.MULTILINE)
            assert match is not None, (
                f"Variable '{var_name}' not found with ?= assignment in Makefile"
            )
            actual = match.group(1).strip()
            assert actual == default_value, (
                f"Variable '{var_name}' default is '{actual}', expected '{default_value}'"
            )
