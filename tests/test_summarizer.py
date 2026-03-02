"""Property-based tests for Summarizer (Property 8: Duration CSS classification)."""

import json
import os
import sys
import tempfile
from io import StringIO

from hypothesis import given, settings
from hypothesis import strategies as st

# Add parent directory to path so we can import summarizer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from summarizer import (  # noqa: E402
    MAX_GAP_ERROR,
    MAX_GAP_WARN,
    MIN_DURATION_ERROR,
    MIN_DURATION_WARN,
    Summarizer,
)


def _make_json_file(tmp_dir: str, duration: int, gap: int | None) -> str:
    """Create a minimal JSON metadata file with given duration and gap values."""
    data: dict[str, object] = {
        "flagged_tags": {},
        "important_tags": {},
        "ignored_tags": {},
        "time_start": 0,
        "time_end": duration,
        "duration": duration,
        "since": gap,
    }
    path = os.path.join(tmp_dir, "TestCam-000000-000100.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


# Feature: ruby-to-python-rewrite, Property 8: Duration CSS classification
@settings(max_examples=100)
@given(
    duration=st.integers(min_value=0, max_value=300),
    gap=st.integers(min_value=-60, max_value=120),
)
def test_duration_css_classification(duration: int, gap: int) -> None:
    """Property 8: For any integer duration value, the CSS class applied should be:
    durationError if duration >= 60, durationWarning if 30 <= duration < 60,
    and no extra class if duration < 30. For any integer gap value, the CSS class
    should be: gapError if gap <= 0, gapWarning if 0 < gap <= 15, and no extra
    class if gap > 15.

    Validates: Requirements 5.5, 5.6
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        json_path = _make_json_file(tmp_dir, duration, gap)

        summarizer = Summarizer()
        buf = StringIO()
        summarizer._write_json_to_html(buf, json_path)
        html = buf.getvalue()

        # Duration CSS classification
        if duration >= MIN_DURATION_ERROR:
            assert "durationError" in html, (
                f"Expected durationError for duration={duration}"
            )
            assert "durationWarning" not in html.replace("durationError", ""), (
                f"durationWarning should not appear when durationError applies (duration={duration})"
            )
        elif duration >= MIN_DURATION_WARN:
            assert "durationWarning" in html, (
                f"Expected durationWarning for duration={duration}"
            )
            assert "durationError" not in html, (
                f"durationError should not appear for duration={duration}"
            )
        else:
            # The class="duration " still appears, but no warning/error suffix
            assert "durationWarning" not in html, (
                f"No durationWarning expected for duration={duration}"
            )
            assert "durationError" not in html, (
                f"No durationError expected for duration={duration}"
            )

        # Gap CSS classification
        # Note: when gap < 0, the implementation renders "Gap: UNDEFINED"
        # with a hardcoded gapWarning class (the gap_extra variable is not
        # used because the rendering branch requires since_val >= 0).
        if gap < 0:
            # Negative gap: UNDEFINED path, always gapWarning
            assert "gapWarning" in html, (
                f"Expected gapWarning (UNDEFINED) for negative gap={gap}"
            )
            assert "UNDEFINED" in html, (
                f"Expected UNDEFINED label for negative gap={gap}"
            )
        elif gap <= MAX_GAP_ERROR:
            assert "gapError" in html, (
                f"Expected gapError for gap={gap}"
            )
        elif gap <= MAX_GAP_WARN:
            assert "gapWarning" in html, (
                f"Expected gapWarning for gap={gap}"
            )
            assert "gapError" not in html, (
                f"gapError should not appear for gap={gap}"
            )
        else:
            assert "gapWarning" not in html, (
                f"No gapWarning expected for gap={gap}"
            )
            assert "gapError" not in html, (
                f"No gapError expected for gap={gap}"
            )


def _create_json_files(tmp_dir: str, count: int) -> list[str]:
    """Create `count` minimal JSON metadata files in tmp_dir, returning their paths."""
    paths: list[str] = []
    for i in range(count):
        data: dict[str, object] = {
            "flagged_tags": {},
            "important_tags": {},
            "ignored_tags": {},
            "time_start": 0,
            "time_end": 10,
            "duration": 10,
            "since": 5,
        }
        name = f"Cam{i:03d}-000000-000010.json"
        path = os.path.join(tmp_dir, name)
        with open(path, "w") as f:
            json.dump(data, f)
        paths.append(path)
    return paths


# Feature: ruby-to-python-rewrite, Property 9: Summarizer change detection round trip
@settings(max_examples=100)
@given(
    initial_count=st.integers(min_value=1, max_value=10),
    add_after=st.booleans(),
)
def test_summarizer_change_detection_round_trip(
    initial_count: int, add_after: bool
) -> None:
    """Property 9: After the Summarizer generates index.html and writes the JSON
    count to summarizer.txt, calling needs_processing on the same directory (with
    no changes) should return False. If a JSON file is then added or removed,
    needs_processing should return True.

    Validates: Requirements 5.1, 5.2, 5.10
    """
    from unittest.mock import patch, MagicMock

    with tempfile.TemporaryDirectory() as tmp_dir:
        json_paths = _create_json_files(tmp_dir, initial_count)
        summarizer = Summarizer()

        # Mock screencapture (os.system) and df (subprocess.run) to avoid side effects
        mock_run_result = MagicMock()
        mock_run_result.stdout = b"Filesystem  Size  Used  Avail\n/dev/disk1  500G  250G  250G\n"
        with patch("summarizer.os.system"), patch(
            "summarizer.subprocess.run", return_value=mock_run_result
        ):
            summarizer.callback(tmp_dir)

        # After callback, needs_processing should return False (no changes)
        assert not summarizer.needs_processing(tmp_dir), (
            f"needs_processing should be False after callback with {initial_count} JSON files"
        )

        # Now mutate: either add or remove a JSON file
        if add_after:
            # Add a new JSON file
            extra_data: dict[str, object] = {
                "flagged_tags": {},
                "important_tags": {},
                "ignored_tags": {},
                "time_start": 0,
                "time_end": 5,
                "duration": 5,
                "since": 2,
            }
            extra_path = os.path.join(tmp_dir, "CamExtra-000000-000005.json")
            with open(extra_path, "w") as f:
                json.dump(extra_data, f)
        else:
            # Remove the last JSON file
            os.remove(json_paths[-1])

        # After mutation, needs_processing should return True
        assert summarizer.needs_processing(tmp_dir), (
            f"needs_processing should be True after {'adding' if add_after else 'removing'} "
            f"a JSON file (was {initial_count} files)"
        )


# Feature: ruby-to-python-rewrite, Property 12: Subdirectory listing reverse-sorted with date parsing
@settings(max_examples=100)
@given(
    dir_names=st.lists(
        st.from_regex(r"[a-zA-Z0-9]{1,12}", fullmatch=True),
        min_size=1,
        max_size=10,
        unique_by=str.lower,
    ),
)
def test_subdirectory_listing_reverse_sorted(dir_names: list[str]) -> None:
    """Property 12 (part 1): For any list of subdirectory names, the Summarizer
    should list them in reverse lexicographic order.

    Validates: Requirements 5.7
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        for name in dir_names:
            os.makedirs(os.path.join(tmp_dir, name))

        summarizer = Summarizer()
        result = summarizer._read_subdirectory_list(tmp_dir)

        expected = sorted(dir_names, reverse=True)
        assert result == expected, (
            f"Expected reverse-sorted {expected}, got {result}"
        )


# Feature: ruby-to-python-rewrite, Property 12: Date parsing with day of week
@settings(max_examples=100)
@given(
    year=st.integers(min_value=2000, max_value=2099),
    month=st.integers(min_value=1, max_value=12),
    day=st.integers(min_value=1, max_value=28),
)
def test_subdirectory_date_parsing_day_of_week(
    year: int, month: int, day: int
) -> None:
    """Property 12 (part 2): For any 8-digit subdirectory name representing
    YYYYMMDD, the parsed display should include the correct day of the week.

    Validates: Requirements 5.7
    """
    from datetime import date as dt_date

    dir_name = f"{year:04d}{month:02d}{day:02d}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        os.makedirs(os.path.join(tmp_dir, dir_name))

        summarizer = Summarizer()
        buf = StringIO()
        summarizer._write_directory_to_html(buf, tmp_dir, dir_name)
        html = buf.getvalue()

        expected_date = dt_date(year, month, day)
        expected_dow = expected_date.strftime("%A")
        expected_display = f"{expected_dow} {year:04d}-{month:02d}-{day:02d}"

        assert expected_display in html, (
            f"Expected '{expected_display}' in HTML for dir '{dir_name}', got: {html}"
        )


# Feature: ruby-to-python-rewrite, Property 13: Time formatting
@settings(max_examples=100)
@given(
    seconds=st.integers(min_value=0, max_value=86399),
    include_am_pm=st.booleans(),
)
def test_time_formatting_valid(seconds: int, include_am_pm: bool) -> None:
    """Property 13: For any non-negative integer representing seconds since midnight
    (0 to 86399), format_time should produce a string in H:MM:SS format where the
    hours, minutes, and seconds correctly decompose the input, and when include_am_pm
    is True, the suffix should be 'am' for hours 0-12 and 'pm' for hours > 12.

    Validates: Requirements 5.4
    """
    summarizer = Summarizer()
    result = summarizer._format_time(seconds, include_am_pm)

    # Decompose seconds into expected components
    raw_hours = seconds // 3600
    remainder = seconds % 3600
    expected_minutes = remainder // 60
    expected_seconds = remainder % 60

    # The implementation subtracts 12 from hours > 12 for display
    if raw_hours > 12:
        display_hours = raw_hours - 12
    else:
        display_hours = raw_hours

    expected_time = f"{display_hours}:{expected_minutes:02d}:{expected_seconds:02d}"

    if include_am_pm:
        suffix = "pm" if raw_hours > 12 else "am"
        expected_time += suffix

    assert result == expected_time, (
        f"For seconds={seconds}, include_am_pm={include_am_pm}: "
        f"expected '{expected_time}', got '{result}'"
    )


# Feature: ruby-to-python-rewrite, Property 13: Time formatting (invalid inputs)
@settings(max_examples=100)
@given(
    seconds=st.one_of(
        st.integers(max_value=-1),
        st.none(),
    ),
    include_am_pm=st.booleans(),
)
def test_time_formatting_invalid(seconds: int | None, include_am_pm: bool) -> None:
    """Property 13 (negative/None): For negative inputs or None, format_time
    should return 'err:err:err'.

    Validates: Requirements 5.4
    """
    summarizer = Summarizer()
    result = summarizer._format_time(seconds, include_am_pm)
    assert result == "err:err:err", (
        f"For seconds={seconds}: expected 'err:err:err', got '{result}'"
    )
