"""Unit tests for Summarizer plugin (Task 8.6).

Tests HTML output structure, summarizer.txt tracking, and disk usage display.
Requirements: 5.3, 5.4, 5.8, 5.9
"""

import json
import os
import sys
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from summarizer import Summarizer  # noqa: E402


def _write_json(directory: str, name: str, data: dict[str, object]) -> str:
    """Write a JSON metadata file and return its path."""
    path = os.path.join(directory, name)
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def _sample_json_data(
    duration: int = 17,
    since: int = 120,
    time_start: int = 5923,
    time_end: int = 5940,
) -> dict[str, object]:
    """Return a representative JSON metadata dict."""
    return {
        "flagged_tags": {"person": 95, "human": 92},
        "important_tags": {"dog": 85},
        "ignored_tags": {"plant": 99},
        "time_start": time_start,
        "time_end": time_end,
        "duration": duration,
        "since": since,
    }


class TestHtmlOutputContainsRequiredElements:
    """Requirement 5.3: HTML block displays GIF thumbnail, video link, timing, tags."""

    def test_gif_thumbnail_present(self) -> None:
        """HTML should contain an img tag referencing the GIF thumbnail."""
        with tempfile.TemporaryDirectory() as tmp:
            json_path = _write_json(tmp, "Cam-120000-120017.json", _sample_json_data())
            s = Summarizer()
            buf = StringIO()
            s._write_json_to_html(buf, json_path)
            html = buf.getvalue()
            assert 'src="Cam-120000-120017.gif"' in html
            assert 'class="gif_thumbnail"' in html

    def test_video_filename_link(self) -> None:
        """HTML should contain a link to the .mp4 video file."""
        with tempfile.TemporaryDirectory() as tmp:
            json_path = _write_json(tmp, "Cam-120000-120017.json", _sample_json_data())
            s = Summarizer()
            buf = StringIO()
            s._write_json_to_html(buf, json_path)
            html = buf.getvalue()
            assert 'href="Cam-120000-120017.mp4"' in html
            assert "Cam-120000-120017.mp4" in html

    def test_timing_info_present(self) -> None:
        """HTML should contain formatted start and end times (Req 5.4)."""
        with tempfile.TemporaryDirectory() as tmp:
            # time_start=5923 => 1:38:43, time_end=5940 => 1:39:00
            json_path = _write_json(tmp, "Cam-013843-013900.json", _sample_json_data())
            s = Summarizer()
            buf = StringIO()
            s._write_json_to_html(buf, json_path)
            html = buf.getvalue()
            assert "1:38:43" in html
            assert "1:39:00" in html
            assert "timespan" in html

    def test_duration_displayed(self) -> None:
        """HTML should contain the formatted duration."""
        with tempfile.TemporaryDirectory() as tmp:
            json_path = _write_json(tmp, "Cam-000000-000017.json", _sample_json_data(duration=17))
            s = Summarizer()
            buf = StringIO()
            s._write_json_to_html(buf, json_path)
            html = buf.getvalue()
            assert 'class="duration' in html
            assert "0:00:17" in html

    def test_gap_displayed(self) -> None:
        """HTML should contain the gap since previous video."""
        with tempfile.TemporaryDirectory() as tmp:
            json_path = _write_json(tmp, "Cam-000000-000010.json", _sample_json_data(since=120))
            s = Summarizer()
            buf = StringIO()
            s._write_json_to_html(buf, json_path)
            html = buf.getvalue()
            assert "Gap:" in html
            assert "0:02:00" in html

    def test_flagged_tags_rendered(self) -> None:
        """HTML should contain flagged tags with confidence percentages."""
        with tempfile.TemporaryDirectory() as tmp:
            json_path = _write_json(tmp, "Cam-000000-000010.json", _sample_json_data())
            s = Summarizer()
            buf = StringIO()
            s._write_json_to_html(buf, json_path)
            html = buf.getvalue()
            assert "person" in html
            assert "(95%)" in html
            assert "human" in html
            assert "(92%)" in html
            assert 'class="flagged"' in html

    def test_important_tags_rendered(self) -> None:
        """HTML should contain important tags."""
        with tempfile.TemporaryDirectory() as tmp:
            json_path = _write_json(tmp, "Cam-000000-000010.json", _sample_json_data())
            s = Summarizer()
            buf = StringIO()
            s._write_json_to_html(buf, json_path)
            html = buf.getvalue()
            assert "dog" in html
            assert "(85%)" in html
            assert 'class="important"' in html

    def test_gap_undefined_for_negative_since(self) -> None:
        """HTML should show UNDEFINED when gap is negative."""
        with tempfile.TemporaryDirectory() as tmp:
            json_path = _write_json(tmp, "Cam-000000-000010.json", _sample_json_data(since=-5))
            s = Summarizer()
            buf = StringIO()
            s._write_json_to_html(buf, json_path)
            html = buf.getvalue()
            assert "UNDEFINED" in html


class TestSummarizerTxtTracking:
    """Requirements 5.8, 5.9: summarizer.txt creation and reading."""

    def _run_callback(self, tmp_dir: str, json_count: int) -> None:
        """Run summarizer callback with mocked system calls."""
        mock_run = MagicMock()
        mock_run.stdout = b"500G\t/path\n"
        with patch("summarizer.os.system"), patch(
            "summarizer.subprocess.run", return_value=mock_run
        ):
            Summarizer().callback(tmp_dir)

    def test_summarizer_txt_created_after_callback(self) -> None:
        """callback should create summarizer.txt with the JSON file count."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_json(tmp, "A.json", _sample_json_data())
            _write_json(tmp, "B.json", _sample_json_data())
            self._run_callback(tmp, 2)
            txt_path = os.path.join(tmp, "summarizer.txt")
            assert os.path.exists(txt_path)
            with open(txt_path) as f:
                assert f.read().strip() == "2"

    def test_summarizer_txt_updated_on_rerun(self) -> None:
        """Re-running callback after adding a file should update summarizer.txt."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_json(tmp, "A.json", _sample_json_data())
            self._run_callback(tmp, 1)
            with open(os.path.join(tmp, "summarizer.txt")) as f:
                assert f.read().strip() == "1"

            _write_json(tmp, "B.json", _sample_json_data())
            self._run_callback(tmp, 2)
            with open(os.path.join(tmp, "summarizer.txt")) as f:
                assert f.read().strip() == "2"

    def test_index_html_created(self) -> None:
        """callback should create index.html."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_json(tmp, "A.json", _sample_json_data())
            self._run_callback(tmp, 1)
            assert os.path.exists(os.path.join(tmp, "index.html"))

    def test_needs_processing_reads_summarizer_txt(self) -> None:
        """needs_processing should read summarizer.txt to compare counts."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_json(tmp, "A.json", _sample_json_data())
            self._run_callback(tmp, 1)
            s = Summarizer()
            # No changes — should not need processing
            assert s.needs_processing(tmp) is False
            # Manually corrupt summarizer.txt
            with open(os.path.join(tmp, "summarizer.txt"), "w") as f:
                f.write("999")
            assert s.needs_processing(tmp) is True


class TestDiskUsageDisplay:
    """Requirements 5.8, 5.9: disk usage and screenshot for subdirectories."""

    def test_du_output_in_subdirectory_html(self) -> None:
        """_write_directory_to_html should include disk usage from du command."""
        with tempfile.TemporaryDirectory() as tmp:
            subdir = "20240115"
            os.makedirs(os.path.join(tmp, subdir))
            s = Summarizer()
            mock_result = MagicMock()
            mock_result.stdout = b"4.2G\t/some/path\n"
            with patch("summarizer.subprocess.run", return_value=mock_result):
                buf = StringIO()
                s._write_directory_to_html(buf, tmp, subdir)
                html = buf.getvalue()
            assert "4.2G" in html

    def test_du_failure_shows_question_mark(self) -> None:
        """_write_directory_to_html should show '?' when du fails."""
        with tempfile.TemporaryDirectory() as tmp:
            subdir = "mydir"
            os.makedirs(os.path.join(tmp, subdir))
            s = Summarizer()
            with patch("summarizer.subprocess.run", side_effect=OSError("fail")):
                buf = StringIO()
                s._write_directory_to_html(buf, tmp, subdir)
                html = buf.getvalue()
            assert "?" in html

    def test_callback_includes_df_when_subdirs_present(self) -> None:
        """callback should include df output and screenshot when subdirectories exist (Req 5.9)."""
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "20240101"))
            _write_json(tmp, "A.json", _sample_json_data())

            mock_run = MagicMock()
            mock_run.stdout = b"Filesystem  Size  Used  Avail\n/dev/disk1  500G  250G  250G\n"
            with patch("summarizer.os.system"), patch(
                "summarizer.subprocess.run", return_value=mock_run
            ):
                Summarizer().callback(tmp)

            with open(os.path.join(tmp, "index.html")) as f:
                html = f.read()
            assert "<pre>" in html
            assert "screen.png" in html

    def test_callback_no_df_without_subdirs(self) -> None:
        """callback should not include df/screenshot when no subdirectories exist."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_json(tmp, "A.json", _sample_json_data())

            mock_run = MagicMock()
            mock_run.stdout = b"4.2G\t/path\n"
            with patch("summarizer.os.system"), patch(
                "summarizer.subprocess.run", return_value=mock_run
            ):
                Summarizer().callback(tmp)

            with open(os.path.join(tmp, "index.html")) as f:
                html = f.read()
            assert "screen.png" not in html
            assert "<pre>" not in html
