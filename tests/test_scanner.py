"""Property-based and unit tests for Scanner."""

import os
import pathlib
import shutil
import sys
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scanner import Scanner, Callback, DirectoryCallback  # noqa: E402


class RecordingCallback(Callback):
    """Test callback that records the order of files it receives."""

    def __init__(self) -> None:
        self.processed_files: list[str] = []

    def needs_processing(self, input_file: str) -> bool:
        return True

    def callback(self, input_file: str, frames: list[str]) -> None:
        self.processed_files.append(input_file)


# Strategy for generating a list of unique, non-hidden filenames with .mp4 extension.
# Use lowercase only to avoid case-insensitive filesystem collisions (macOS HFS+/APFS).
_mp4_basenames = st.from_regex(r"[a-z][a-z0-9_]{0,14}", fullmatch=True)


# Feature: ruby-to-python-rewrite, Property 10: Scanner processes files in sorted order
@settings(max_examples=100)
@given(
    filenames=st.lists(
        _mp4_basenames,
        min_size=1,
        max_size=10,
        unique=True,
    )
)
def test_scanner_processes_files_in_sorted_order(
    filenames: list[str],
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Property 10: For any directory containing multiple files matching the
    configured extension, the Scanner invokes callbacks on those files in
    lexicographically sorted order.

    Validates: Requirements 1.8
    """
    tmp_path = tmp_path_factory.mktemp("scandir")
    scan_dir = str(tmp_path)

    # Create .mp4 files in the directory
    mp4_files: list[str] = []
    for name in filenames:
        fpath = os.path.join(scan_dir, name + ".mp4")
        with open(fpath, "w") as f:
            f.write("fake video")
        mp4_files.append(os.path.abspath(fpath))

    expected_order = sorted(mp4_files)

    recorder = RecordingCallback()

    # Mock ffmpeg presence check and frame extraction so no real ffmpeg needed
    with patch("subprocess.run") as mock_run:
        # Make 'which ffmpeg' succeed
        which_result = MagicMock()
        which_result.returncode = 0
        which_result.stdout = b"/usr/bin/ffmpeg\n"

        # Make frame extraction fail immediately (no frames to extract)
        extract_result = MagicMock()
        extract_result.returncode = 1
        extract_result.stdout = b""

        def run_side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
            if cmd[0] == "which":
                return which_result
            return extract_result

        mock_run.side_effect = run_side_effect

        scanner = Scanner(scan_dir, ".mp4", [recorder], [])
        scanner.scan()

    assert recorder.processed_files == expected_order, (
        f"Files not processed in sorted order.\n"
        f"  Expected: {expected_order}\n"
        f"  Got:      {recorder.processed_files}"
    )


class RecordingDirectoryCallback(DirectoryCallback):
    """Test directory callback that records the order of directories it receives."""

    def __init__(self) -> None:
        self.processed_dirs: list[str] = []

    def needs_processing(self, input_dir: str) -> bool:
        return True

    def callback(self, input_dir: str) -> None:
        self.processed_dirs.append(input_dir)


def _build_dir_tree(base: str, tree: dict[str, object]) -> None:
    """Recursively create a directory tree from a nested dict.

    Keys are directory names, values are nested dicts (sub-trees).
    """
    for name, subtree in tree.items():
        child = os.path.join(base, name)
        os.makedirs(child, exist_ok=True)
        if isinstance(subtree, dict):
            _build_dir_tree(child, subtree)


# Strategy: generate a nested directory tree as a recursive dict.
# Leaf nodes are empty dicts. Max depth ~3, max breadth ~3.
_dir_name = st.from_regex(r"[a-z][a-z0-9]{0,5}", fullmatch=True)

_dir_tree: st.SearchStrategy[dict[str, object]] = st.recursive(
    st.fixed_dictionaries({}),
    lambda children: st.dictionaries(
        _dir_name,
        children,
        min_size=1,
        max_size=3,
    ),
    max_leaves=9,
)


def _collect_all_dirs(base: str, tree: dict[str, object]) -> list[str]:
    """Return all directory paths that would be created from the tree."""
    result: list[str] = []
    for name, subtree in tree.items():
        child = os.path.join(base, name)
        if isinstance(subtree, dict):
            result.extend(_collect_all_dirs(child, subtree))
        result.append(child)
    return result


# Feature: ruby-to-python-rewrite, Property 11: Scanner directory traversal is depth-first
@settings(max_examples=100)
@given(tree=_dir_tree)
def test_scanner_directory_traversal_is_depth_first(
    tree: dict[str, object],
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Property 11: For any directory tree, the Scanner invokes directory
    callbacks on child directories before their parent directories, with the
    root directory processed last.

    Validates: Requirements 1.6
    """
    assume(len(tree) > 0)

    tmp_path = tmp_path_factory.mktemp("dirtree")
    scan_dir = str(tmp_path)

    _build_dir_tree(scan_dir, tree)

    recorder = RecordingDirectoryCallback()

    with patch("subprocess.run") as mock_run:
        which_result = MagicMock()
        which_result.returncode = 0
        which_result.stdout = b"/usr/bin/ffmpeg\n"
        mock_run.return_value = which_result

        scanner = Scanner(scan_dir, ".mp4", [], [recorder])
        scanner.scan()

    processed = recorder.processed_dirs

    # The root directory must be processed last
    assert processed[-1] == os.path.abspath(scan_dir), (
        f"Root directory should be processed last.\n"
        f"  Root: {os.path.abspath(scan_dir)}\n"
        f"  Last processed: {processed[-1]}"
    )

    # For every directory that was processed, all of its children that appear
    # in the processed list must appear before it (depth-first invariant).
    index_of: dict[str, int] = {d: i for i, d in enumerate(processed)}
    for directory in processed:
        for other in processed:
            # Check if 'other' is a direct or indirect child of 'directory'
            if other != directory and other.startswith(directory + os.sep):
                assert index_of[other] < index_of[directory], (
                    f"Child directory should be processed before parent.\n"
                    f"  Parent: {directory} (index {index_of[directory]})\n"
                    f"  Child:  {other} (index {index_of[other]})"
                )

# ---------------------------------------------------------------------------
# Unit tests for Scanner (Task 3.5)
# ---------------------------------------------------------------------------


class TestScannerFfmpegPresenceCheck:
    """Test ffmpeg availability check at Scanner initialization (Requirement 1.7)."""

    def test_raises_runtime_error_when_ffmpeg_not_found(self, tmp_path: pathlib.Path) -> None:
        """Scanner should raise RuntimeError when ffmpeg is not on the system."""
        with patch("subprocess.run") as mock_run:
            result = MagicMock()
            result.returncode = 1
            result.stdout = b""
            mock_run.return_value = result

            try:
                Scanner(str(tmp_path), ".mp4", [], [])
                assert False, "Expected RuntimeError for missing ffmpeg"
            except RuntimeError as e:
                assert "ffmpeg" in str(e).lower()

    def test_succeeds_when_ffmpeg_is_present(self, tmp_path: pathlib.Path) -> None:
        """Scanner should initialize without error when ffmpeg is available."""
        with patch("subprocess.run") as mock_run:
            result = MagicMock()
            result.returncode = 0
            result.stdout = b"/usr/bin/ffmpeg\n"
            mock_run.return_value = result

            scanner = Scanner(str(tmp_path), ".mp4", [], [])
            assert scanner.directory == os.path.abspath(str(tmp_path))

    def test_raises_when_which_returns_zero_but_empty_stdout(self, tmp_path: pathlib.Path) -> None:
        """Scanner should raise RuntimeError when 'which' returns 0 but empty output."""
        with patch("subprocess.run") as mock_run:
            result = MagicMock()
            result.returncode = 0
            result.stdout = b""
            mock_run.return_value = result

            try:
                Scanner(str(tmp_path), ".mp4", [], [])
                assert False, "Expected RuntimeError for empty ffmpeg path"
            except RuntimeError:
                pass


class TestScannerTempDirectoryCleanup:
    """Test that /tmp/tagger/ is cleaned before each file (Requirement 1.9)."""

    def test_temp_directory_cleaned_between_files(self, tmp_path: pathlib.Path) -> None:
        """The temp directory should be recreated (cleaned) before each file is processed."""
        scan_dir = str(tmp_path)
        # Create two .mp4 files
        for name in ["aaa.mp4", "bbb.mp4"]:
            with open(os.path.join(scan_dir, name), "w") as f:
                f.write("fake")

        rmtree_calls: list[str] = []
        makedirs_calls: list[str] = []

        original_rmtree = shutil.rmtree
        original_makedirs = os.makedirs

        def tracking_rmtree(path: str, *args: object, **kwargs: object) -> None:
            rmtree_calls.append(path)
            original_rmtree(path, *args, **kwargs)  # type: ignore[arg-type]

        def tracking_makedirs(path: str, *args: object, **kwargs: object) -> None:
            makedirs_calls.append(path)
            original_makedirs(path, *args, **kwargs)  # type: ignore[arg-type]

        recorder = RecordingCallback()

        with patch("subprocess.run") as mock_run, \
             patch("shutil.rmtree", side_effect=tracking_rmtree), \
             patch("os.makedirs", side_effect=tracking_makedirs):

            which_result = MagicMock()
            which_result.returncode = 0
            which_result.stdout = b"/usr/bin/ffmpeg\n"

            extract_fail = MagicMock()
            extract_fail.returncode = 1
            extract_fail.stdout = b""

            def run_side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
                if cmd[0] == "which":
                    return which_result
                return extract_fail

            mock_run.side_effect = run_side_effect

            # Pre-create /tmp/tagger/ so rmtree has something to remove
            os.makedirs("/tmp/tagger/", exist_ok=True)

            scanner = Scanner(scan_dir, ".mp4", [recorder], [])
            scanner.scan()

        # Both files should have been processed
        assert len(recorder.processed_files) == 2

        # /tmp/tagger/ should have been cleaned (rmtree + makedirs) for each file
        tagger_rmtree = [c for c in rmtree_calls if "/tmp/tagger" in c]
        tagger_makedirs = [c for c in makedirs_calls if "/tmp/tagger" in c]
        assert len(tagger_rmtree) >= 2, f"Expected rmtree called for each file, got {len(tagger_rmtree)}"
        assert len(tagger_makedirs) >= 2, f"Expected makedirs called for each file, got {len(tagger_makedirs)}"


class TestScannerCallbackDispatch:
    """Test callback dispatch with mock callbacks (Requirement 1.3)."""

    def test_callbacks_invoked_for_files_needing_processing(self, tmp_path: pathlib.Path) -> None:
        """All callbacks should be invoked for files where at least one needs processing."""
        scan_dir = str(tmp_path)
        with open(os.path.join(scan_dir, "video.mp4"), "w") as f:
            f.write("fake")

        cb1 = RecordingCallback()  # needs_processing returns True
        cb2 = RecordingCallback()

        with patch("subprocess.run") as mock_run:
            which_result = MagicMock()
            which_result.returncode = 0
            which_result.stdout = b"/usr/bin/ffmpeg\n"

            extract_fail = MagicMock()
            extract_fail.returncode = 1

            def run_side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
                if cmd[0] == "which":
                    return which_result
                return extract_fail

            mock_run.side_effect = run_side_effect

            scanner = Scanner(scan_dir, ".mp4", [cb1, cb2], [])
            scanner.scan()

        expected_file = os.path.abspath(os.path.join(scan_dir, "video.mp4"))
        assert cb1.processed_files == [expected_file]
        assert cb2.processed_files == [expected_file]

    def test_callbacks_not_invoked_when_no_processing_needed(self, tmp_path: pathlib.Path) -> None:
        """No callbacks should fire when all callbacks return False for needs_processing."""
        scan_dir = str(tmp_path)
        with open(os.path.join(scan_dir, "video.mp4"), "w") as f:
            f.write("fake")

        class SkipCallback(Callback):
            def __init__(self) -> None:
                self.invoked: bool = False

            def needs_processing(self, input_file: str) -> bool:
                return False

            def callback(self, input_file: str, frames: list[str]) -> None:
                self.invoked = True

        cb = SkipCallback()

        with patch("subprocess.run") as mock_run:
            which_result = MagicMock()
            which_result.returncode = 0
            which_result.stdout = b"/usr/bin/ffmpeg\n"
            mock_run.return_value = which_result

            scanner = Scanner(scan_dir, ".mp4", [cb], [])
            scanner.scan()

        assert not cb.invoked, "Callback should not be invoked when needs_processing returns False"

    def test_callbacks_receive_extracted_frames(self, tmp_path: pathlib.Path) -> None:
        """Callbacks should receive the list of extracted frame paths."""
        scan_dir = str(tmp_path)
        with open(os.path.join(scan_dir, "clip.mp4"), "w") as f:
            f.write("fake")

        received_frames: list[list[str]] = []

        class FrameRecorder(Callback):
            def needs_processing(self, input_file: str) -> bool:
                return True

            def callback(self, input_file: str, frames: list[str]) -> None:
                received_frames.append(list(frames))

        cb = FrameRecorder()

        with patch("subprocess.run") as mock_run:
            which_result = MagicMock()
            which_result.returncode = 0
            which_result.stdout = b"/usr/bin/ffmpeg\n"

            call_count = 0

            def run_side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
                nonlocal call_count
                if cmd[0] == "which":
                    return which_result

                # Simulate extracting 2 frames then failing on the 3rd
                result = MagicMock()
                if call_count < 2:
                    # Create the frame file that ffmpeg would produce
                    output_path = cmd[-1]  # last arg is the output filename
                    with open(output_path, "wb") as f:
                        f.write(b"\xff\xd8fake jpeg")
                    result.returncode = 0
                    call_count += 1
                else:
                    result.returncode = 1
                return result

            mock_run.side_effect = run_side_effect

            scanner = Scanner(scan_dir, ".mp4", [cb], [])
            scanner.scan()

        assert len(received_frames) == 1, "Callback should be invoked once for the single file"
        assert len(received_frames[0]) == 2, f"Expected 2 frames, got {len(received_frames[0])}"
        for frame_path in received_frames[0]:
            assert frame_path.endswith(".jpg")

    def test_hidden_files_and_dirs_are_skipped(self, tmp_path: pathlib.Path) -> None:
        """Scanner should skip hidden files and directories (starting with '.')."""
        scan_dir = str(tmp_path)

        # Create a hidden file and a hidden directory
        with open(os.path.join(scan_dir, ".hidden.mp4"), "w") as f:
            f.write("fake")
        hidden_dir = os.path.join(scan_dir, ".hidden_dir")
        os.makedirs(hidden_dir)
        with open(os.path.join(hidden_dir, "inside.mp4"), "w") as f:
            f.write("fake")

        # Create a visible file
        with open(os.path.join(scan_dir, "visible.mp4"), "w") as f:
            f.write("fake")

        recorder = RecordingCallback()

        with patch("subprocess.run") as mock_run:
            which_result = MagicMock()
            which_result.returncode = 0
            which_result.stdout = b"/usr/bin/ffmpeg\n"

            extract_fail = MagicMock()
            extract_fail.returncode = 1

            def run_side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
                if cmd[0] == "which":
                    return which_result
                return extract_fail

            mock_run.side_effect = run_side_effect

            scanner = Scanner(scan_dir, ".mp4", [recorder], [])
            scanner.scan()

        # Only the visible file should be processed
        assert len(recorder.processed_files) == 1
        assert recorder.processed_files[0].endswith("visible.mp4")
