"""Property-based test for Docker exit code propagation."""

import os
import subprocess

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DOCKER_IMAGE_NAME = os.environ.get("DOCKER_IMAGE_NAME", "securitycam-processor")
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


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

# Feature: docker-containerization, Property 4: Exit code propagation for docker targets
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(exit_code=st.integers(min_value=1, max_value=255))
def test_exit_code_propagation(exit_code: int) -> None:
    """Property 4: For any non-zero exit code produced by a command inside
    the container, the ``docker run`` invocation (used by the Makefile
    docker-test and docker-run targets) returns that same non-zero exit
    code to the caller.

    We verify this by overriding the entrypoint to ``python -c "exit(N)"``
    and asserting the subprocess exit code matches N.

    Validates: Requirements 4.2, 5.3
    """
    assert _image_exists(DOCKER_IMAGE_NAME), (
        f"Docker image '{DOCKER_IMAGE_NAME}' not found. "
        "Run 'make docker-build' first."
    )

    # Run a minimal python command that exits with the generated code.
    # This mirrors what happens when pytest or main.py fails inside the
    # docker-test / docker-run targets.
    result = subprocess.run(
        [
            "docker", "run", "--rm",
            "--entrypoint", "python",
            DOCKER_IMAGE_NAME,
            "-c", f"import sys; sys.exit({exit_code})",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == exit_code, (
        f"Expected exit code {exit_code}, got {result.returncode}. "
        f"Docker did not propagate the inner process exit code.\n"
        f"stderr: {result.stderr.strip()}"
    )
