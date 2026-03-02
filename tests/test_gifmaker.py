"""Property-based and unit tests for GifMaker plugin."""

import os
import sys
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import patch

# Add parent directory to path so we can import gifmaker
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gifmaker import GifMaker  # noqa: E402


# Strategy for base filenames without extension
base_names = st.from_regex(r"[A-Za-z][A-Za-z0-9_\-]{0,29}", fullmatch=True)

# Strategy for video extensions
video_extensions = st.sampled_from([".mp4", ".avi", ".mkv", ".mov"])


def _make_gifmaker() -> GifMaker:
    """Create a GifMaker instance with convert check bypassed."""
    with patch.object(GifMaker, "_is_convert_present", return_value=True):
        return GifMaker()


# Feature: ruby-to-python-rewrite, Property 6: Needs-processing detects missing output files (GIF variant)
@settings(max_examples=100)
@given(base=base_names, ext=video_extensions)
def test_needs_processing_detects_missing_gif(base: str, ext: str) -> None:
    """Property 6 (GIF variant): For any input file path, needs_processing
    returns True if and only if the corresponding .gif file does not exist.

    Validates: Requirements 2.1
    """
    gm = _make_gifmaker()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = os.path.join(tmpdir, base + ext)
        gif_file = os.path.join(tmpdir, base + ".gif")

        # Case 1: GIF does not exist → needs_processing returns True
        assert gm.needs_processing(input_file) is True, (
            f"needs_processing should return True when {gif_file} does not exist"
        )

        # Case 2: GIF exists → needs_processing returns False
        with open(gif_file, "wb") as f:
            f.write(b"GIF89a")
        assert gm.needs_processing(input_file) is False, (
            f"needs_processing should return False when {gif_file} exists"
        )

        # Case 3: Remove GIF → needs_processing returns True again
        os.remove(gif_file)
        assert gm.needs_processing(input_file) is True, (
            "needs_processing should return True after GIF is removed"
        )

# --- Unit tests for GifMaker (Task 5.3) ---
# Requirements: 2.5, 2.6, 2.7


class TestGifMakerConvertPresence:
    """Test ImageMagick convert availability check (Requirement 2.5)."""

    def test_init_raises_when_convert_missing(self) -> None:
        """GifMaker.__init__ raises RuntimeError when convert is not found."""
        with patch("gifmaker.subprocess.run") as mock_run:
            mock_run.return_value = type(
                "Result", (), {"returncode": 1, "stdout": b""}
            )()
            try:
                GifMaker()
                assert False, "Expected RuntimeError"
            except RuntimeError as e:
                assert "convert" in str(e).lower()

    def test_init_succeeds_when_convert_present(self) -> None:
        """GifMaker.__init__ succeeds when convert is found."""
        with patch("gifmaker.subprocess.run") as mock_run:
            mock_run.return_value = type(
                "Result", (), {"returncode": 0, "stdout": b"/usr/bin/convert\n"}
            )()
            gm = GifMaker()
            assert gm is not None


class TestGifMakerSkipBehavior:
    """Test callback skip conditions (Requirements 2.6, 2.7)."""

    def test_skip_when_input_file_missing(self) -> None:
        """callback should return without error when input file doesn't exist (Req 2.6)."""
        gm = _make_gifmaker()
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_input = os.path.join(tmpdir, "nonexistent.mp4")
            # Should not raise, should not create any output
            gm.callback(missing_input, [])
            gif_path = os.path.join(tmpdir, "nonexistent.gif")
            assert not os.path.exists(gif_path)

    def test_skip_when_output_gif_exists(self) -> None:
        """callback should skip when output GIF already exists (Req 2.7)."""
        gm = _make_gifmaker()
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "Camera-120000-120010.mp4")
            gif_file = os.path.join(tmpdir, "Camera-120000-120010.gif")

            # Create both input and output files
            with open(input_file, "wb") as f:
                f.write(b"\x00" * 10)
            with open(gif_file, "wb") as f:
                f.write(b"GIF89a")

            # Patch _convert_frames to detect if it gets called
            with patch.object(gm, "_convert_frames") as mock_convert:
                gm.callback(input_file, ["/tmp/frame1.jpg"])
                mock_convert.assert_not_called()

    def test_skip_when_input_missing_does_not_call_convert(self) -> None:
        """callback should not invoke convert/gifsicle when input is missing (Req 2.6)."""
        gm = _make_gifmaker()
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_input = os.path.join(tmpdir, "gone.mp4")
            with patch.object(gm, "_convert_frames") as mock_convert, \
                 patch.object(gm, "_build_gif") as mock_build:
                gm.callback(missing_input, ["/tmp/frame1.jpg"])
                mock_convert.assert_not_called()
                mock_build.assert_not_called()
