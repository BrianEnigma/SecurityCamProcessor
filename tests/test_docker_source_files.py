"""Property-based test for Docker image source file presence."""

import glob
import os
import subprocess

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
DOCKER_IMAGE_NAME = os.environ.get("DOCKER_IMAGE_NAME", "securitycam-processor")


def _list_py_files() -> list[str]:
    """Return basenames of all *.py files in the project root."""
    pattern = os.path.join(PROJECT_ROOT, "*.py")
    return [os.path.basename(p) for p in sorted(glob.glob(pattern))]


PY_FILES = _list_py_files()


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

# Feature: docker-containerization, Property 2: All source files are present in the image
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(data=st.data())
def test_all_source_files_present_in_image(data: st.DataObject) -> None:
    """Property 2: For any .py file in the project root on the host,
    that file exists at /app/<filename> inside the built container image.

    Validates: Requirements 1.5
    """
    assert PY_FILES, "No .py files found in the project root"
    assert _image_exists(DOCKER_IMAGE_NAME), (
        f"Docker image '{DOCKER_IMAGE_NAME}' not found. "
        "Run 'make docker-build' first."
    )

    filename = data.draw(st.sampled_from(PY_FILES), label="py_file")

    result = subprocess.run(
        [
            "docker", "run", "--rm", "--entrypoint", "test",
            DOCKER_IMAGE_NAME, "-f", f"/app/{filename}",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        f"Source file {filename!r} not found at /app/{filename} "
        f"inside the container (exit code {result.returncode})."
    )
