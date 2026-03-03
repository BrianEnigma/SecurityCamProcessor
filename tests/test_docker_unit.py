"""Unit tests for Dockerfile correctness.

These tests verify specific integration requirements for the Docker image:
- Python version >= 3.10 (Req 1.1)
- ffmpeg supports H.264 and HEVC codecs (Req 1.3, 1.4)
- Image is tagged with expected name after docker-build (Req 3.2)
- Config file mount path at /app/settings.yml (Req 2.1)
- Input/output directory mount paths at /media/input and /media/output (Req 2.2, 2.3)
"""

import os
import subprocess

import pytest


DOCKER_IMAGE_NAME = os.environ.get("DOCKER_IMAGE_NAME", "securitycam-processor")
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _image_exists(image: str) -> bool:
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
    )
    return result.returncode == 0


def _docker_run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    """Run a command inside the Docker image and return the result."""
    return subprocess.run(
        ["docker", "run", "--rm", "--entrypoint"] + cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture(autouse=True)
def _require_image():
    """Skip all tests if the Docker image is not built."""
    if not _image_exists(DOCKER_IMAGE_NAME):
        pytest.skip(
            f"Docker image '{DOCKER_IMAGE_NAME}' not found. "
            "Run 'make docker-build' first."
        )


# ---------------------------------------------------------------------------
# Req 1.1 – Python version >= 3.10
# ---------------------------------------------------------------------------

class TestPythonVersion:
    def test_python_version_at_least_3_10(self):
        """The container image must include Python 3.10 or newer."""
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--entrypoint", "python",
                DOCKER_IMAGE_NAME,
                "-c",
                "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"python command failed: {result.stderr}"
        major, minor = result.stdout.strip().split(".")
        assert (int(major), int(minor)) >= (3, 10), (
            f"Expected Python >= 3.10, got {major}.{minor}"
        )


# ---------------------------------------------------------------------------
# Req 1.3, 1.4 – ffmpeg H.264 and HEVC codec support
# ---------------------------------------------------------------------------

class TestFfmpegCodecs:
    def _get_ffmpeg_codecs(self) -> str:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--entrypoint", "ffmpeg",
                DOCKER_IMAGE_NAME,
                "-codecs",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"ffmpeg -codecs failed: {result.stderr}"
        return result.stdout

    def test_ffmpeg_supports_h264(self):
        """ffmpeg in the image must support H.264 decoding and encoding."""
        codecs = self._get_ffmpeg_codecs()
        assert "h264" in codecs.lower(), "H.264 codec not found in ffmpeg output"

    def test_ffmpeg_supports_hevc(self):
        """ffmpeg in the image must support HEVC (H.265) decoding and encoding."""
        codecs = self._get_ffmpeg_codecs()
        assert "hevc" in codecs.lower() or "h265" in codecs.lower(), (
            "HEVC/H.265 codec not found in ffmpeg output"
        )


# ---------------------------------------------------------------------------
# Req 3.2 – Image tagged with expected name
# ---------------------------------------------------------------------------

class TestImageTag:
    def test_image_tagged_with_expected_name(self):
        """After docker-build, the image must be tagged with the expected name."""
        result = subprocess.run(
            ["docker", "image", "inspect", DOCKER_IMAGE_NAME],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Image '{DOCKER_IMAGE_NAME}' not found. "
            "Expected it to be tagged after 'make docker-build'."
        )


# ---------------------------------------------------------------------------
# Req 2.1 – Config file mount path
# ---------------------------------------------------------------------------

class TestConfigMount:
    def test_config_mount_path_in_makefile(self):
        """The docker-run target must mount the config file to /app/settings.yml."""
        makefile_path = os.path.join(PROJECT_ROOT, "Makefile")
        with open(makefile_path) as f:
            content = f.read()
        assert "/app/settings.yml" in content, (
            "Makefile docker-run target does not mount config to /app/settings.yml"
        )


# ---------------------------------------------------------------------------
# Req 2.2, 2.3 – Input/output directory mount paths
# ---------------------------------------------------------------------------

class TestMediaMounts:
    def test_input_mount_path_in_makefile(self):
        """The docker-run target must mount the input directory to /media/input."""
        makefile_path = os.path.join(PROJECT_ROOT, "Makefile")
        with open(makefile_path) as f:
            content = f.read()
        assert "/media/input" in content, (
            "Makefile docker-run target does not mount input dir to /media/input"
        )

    def test_output_mount_path_in_makefile(self):
        """The docker-run target must mount the output directory to /media/output."""
        makefile_path = os.path.join(PROJECT_ROOT, "Makefile")
        with open(makefile_path) as f:
            content = f.read()
        assert "/media/output" in content, (
            "Makefile docker-run target does not mount output dir to /media/output"
        )
