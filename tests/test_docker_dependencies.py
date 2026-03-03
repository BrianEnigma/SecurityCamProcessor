"""Property-based test for Docker image pip dependency installation."""

import os
import re
import subprocess

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQUIREMENTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "requirements.txt"
)
DOCKER_IMAGE_NAME = os.environ.get("DOCKER_IMAGE_NAME", "securitycam-processor")


def _parse_requirements(path: str) -> list[str]:
    """Return normalised pip package names from a requirements.txt file."""
    packages: list[str] = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip version specifiers (>=, ==, ~=, etc.)
            name = re.split(r"[><=!~;]", line)[0].strip()
            if name:
                packages.append(name)
    return packages


PACKAGES = _parse_requirements(REQUIREMENTS_PATH)


def _image_exists(image: str) -> bool:
    """Return True if the Docker image is available locally."""
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------

# Feature: docker-containerization, Property 1: All pip dependencies are installed in the image
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(data=st.data())
def test_all_pip_dependencies_installed_in_image(data: st.DataObject) -> None:
    """Property 1: For any package listed in requirements.txt, running
    ``pip show <package>`` inside the built container image succeeds
    (exit code 0), confirming the package is installed.

    Validates: Requirements 1.2
    """
    assert PACKAGES, "requirements.txt must contain at least one package"
    assert _image_exists(DOCKER_IMAGE_NAME), (
        f"Docker image '{DOCKER_IMAGE_NAME}' not found. "
        "Run 'make docker-build' first."
    )

    package = data.draw(st.sampled_from(PACKAGES), label="package")

    result = subprocess.run(
        [
            "docker", "run", "--rm", "--entrypoint", "pip",
            DOCKER_IMAGE_NAME, "show", package,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        f"pip show {package!r} failed inside the container "
        f"(exit code {result.returncode}).\n"
        f"stderr: {result.stderr.strip()}"
    )
