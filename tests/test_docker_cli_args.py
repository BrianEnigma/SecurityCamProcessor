"""Property-based test for CLI argument pass-through via Docker."""

import json
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


# Strategy: generate a non-empty list of CLI-safe argument strings.
# We avoid empty strings and shell-special characters to keep the test
# focused on pass-through ordering rather than shell escaping (which is
# the caller's responsibility, not Docker's).
_arg_chars = st.sampled_from(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "-_=./:"
)
_single_arg = st.text(_arg_chars, min_size=1, max_size=30)
_arg_list = st.lists(_single_arg, min_size=1, max_size=10)


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------

# Feature: docker-containerization, Property 5: CLI argument pass-through
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(args=_arg_list)
def test_cli_argument_passthrough(args: list[str]) -> None:
    """Property 5: For any set of additional command-line arguments passed
    to the container entrypoint, all arguments are forwarded to the process
    inside the container in the same order.

    We override the entrypoint to a Python snippet that dumps ``sys.argv[1:]``
    as JSON, then verify the output matches the generated argument list.

    Validates: Requirements 5.2
    """
    assert _image_exists(DOCKER_IMAGE_NAME), (
        f"Docker image '{DOCKER_IMAGE_NAME}' not found. "
        "Run 'make docker-build' first."
    )

    # The Dockerfile ENTRYPOINT is ["python", "main.py"].
    # docker-run appends: /media/input /media/output $(ARGS)
    # We simulate the same mechanism by overriding the entrypoint to a
    # Python one-liner that prints sys.argv[1:] as JSON, then passing
    # the generated args as positional arguments.
    cmd = [
        "docker", "run", "--rm",
        "--entrypoint", "python",
        DOCKER_IMAGE_NAME,
        "-c",
        "import sys, json; print(json.dumps(sys.argv[1:]))",
        *args,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        f"Container exited with code {result.returncode}.\n"
        f"stderr: {result.stderr.strip()}"
    )

    received = json.loads(result.stdout.strip())
    assert received == args, (
        f"Arguments were not passed through in order.\n"
        f"Sent:     {args}\n"
        f"Received: {received}"
    )
