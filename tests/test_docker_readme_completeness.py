"""Unit tests for README Docker documentation completeness.

These tests verify:
- README mentions Docker as a prerequisite (Req 8.1)
- README describes volume mount configuration (Req 8.3)
- README includes usage examples for all four docker targets (Req 8.4)
"""

import os

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
README_PATH = os.path.join(PROJECT_ROOT, "README.md")


@pytest.fixture()
def readme_content() -> str:
    with open(README_PATH) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Req 8.1 – README mentions Docker as a prerequisite
# ---------------------------------------------------------------------------


class TestDockerPrerequisite:
    def test_readme_mentions_docker_prerequisite(self, readme_content: str):
        """README must mention Docker as a prerequisite."""
        lower = readme_content.lower()
        assert "docker" in lower, "README does not mention Docker"
        # Check for prerequisite-related language near Docker
        assert any(
            term in lower
            for term in ["prerequisite", "must be installed", "docker engine", "docker desktop"]
        ), "README does not describe Docker as a prerequisite"


# ---------------------------------------------------------------------------
# Req 8.3 – README describes volume mount configuration
# ---------------------------------------------------------------------------


class TestVolumeMountDocs:
    def test_readme_describes_config_mount(self, readme_content: str):
        """README must describe the config file volume mount."""
        assert "/app/settings.yml" in readme_content, (
            "README does not describe config mount path /app/settings.yml"
        )

    def test_readme_describes_input_mount(self, readme_content: str):
        """README must describe the input directory volume mount."""
        assert "/media/input" in readme_content, (
            "README does not describe input mount path /media/input"
        )

    def test_readme_describes_output_mount(self, readme_content: str):
        """README must describe the output directory volume mount."""
        assert "/media/output" in readme_content, (
            "README does not describe output mount path /media/output"
        )


# ---------------------------------------------------------------------------
# Req 8.4 – README includes usage examples for all four docker targets
# ---------------------------------------------------------------------------


class TestUsageExamples:
    @pytest.mark.parametrize(
        "target",
        ["docker-build", "docker-test", "docker-run", "docker-debug"],
    )
    def test_readme_includes_usage_example(self, readme_content: str, target: str):
        """README must include a usage example for each docker Makefile target."""
        # Look for the target in a make command context
        assert f"make {target}" in readme_content, (
            f"README does not include a usage example for 'make {target}'"
        )
