"""Property-based tests for Metadata extraction."""

import os
import sys

from hypothesis import given, settings
from hypothesis import strategies as st

# Add parent directory to path so we can import metadata
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from metadata import Metadata  # noqa: E402


# Strategy for valid hour/minute/second components
hours = st.integers(min_value=0, max_value=23)
minutes = st.integers(min_value=0, max_value=59)
seconds = st.integers(min_value=0, max_value=59)

# Strategy for a camera name: at least one non-digit, non-dot, non-hyphen char
camera_names = st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,19}", fullmatch=True)

# Strategy for a file extension
extensions = st.sampled_from([".mp4", ".avi", ".mkv", ".mov"])

# Strategy for an optional directory prefix
dir_prefixes = st.sampled_from([
    "",
    "/tmp/",
    "/home/user/videos/",
    "relative/path/to/",
    "/a/b/c/d/e/",
])


# Feature: ruby-to-python-rewrite, Property 1: Metadata extraction round trip
@settings(max_examples=100)
@given(
    camera=camera_names,
    h1=hours, m1=minutes, s1=seconds,
    h2=hours, m2=minutes, s2=seconds,
    ext=extensions,
    prefix=dir_prefixes,
)
def test_metadata_extraction_round_trip(
    camera: str,
    h1: int, m1: int, s1: int,
    h2: int, m2: int, s2: int,
    ext: str,
    prefix: str,
) -> None:
    """Property 1: For any valid camera filename, extract_times produces
    correct time_start, time_end, and duration. The result is identical
    regardless of directory path prefix.

    Validates: Requirements 4.1, 4.2, 4.3, 4.6
    """
    filename = f"{camera}-{h1:02d}{m1:02d}{s1:02d}-{h2:02d}{m2:02d}{s2:02d}{ext}"

    expected_start = h1 * 3600 + m1 * 60 + s1
    expected_end = h2 * 3600 + m2 * 60 + s2
    expected_duration = expected_end - expected_start
    if expected_duration < 0:
        expected_duration += 86400

    # Test without prefix
    result = Metadata.extract_times(filename)
    assert result["time_start"] == expected_start
    assert result["time_end"] == expected_end
    assert result["duration"] == expected_duration

    # Test with directory prefix — result must be identical (Req 4.6)
    result_with_prefix = Metadata.extract_times(prefix + filename)
    assert result_with_prefix == result


# Strategy for filenames that do NOT match the expected CameraName-HHMMSS-HHMMSS.ext
# pattern.  The implementation matches start via r"-\d{6}-" and end via
# r"-\d{6}\.".  We must ensure generated strings contain neither pattern.
_invalid_filename_patterns = st.one_of(
    # Empty string
    st.just(""),
    # Just an extension
    st.just(".mp4"),
    # Pure alphabetic strings — no digits or hyphens at all
    st.from_regex(r"[A-Za-z]{1,30}", fullmatch=True),
    # Digits but no hyphens at all
    st.from_regex(r"[A-Za-z0-9]{1,20}\.[a-z]{3}", fullmatch=True).filter(
        lambda s: "-" not in s
    ),
    # Hyphens but fewer than 6 consecutive digits after any hyphen
    st.from_regex(r"[A-Za-z]+-[A-Za-z]+-[A-Za-z]+\.[a-z]{3}", fullmatch=True),
    # Too few digits between hyphens (1-5 digits, never 6)
    st.from_regex(r"[A-Za-z]+-\d{1,5}-\d{1,5}[A-Za-z]+", fullmatch=True),
    # Random text with no structure
    st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz "),
        min_size=1,
        max_size=30,
    ),
)


# Feature: ruby-to-python-rewrite, Property 2: Invalid filename produces sentinel values
@settings(max_examples=100)
@given(filename=_invalid_filename_patterns)
def test_invalid_filename_produces_sentinel_values(filename: str) -> None:
    """Property 2: For any filename that does not contain two HHMMSS timestamp
    segments separated by hyphens, extract_times returns -1 for all of
    time_start, time_end, and duration.

    Validates: Requirements 4.5
    """
    result = Metadata.extract_times(filename)
    assert result["time_start"] == -1, f"time_start should be -1 for invalid filename {filename!r}"
    assert result["time_end"] == -1, f"time_end should be -1 for invalid filename {filename!r}"
    assert result["duration"] == -1, f"duration should be -1 for invalid filename {filename!r}"


# ---------------------------------------------------------------------------
# Unit tests for Metadata edge cases (Task 2.4)
# Validates: Requirements 4.4, 4.5, 4.6
# ---------------------------------------------------------------------------


class TestDayBoundaryCrossing:
    """Requirement 4.4: end time < start time adds 86400 to duration."""

    def test_near_midnight_crossing(self) -> None:
        result = Metadata.extract_times("Garage-235900-000100.mp4")
        assert result["time_start"] == 23 * 3600 + 59 * 60  # 86340
        assert result["time_end"] == 60  # 00:01:00
        assert result["duration"] == 86400 - 86340 + 60  # 120 seconds

    def test_late_to_early(self) -> None:
        result = Metadata.extract_times("Driveway-230000-010000.mp4")
        assert result["time_start"] == 23 * 3600  # 82800
        assert result["time_end"] == 1 * 3600  # 3600
        assert result["duration"] == 86400 - 82800 + 3600  # 7200

    def test_just_before_to_just_after_midnight(self) -> None:
        result = Metadata.extract_times("FrontDoor-235959-000000.mp4")
        assert result["time_start"] == 86399
        assert result["time_end"] == 0
        assert result["duration"] == 1

    def test_same_time_yields_zero_duration(self) -> None:
        result = Metadata.extract_times("Cam-120000-120000.mp4")
        assert result["duration"] == 0


class TestDirectoryPathPrefixes:
    """Requirement 4.6: operates on basename only, stripping directory prefix."""

    def test_absolute_unix_path(self) -> None:
        result = Metadata.extract_times("/home/user/videos/Garage-100000-100500.mp4")
        assert result["time_start"] == 36000
        assert result["time_end"] == 36300
        assert result["duration"] == 300

    def test_relative_path(self) -> None:
        result = Metadata.extract_times("some/relative/path/Cam-080000-080030.mp4")
        assert result["time_start"] == 28800
        assert result["time_end"] == 28830
        assert result["duration"] == 30

    def test_deeply_nested_path(self) -> None:
        result = Metadata.extract_times("/a/b/c/d/e/f/Porch-120000-120100.mp4")
        assert result["time_start"] == 43200
        assert result["time_end"] == 43260
        assert result["duration"] == 60

    def test_path_with_digits_in_directory(self) -> None:
        """Digits in directory names must not confuse the parser."""
        result = Metadata.extract_times("/recordings/20240101/Cam-140000-140010.mp4")
        assert result["time_start"] == 50400
        assert result["time_end"] == 50410
        assert result["duration"] == 10


class TestCompletelyInvalidFilenames:
    """Requirement 4.5: non-matching filenames return -1 for all fields."""

    def test_empty_string(self) -> None:
        result = Metadata.extract_times("")
        assert result == {"time_start": -1, "time_end": -1, "duration": -1}

    def test_no_timestamps(self) -> None:
        result = Metadata.extract_times("random_video.mp4")
        assert result == {"time_start": -1, "time_end": -1, "duration": -1}

    def test_only_text(self) -> None:
        result = Metadata.extract_times("hello world")
        assert result == {"time_start": -1, "time_end": -1, "duration": -1}

    def test_single_timestamp(self) -> None:
        """Only one timestamp segment — not enough for start+end."""
        result = Metadata.extract_times("Cam-120000.mp4")
        assert result["time_start"] == -1
        assert result["duration"] == -1

    def test_no_extension_dot(self) -> None:
        """Missing dot means end timestamp regex won't match."""
        result = Metadata.extract_times("Cam-120000-130000mp4")
        assert result["time_end"] == -1
        assert result["duration"] == -1
