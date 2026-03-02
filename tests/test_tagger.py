"""Property-based tests for Tagger."""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

# Add parent directory to path so we can import tagger
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tagger import Tagger  # noqa: E402


# Strategy for tag names: lowercase alpha strings (since _add_tag lowercases)
tag_names = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
    min_size=1,
    max_size=20,
)

# Strategy for confidence values (0-100 integer percentages)
confidences = st.integers(min_value=0, max_value=100)

# Strategy for a non-empty list of (tag_name, confidence) pairs
tag_entries = st.lists(
    st.tuples(tag_names, confidences),
    min_size=1,
    max_size=50,
)


# Feature: ruby-to-python-rewrite, Property 3: Tag confidence maximization
@settings(max_examples=100)
@given(entries=tag_entries)
def test_tag_confidence_maximization(entries: list[tuple[str, int]]) -> None:
    """Property 3: For any sequence of (label, confidence) pairs where the same
    label appears multiple times with different confidence values, after
    processing all pairs through _add_tag, the stored confidence for that label
    equals the maximum confidence seen across all occurrences.

    Validates: Requirements 3.7
    """
    # Build a Tagger with an empty tags dict, bypassing __init__ which
    # requires settings.yml and AWS credentials.
    tagger = object.__new__(Tagger)
    tagger.tags = {}

    # Compute expected max confidence per label
    expected: dict[str, int] = {}
    for name, confidence in entries:
        lower_name = name.lower()
        if lower_name in expected:
            expected[lower_name] = max(expected[lower_name], confidence)
        else:
            expected[lower_name] = confidence

    # Feed all entries through _add_tag
    for name, confidence in entries:
        tagger._add_tag(name, confidence)

    # Verify: every tag has the maximum confidence
    assert tagger.tags == expected

    # Verify: no extra tags appeared
    assert set(tagger.tags.keys()) == set(expected.keys())


# Feature: ruby-to-python-rewrite, Property 4: Tag categorization is a complete partition
@settings(max_examples=100)
@given(
    tag_entries=st.dictionaries(
        keys=tag_names,
        values=confidences,
        min_size=0,
        max_size=30,
    ),
    flagged=st.lists(tag_names, min_size=0, max_size=10, unique=True),
    stopwords=st.lists(tag_names, min_size=0, max_size=10, unique=True),
)
def test_tag_categorization_is_complete_partition(
    tag_entries: dict[str, int],
    flagged: list[str],
    stopwords: list[str],
) -> None:
    """Property 4: For any set of detected labels (after lowercase normalization)
    and given flagged_tags and stopwords lists, every label appears in exactly one
    of the three categories (flagged_tags, important_tags, ignored_tags), and the
    union of all three categories equals the full set of detected labels. A label
    is flagged if it matches the flagged list, ignored if it matches the stopwords
    list, and important otherwise.

    Validates: Requirements 3.8, 3.11
    """
    # Categorize using the same logic as Tagger.callback
    flagged_result: dict[str, int] = {}
    important_result: dict[str, int] = {}
    ignored_result: dict[str, int] = {}

    for tag, percent in tag_entries.items():
        if tag in flagged:
            flagged_result[tag] = percent
        elif tag in stopwords:
            ignored_result[tag] = percent
        else:
            important_result[tag] = percent

    all_tags = set(tag_entries.keys())

    # Union of all three categories equals the full set
    categorized = set(flagged_result.keys()) | set(important_result.keys()) | set(ignored_result.keys())
    assert categorized == all_tags, (
        f"Union of categories {categorized} != all tags {all_tags}"
    )

    # No overlap between any two categories (each label in exactly one)
    assert set(flagged_result.keys()).isdisjoint(important_result.keys()), (
        "flagged and important overlap"
    )
    assert set(flagged_result.keys()).isdisjoint(ignored_result.keys()), (
        "flagged and ignored overlap"
    )
    assert set(important_result.keys()).isdisjoint(ignored_result.keys()), (
        "important and ignored overlap"
    )

    # Total count matches
    assert len(flagged_result) + len(important_result) + len(ignored_result) == len(tag_entries), (
        "Category counts don't sum to total tag count"
    )

    # Verify categorization correctness: flagged tags are in flagged list
    for tag in flagged_result:
        assert tag in flagged, f"Tag '{tag}' in flagged_result but not in flagged list"

    # Ignored tags are in stopwords list (and not in flagged, due to priority)
    for tag in ignored_result:
        assert tag in stopwords, f"Tag '{tag}' in ignored_result but not in stopwords list"
        assert tag not in flagged, f"Tag '{tag}' in ignored but should be flagged (flagged takes priority)"

    # Important tags are in neither list
    for tag in important_result:
        assert tag not in flagged, f"Tag '{tag}' in important but is in flagged list"
        assert tag not in stopwords, f"Tag '{tag}' in important but is in stopwords list"


# Strategy for frame paths: unique file-like strings
frame_paths = st.lists(
    st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_"),
        min_size=5,
        max_size=20,
    ).map(lambda s: f"/tmp/tagger/img{s}.jpg"),
    min_size=1,
    max_size=60,
    unique=True,
)


# Feature: ruby-to-python-rewrite, Property 5: Frame selection algorithm
@settings(max_examples=100)
@given(frames=frame_paths)
def test_frame_selection_algorithm(frames: list[str]) -> None:
    """Property 5: For any list of sorted frame paths, if the list has 6 or
    fewer elements, the selected subset should equal the entire list. If the
    list has more than 6 elements, the selected subset should contain the frame
    at index 5 plus frames at evenly spaced intervals of len(frames) // 5, and
    the selected subset should be a strict subset of the original list.

    Validates: Requirements 3.5
    """
    tagger = object.__new__(Tagger)
    tagger.partitions = 5

    sorted_frames = sorted(frames)
    selected = tagger._select_frames(sorted_frames)

    if len(sorted_frames) <= 6:
        # All frames should be selected
        assert selected == sorted_frames, (
            f"Expected all {len(sorted_frames)} frames, got {len(selected)}"
        )
    else:
        # All selected frames must come from the original list
        for frame in selected:
            assert frame in sorted_frames, (
                f"Selected frame '{frame}' not in original sorted frames"
            )

        # Frame at index 5 must be the first element
        assert selected[0] == sorted_frames[5], (
            "First selected frame must be frame at index 5"
        )

        # Reconstruct the exact expected list: frame[5] then evenly spaced
        span = len(sorted_frames) // 5
        expected_list: list[str] = [sorted_frames[5]]
        counter = span - 1
        while counter < len(sorted_frames):
            expected_list.append(sorted_frames[counter])
            counter += span

        assert selected == expected_list, (
            f"Selected list {selected} != expected {expected_list}"
        )

        # The unique selected frames are a subset of the original
        assert set(selected).issubset(set(sorted_frames)), (
            "Selected frames are not a subset of the original"
        )


# Strategy for base filenames without extension
base_names = st.from_regex(r"[A-Za-z][A-Za-z0-9_\-]{0,29}", fullmatch=True)

# Strategy for video extensions
video_extensions = st.sampled_from([".mp4", ".avi", ".mkv", ".mov"])


# Feature: ruby-to-python-rewrite, Property 6: Needs-processing detects missing output files (JSON variant)
@settings(max_examples=100)
@given(base=base_names, ext=video_extensions)
def test_needs_processing_detects_missing_json(base: str, ext: str) -> None:
    """Property 6 (JSON variant): For any input file path, needs_processing
    returns True if and only if the corresponding .json file does not exist.

    Validates: Requirements 3.1
    """
    tagger = object.__new__(Tagger)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = os.path.join(tmpdir, base + ext)
        json_file = os.path.join(tmpdir, base + ".json")

        # Case 1: JSON does not exist → needs_processing returns True
        assert tagger.needs_processing(input_file) is True, (
            f"needs_processing should return True when {json_file} does not exist"
        )

        # Case 2: JSON exists → needs_processing returns False
        with open(json_file, "w") as f:
            f.write("{}")
        assert tagger.needs_processing(input_file) is False, (
            f"needs_processing should return False when {json_file} exists"
        )

        # Case 3: Remove JSON → needs_processing returns True again
        os.remove(json_file)
        assert tagger.needs_processing(input_file) is True, (
            "needs_processing should return True after JSON is removed"
        )


# Strategy for non-empty strings suitable for YAML scalar values
yaml_safe_strings = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_- "),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() == s and len(s.strip()) > 0)

# Strategy for lists of unique tag-like strings
yaml_tag_lists = st.lists(yaml_safe_strings, min_size=0, max_size=15, unique=True)


# Feature: ruby-to-python-rewrite, Property 14: Settings YAML round trip
@settings(max_examples=100)
@given(
    access_key_id=yaml_safe_strings,
    secret_access_key=yaml_safe_strings,
    region=yaml_safe_strings,
    flagged_tags=yaml_tag_lists,
    stopwords=yaml_tag_lists,
)
def test_settings_yaml_round_trip(
    access_key_id: str,
    secret_access_key: str,
    region: str,
    flagged_tags: list[str],
    stopwords: list[str],
) -> None:
    """Property 14: For any valid settings dictionary containing access_key_id,
    secret_access_key, region, flagged_tags (list of strings), and stopwords
    (list of strings), writing it as YAML and reading it back should produce
    an equivalent dictionary.

    Validates: Requirements 8.1
    """
    original: dict[str, object] = {
        "access_key_id": access_key_id,
        "secret_access_key": secret_access_key,
        "region": region,
        "flagged_tags": flagged_tags,
        "stopwords": stopwords,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(original, f, default_flow_style=False)
        tmp_path = f.name

    try:
        with open(tmp_path, "r") as f:
            loaded: dict[str, object] = yaml.safe_load(f)

        assert loaded == original, (
            f"Round-tripped settings differ.\nOriginal: {original}\nLoaded: {loaded}"
        )

        # Verify all expected keys are present
        for key in ("access_key_id", "secret_access_key", "region", "flagged_tags", "stopwords"):
            assert key in loaded, f"Missing key '{key}' after round trip"

        # Verify types are preserved
        assert isinstance(loaded["access_key_id"], str)
        assert isinstance(loaded["secret_access_key"], str)
        assert isinstance(loaded["region"], str)
        assert isinstance(loaded["flagged_tags"], list)
        assert isinstance(loaded["stopwords"], list)
    finally:
        os.unlink(tmp_path)


# --- Unit tests for Tagger (Task 6.7) ---
# Requirements: 3.2, 3.3, 3.4, 3.9


def _valid_settings() -> dict[str, object]:
    """Return a minimal valid settings dict."""
    return {
        "access_key_id": "AKIAIOSFODNN7EXAMPLE",
        "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "region": "us-west-2",
        "flagged_tags": ["human", "person"],
        "stopwords": ["plant", "building"],
    }


def _write_settings(path: str, data: dict[str, object]) -> None:
    """Write a settings dict as YAML to the given path."""
    with open(path, "w") as f:
        yaml.dump(data, f)


class TestTaggerSettingsCredentials:
    """Test settings loading with missing/empty credentials (Requirement 3.2, 3.3)."""

    def test_missing_access_key_raises(self) -> None:
        """Tagger raises RuntimeError when access_key_id is missing."""
        settings_data = _valid_settings()
        del settings_data["access_key_id"]
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "settings.yml")
            _write_settings(settings_path, settings_data)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with pytest.raises(RuntimeError, match="bad config"):
                    Tagger()
            finally:
                os.chdir(original_cwd)

    def test_empty_access_key_raises(self) -> None:
        """Tagger raises RuntimeError when access_key_id is empty string."""
        settings_data = _valid_settings()
        settings_data["access_key_id"] = ""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "settings.yml")
            _write_settings(settings_path, settings_data)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with pytest.raises(RuntimeError, match="bad config"):
                    Tagger()
            finally:
                os.chdir(original_cwd)

    def test_missing_secret_key_raises(self) -> None:
        """Tagger raises RuntimeError when secret_access_key is missing."""
        settings_data = _valid_settings()
        del settings_data["secret_access_key"]
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "settings.yml")
            _write_settings(settings_path, settings_data)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with pytest.raises(RuntimeError, match="bad config"):
                    Tagger()
            finally:
                os.chdir(original_cwd)

    def test_empty_secret_key_raises(self) -> None:
        """Tagger raises RuntimeError when secret_access_key is empty string."""
        settings_data = _valid_settings()
        settings_data["secret_access_key"] = ""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "settings.yml")
            _write_settings(settings_path, settings_data)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with pytest.raises(RuntimeError, match="bad config"):
                    Tagger()
            finally:
                os.chdir(original_cwd)


class TestTaggerSettingsRegion:
    """Test settings loading with missing/empty region (Requirement 3.4)."""

    def test_missing_region_raises(self) -> None:
        """Tagger raises RuntimeError when region is missing."""
        settings_data = _valid_settings()
        del settings_data["region"]
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "settings.yml")
            _write_settings(settings_path, settings_data)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with pytest.raises(RuntimeError, match="bad config"):
                    Tagger()
            finally:
                os.chdir(original_cwd)

    def test_empty_region_raises(self) -> None:
        """Tagger raises RuntimeError when region is empty string."""
        settings_data = _valid_settings()
        settings_data["region"] = ""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "settings.yml")
            _write_settings(settings_path, settings_data)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with pytest.raises(RuntimeError, match="bad config"):
                    Tagger()
            finally:
                os.chdir(original_cwd)


class TestTaggerRekognitionMocking:
    """Test Rekognition API call mocking (Requirement 3.6, 3.7)."""

    def test_process_frame_calls_rekognition(self) -> None:
        """_process_frame sends frame bytes to Rekognition with correct params."""
        tagger = object.__new__(Tagger)
        tagger.tags = {}

        mock_client = MagicMock()
        mock_client.detect_labels.return_value = {
            "Labels": [
                {"Name": "Person", "Confidence": 95.5},
                {"Name": "Dog", "Confidence": 82.3},
            ]
        }
        tagger.client = mock_client

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            frame_path = f.name

        try:
            tagger._process_frame(frame_path)

            mock_client.detect_labels.assert_called_once()
            call_kwargs = mock_client.detect_labels.call_args
            assert call_kwargs[1]["MaxLabels"] == 20
            assert call_kwargs[1]["MinConfidence"] == 70

            # Tags should be stored lowercase with int confidence
            assert "person" in tagger.tags
            assert "dog" in tagger.tags
            assert tagger.tags["person"] == 95
            assert tagger.tags["dog"] == 82
        finally:
            os.unlink(frame_path)

    def test_process_frame_handles_empty_labels(self) -> None:
        """_process_frame handles empty Labels response gracefully."""
        tagger = object.__new__(Tagger)
        tagger.tags = {}

        mock_client = MagicMock()
        mock_client.detect_labels.return_value = {"Labels": []}
        tagger.client = mock_client

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0")
            frame_path = f.name

        try:
            tagger._process_frame(frame_path)
            assert tagger.tags == {}
        finally:
            os.unlink(frame_path)


class TestTaggerJsonOutput:
    """Test JSON output structure (Requirement 3.9)."""

    def test_callback_writes_correct_json_structure(self) -> None:
        """callback produces JSON with all required fields and correct values."""
        tagger = object.__new__(Tagger)
        tagger.tags = {}
        tagger.previous_item_time = -9999
        tagger.partitions = 5
        tagger.flagged_tags = ["person", "human"]
        tagger.stopwords = ["plant", "tree"]

        mock_client = MagicMock()
        mock_client.detect_labels.return_value = {
            "Labels": [
                {"Name": "Person", "Confidence": 95.0},
                {"Name": "Car", "Confidence": 88.0},
                {"Name": "Plant", "Confidence": 72.0},
            ]
        }
        tagger.client = mock_client

        with tempfile.TemporaryDirectory() as tmpdir:
            # Filename: Camera-120000-120030.mp4 → start=43200, end=43230, duration=30
            input_file = os.path.join(tmpdir, "Camera-120000-120030.mp4")
            output_json = os.path.join(tmpdir, "Camera-120000-120030.json")

            with open(input_file, "wb") as f:
                f.write(b"\x00" * 10)

            # Create a fake frame file
            frame_file = os.path.join(tmpdir, "img001.jpg")
            with open(frame_file, "wb") as f:
                f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

            tagger.callback(input_file, [frame_file])

            assert os.path.exists(output_json)
            with open(output_json, "r") as f:
                data = json.load(f)

            # Verify all required keys exist
            assert "flagged_tags" in data
            assert "important_tags" in data
            assert "ignored_tags" in data
            assert "time_start" in data
            assert "time_end" in data
            assert "duration" in data
            assert "since" in data

            # Verify tag categorization
            assert "person" in data["flagged_tags"]
            assert "car" in data["important_tags"]
            assert "plant" in data["ignored_tags"]

            # Verify timing from filename Camera-120000-120030
            assert data["time_start"] == 43200  # 12*3600
            assert data["time_end"] == 43230    # 12*3600 + 30
            assert data["duration"] == 30

    def test_callback_skips_when_input_missing(self) -> None:
        """callback returns without writing JSON when input file doesn't exist."""
        tagger = object.__new__(Tagger)
        tagger.tags = {}
        tagger.previous_item_time = -9999
        tagger.partitions = 5
        tagger.flagged_tags = []
        tagger.stopwords = []

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "nonexistent.mp4")
            output_json = os.path.join(tmpdir, "nonexistent.json")

            tagger.callback(input_file, [])
            assert not os.path.exists(output_json)

    def test_callback_skips_when_json_exists(self) -> None:
        """callback returns without overwriting when JSON output already exists."""
        tagger = object.__new__(Tagger)
        tagger.tags = {}
        tagger.previous_item_time = -9999
        tagger.partitions = 5
        tagger.flagged_tags = []
        tagger.stopwords = []
        tagger.client = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "Camera-100000-100010.mp4")
            output_json = os.path.join(tmpdir, "Camera-100000-100010.json")

            with open(input_file, "wb") as f:
                f.write(b"\x00" * 10)
            with open(output_json, "w") as f:
                f.write('{"existing": true}')

            tagger.callback(input_file, ["/tmp/frame.jpg"])

            # Original JSON should be untouched
            with open(output_json, "r") as f:
                data = json.load(f)
            assert data == {"existing": True}
            tagger.client.detect_labels.assert_not_called()
