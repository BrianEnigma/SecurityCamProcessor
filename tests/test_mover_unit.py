"""Unit tests for Mover: remux failure handling, date_transform edge cases, output directory creation."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mover import Mover  # noqa: E402


class TestRemuxFailureHandling:
    """Tests for _remux_move when ffmpeg returns non-zero (Requirement 6.6, 6.8)."""

    def test_remux_failure_retains_source_file(self, tmp_path: Path) -> None:
        """When ffmpeg fails, the source file must NOT be deleted."""
        src = tmp_path / "input.mp4"
        dst = tmp_path / "output.mp4"
        src.write_bytes(b"fake video data")

        mover = Mover.__new__(Mover)

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("mover.subprocess.run", return_value=mock_result):
            mover._remux_move(str(src), str(dst))

        assert src.exists(), "Source file should be retained after remux failure"

    def test_remux_failure_logs_error(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """When ffmpeg fails, an error message should be printed."""
        src = tmp_path / "input.mp4"
        dst = tmp_path / "output.mp4"
        src.write_bytes(b"fake video data")

        mover = Mover.__new__(Mover)

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("mover.subprocess.run", return_value=mock_result):
            mover._remux_move(str(src), str(dst))

        captured = capsys.readouterr()
        assert "Error remuxing" in captured.out

    def test_remux_success_deletes_source_file(self, tmp_path: Path) -> None:
        """When ffmpeg succeeds, the source file must be deleted."""
        src = tmp_path / "input.mp4"
        dst = tmp_path / "output.mp4"
        src.write_bytes(b"fake video data")

        mover = Mover.__new__(Mover)

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("mover.subprocess.run", return_value=mock_result):
            mover._remux_move(str(src), str(dst))

        assert not src.exists(), "Source file should be deleted after successful remux"

    def test_remux_invokes_ffmpeg_with_correct_args(self, tmp_path: Path) -> None:
        """Verify ffmpeg is called with the expected codec copy arguments."""
        src = str(tmp_path / "input.mp4")
        dst = str(tmp_path / "output.mp4")
        (tmp_path / "input.mp4").write_bytes(b"data")

        mover = Mover.__new__(Mover)

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("mover.subprocess.run", return_value=mock_result) as mock_run:
            mover._remux_move(src, dst)

        mock_run.assert_called_once_with([
            "ffmpeg", "-i", src,
            "-vcodec", "copy", "-acodec", "copy",
            "-y", dst
        ])


class TestDateTransformEdgeCases:
    """Unit tests for _date_transform with specific examples (Requirement 6.5, 6.9)."""

    def setup_method(self) -> None:
        self.mover = Mover.__new__(Mover)

    def test_mmddyyyy_to_yyyymmdd(self) -> None:
        assert self.mover._date_transform("01152024") == "20240115"

    def test_another_mmddyyyy(self) -> None:
        assert self.mover._date_transform("12312023") == "20231231"

    def test_empty_string_passthrough(self) -> None:
        assert self.mover._date_transform("") == ""

    def test_short_string_passthrough(self) -> None:
        assert self.mover._date_transform("abc") == "abc"

    def test_seven_char_passthrough(self) -> None:
        assert self.mover._date_transform("1234567") == "1234567"

    def test_nine_char_passthrough(self) -> None:
        assert self.mover._date_transform("123456789") == "123456789"

    def test_non_numeric_eight_char_still_swaps(self) -> None:
        """Any 8-char string gets swapped, even non-numeric ones."""
        assert self.mover._date_transform("abcdefgh") == "efghabcd"


class TestOutputDirectoryCreation:
    """Tests for output directory creation during move (Requirement 6.6, 6.8)."""

    def test_creates_output_directory_on_move(self, tmp_path: Path) -> None:
        """When moving a stable file, the output subdirectory should be created."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        sub = input_dir / "01152024"
        sub.mkdir(parents=True)
        output_dir.mkdir()

        video = sub / "cam1.mp4"
        video.write_bytes(b"video data")

        mover = Mover(str(input_dir), str(output_dir), 0)
        # Pre-record file size to simulate phase 1
        mover.file_sizes[str(video)] = os.path.getsize(str(video))

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("mover.subprocess.run", return_value=mock_result):
            mover._scan_subfolder_move("01152024")

        expected_dir = output_dir / "20240115"
        assert expected_dir.is_dir(), "Output directory should be created with transformed date name"

    def test_existing_output_directory_no_error(self, tmp_path: Path) -> None:
        """If the output directory already exists, no error should occur."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        sub = input_dir / "01152024"
        sub.mkdir(parents=True)
        (output_dir / "20240115").mkdir(parents=True)

        video = sub / "cam1.mp4"
        video.write_bytes(b"video data")

        mover = Mover(str(input_dir), str(output_dir), 0)
        mover.file_sizes[str(video)] = os.path.getsize(str(video))

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("mover.subprocess.run", return_value=mock_result):
            mover._scan_subfolder_move("01152024")

        # Should not raise; directory already existed
        assert (output_dir / "20240115").is_dir()

    def test_unstable_file_not_moved(self, tmp_path: Path) -> None:
        """Files whose size changed between scans should not be moved."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        sub = input_dir / "01152024"
        sub.mkdir(parents=True)
        output_dir.mkdir()

        video = sub / "cam1.mp4"
        video.write_bytes(b"video data")

        mover = Mover(str(input_dir), str(output_dir), 0)
        # Record a different size to simulate file still being written
        mover.file_sizes[str(video)] = os.path.getsize(str(video)) + 100

        with patch("mover.subprocess.run") as mock_run:
            mover._scan_subfolder_move("01152024")

        mock_run.assert_not_called()
        assert video.exists(), "Unstable file should not be moved"
