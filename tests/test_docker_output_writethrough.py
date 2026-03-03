"""Property test: output file write-through via bind mount (Property 3).

Feature: docker-containerization, Property 3: Output file write-through via bind mount

For any file written by a process inside the container to the /media/output
mount path, that file should appear in the corresponding host output directory
with identical content.

Validates: Requirements 2.5
"""

import os
import shutil
import subprocess
import tempfile

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

DOCKER_IMAGE_NAME = os.environ.get("DOCKER_IMAGE_NAME", "securitycam-processor")


def _image_exists(image: str) -> bool:
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
    )
    return result.returncode == 0


@pytest.fixture(autouse=True)
def _require_image():
    if not _image_exists(DOCKER_IMAGE_NAME):
        pytest.skip(
            f"Docker image '{DOCKER_IMAGE_NAME}' not found. "
            "Run 'make docker-build' first."
        )


# Strategy: safe filenames — alphanumeric with optional hyphens/underscores, plus extension
_safe_filename = st.from_regex(r"[a-zA-Z][a-zA-Z0-9_-]{0,20}\.[a-z]{1,4}", fullmatch=True)
_file_content = st.binary(min_size=0, max_size=4096)


@given(filename=_safe_filename, content=_file_content)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_output_file_write_through_via_bind_mount(filename: str, content: bytes):
    """Files written inside the container to /media/output must appear on the host."""
    host_output_dir = tempfile.mkdtemp(prefix="docker_output_")
    try:
        # Hex-encode the content so it survives shell quoting
        hex_content = content.hex()

        # Write a file inside the container using python -c
        # The container writes to /media/output/<filename>
        cmd = (
            f"import binascii, pathlib; "
            f"pathlib.Path('/media/output/{filename}').write_bytes("
            f"binascii.unhexlify('{hex_content}'))"
        )
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{host_output_dir}:/media/output",
                "--entrypoint", "python",
                DOCKER_IMAGE_NAME,
                "-c", cmd,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Container write failed: {result.stderr}"
        )

        # Verify the file appeared on the host with identical content
        host_file = os.path.join(host_output_dir, filename)
        assert os.path.isfile(host_file), (
            f"File '{filename}' not found on host after container write"
        )
        actual = open(host_file, "rb").read()
        assert actual == content, (
            f"Content mismatch for '{filename}': "
            f"expected {len(content)} bytes, got {len(actual)} bytes"
        )
    finally:
        shutil.rmtree(host_output_dir, ignore_errors=True)
