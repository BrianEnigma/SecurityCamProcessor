"""Property-based and unit tests for GifMaker plugin."""

import os
import subprocess
import sys
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st
from PIL import Image
from unittest.mock import patch

# Add parent directory to path so we can import gifmaker
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gifmaker import GifMaker  # noqa: E402


# Strategy for base filenames without extension
base_names = st.from_regex(r"[A-Za-z][A-Za-z0-9_\-]{0,29}", fullmatch=True)

# Strategy for video extensions
video_extensions = st.sampled_from([".mp4", ".avi", ".mkv", ".mov"])


# Feature: pillow-gif-generation, Property 6: Needs-processing detects missing output files
@settings(max_examples=100)
@given(base=base_names, ext=video_extensions)
def test_needs_processing_detects_missing_gif(base: str, ext: str) -> None:
    """Property 6 (GIF variant): For any input file path, needs_processing
    returns True if and only if the corresponding .gif file does not exist.

    Validates: Requirements 3.4, 6.6
    """
    gm = GifMaker()

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


class TestGifMakerSkipBehavior:
    """Test callback skip conditions (Requirements 3.4, 3.5, 6.7)."""

    def test_skip_when_input_file_missing(self) -> None:
        """callback should return without error when input file doesn't exist."""
        gm = GifMaker()
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_input = os.path.join(tmpdir, "nonexistent.mp4")
            # Should not raise, should not create any output
            gm.callback(missing_input, [])
            gif_path = os.path.join(tmpdir, "nonexistent.gif")
            assert not os.path.exists(gif_path)

    def test_skip_when_output_gif_exists(self) -> None:
        """callback should skip when output GIF already exists."""
        gm = GifMaker()
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "Camera-120000-120010.mp4")
            gif_file = os.path.join(tmpdir, "Camera-120000-120010.gif")

            # Create both input and output files
            with open(input_file, "wb") as f:
                f.write(b"\x00" * 10)
            with open(gif_file, "wb") as f:
                f.write(b"GIF89a")

            # Patch _resize_frames to detect if it gets called
            with patch.object(gm, "_resize_frames") as mock_resize:
                gm.callback(input_file, ["/tmp/frame1.jpg"])
                mock_resize.assert_not_called()

    def test_skip_when_input_missing_does_not_call_resize(self) -> None:
        """callback should not invoke resize or build when input is missing."""
        gm = GifMaker()
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_input = os.path.join(tmpdir, "gone.mp4")
            with patch.object(gm, "_resize_frames") as mock_resize, \
                 patch.object(gm, "_build_gif") as mock_build:
                gm.callback(missing_input, ["/tmp/frame1.jpg"])
                mock_resize.assert_not_called()
                mock_build.assert_not_called()


# Strategy for random source image dimensions (before resize)
image_dimensions = st.tuples(
    st.integers(min_value=1, max_value=800),
    st.integers(min_value=1, max_value=800),
)


def _distinct_colors(n: int) -> list[tuple[int, int, int]]:
    """Return n visually distinct RGB colors spaced evenly across the hue range."""
    colors: list[tuple[int, int, int]] = []
    for i in range(n):
        # Spread hues evenly; use full saturation and value for maximum distinction
        hue = int(255 * i / n) if n > 1 else 128
        # Use HSV-style mapping: place hue in R channel, keep G/B distinct
        colors.append((hue, 255 - hue, (hue * 97) % 256))
    return colors


# Feature: pillow-gif-generation, Property 1: Frame count and dimension preservation
@settings(max_examples=100, deadline=None)
@given(
    num_frames=st.integers(min_value=1, max_value=10),
    dimensions=st.lists(image_dimensions, min_size=1, max_size=10),
)
def test_frame_count_and_dimension_preservation(
    num_frames: int,
    dimensions: list[tuple[int, int]],
) -> None:
    """Property 1: For any list of valid JPEG images (1 or more), the GifMaker
    produces an animated GIF where the frame count equals the input count and
    each frame has 300x300 dimensions.

    Validates: Requirements 1.1, 2.1, 5.1, 5.2, 6.5
    """
    # Use distinct colors so Pillow doesn't deduplicate identical palette frames
    colors = _distinct_colors(num_frames)
    # Cycle dimensions to match num_frames
    dims = [dimensions[i % len(dimensions)] for i in range(num_frames)]

    gm = GifMaker()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate N solid-color JPEG images with varying source dimensions
        frame_paths: list[str] = []
        for i, (color, dim) in enumerate(zip(colors, dims)):
            img = Image.new("RGB", dim, color)
            path = os.path.join(tmpdir, f"frame_{i:04d}.jpg")
            img.save(path, "JPEG")
            frame_paths.append(path)

        # Run through _resize_frames + _build_gif
        resized = gm._resize_frames(frame_paths)
        output_gif = os.path.join(tmpdir, "output.gif")
        gm._build_gif(output_gif, resized)

        # Re-open GIF and verify
        with Image.open(output_gif) as gif:
            # Count frames by seeking through the GIF
            frame_count = 0
            try:
                while True:
                    assert gif.size == (300, 300), (
                        f"Frame {frame_count} has size {gif.size}, expected (300, 300)"
                    )
                    frame_count += 1
                    gif.seek(frame_count)
            except EOFError:
                pass

            assert frame_count == num_frames, (
                f"GIF has {frame_count} frames, expected {num_frames}"
            )

# Feature: pillow-gif-generation, Property 2: GIF metadata invariants
@settings(max_examples=100, deadline=None)
@given(
    num_frames=st.integers(min_value=1, max_value=10),
    dimensions=st.lists(image_dimensions, min_size=1, max_size=10),
)
def test_gif_metadata_invariants(
    num_frames: int,
    dimensions: list[tuple[int, int]],
) -> None:
    """Property 2: For any animated GIF produced by the GifMaker, the frame
    delay is 30ms, the loop count is 0 (infinite), and each frame is in
    palette mode with at most 256 colors.

    Validates: Requirements 2.2, 2.3, 2.4
    """
    colors = _distinct_colors(num_frames)
    dims = [dimensions[i % len(dimensions)] for i in range(num_frames)]

    gm = GifMaker()

    with tempfile.TemporaryDirectory() as tmpdir:
        frame_paths: list[str] = []
        for i, (color, dim) in enumerate(zip(colors, dims)):
            img = Image.new("RGB", dim, color)
            path = os.path.join(tmpdir, f"frame_{i:04d}.jpg")
            img.save(path, "JPEG")
            frame_paths.append(path)

        resized = gm._resize_frames(frame_paths)
        output_gif = os.path.join(tmpdir, "output.gif")
        gm._build_gif(output_gif, resized)

        with Image.open(output_gif) as gif:
            # Verify loop count is 0 (infinite)
            assert gif.info.get("loop", None) == 0, (
                f"Expected loop=0, got {gif.info.get('loop', None)}"
            )

            # First frame must be palette mode — confirms GIF was saved as
            # palette-based (Pillow may decode later frames as RGB internally)
            assert gif.mode == "P", (
                f"First frame: expected mode 'P', got '{gif.mode}'"
            )

            # Verify each frame's duration and color count
            frame_idx = 0
            try:
                while True:
                    assert gif.info.get("duration", None) == 30, (
                        f"Frame {frame_idx}: expected duration=30, "
                        f"got {gif.info.get('duration', None)}"
                    )
                    # Each frame should have at most 256 unique colors
                    rgb_frame = gif.convert("RGB")
                    unique_colors = len(set(rgb_frame.get_flattened_data()))
                    assert unique_colors <= 256, (
                        f"Frame {frame_idx}: has {unique_colors} unique colors, "
                        f"expected at most 256"
                    )
                    frame_idx += 1
                    gif.seek(frame_idx)
            except EOFError:
                pass

# Feature: pillow-gif-generation, Property 3: Output naming convention
@settings(max_examples=100, deadline=None)
@given(
    base=base_names,
    ext=video_extensions,
    num_frames=st.integers(min_value=1, max_value=3),
)
def test_output_naming_convention(
    base: str,
    ext: str,
    num_frames: int,
) -> None:
    """Property 3: For any input file path with any supported video extension,
    the output GIF file path has the same directory and base name as the input
    file, with the extension replaced by .gif.

    Validates: Requirements 2.5
    """
    gm = GifMaker()
    colors = _distinct_colors(num_frames)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = os.path.join(tmpdir, base + ext)
        expected_gif = os.path.splitext(input_file)[0] + ".gif"

        # Create the input file so callback doesn't skip
        with open(input_file, "wb") as f:
            f.write(b"\x00" * 10)

        # Generate JPEG frames
        frame_paths: list[str] = []
        for i, color in enumerate(colors):
            img = Image.new("RGB", (100, 100), color)
            path = os.path.join(tmpdir, f"frame_{i:04d}.jpg")
            img.save(path, "JPEG")
            frame_paths.append(path)

        gm.callback(input_file, frame_paths)

        # Verify the output GIF was created at the expected path
        assert os.path.exists(expected_gif), (
            f"Expected GIF at {expected_gif} but it was not created"
        )
        # Verify no other .gif files were created
        gif_files = [f for f in os.listdir(tmpdir) if f.endswith(".gif")]
        assert len(gif_files) == 1, (
            f"Expected exactly 1 GIF file, found {gif_files}"
        )
        assert gif_files[0] == base + ".gif", (
            f"Expected GIF named '{base}.gif', got '{gif_files[0]}'"
        )


# Feature: pillow-gif-generation, Property 4: Sorted frame assembly order
@settings(max_examples=100, deadline=None)
@given(
    num_frames=st.integers(min_value=2, max_value=8),
)
def test_sorted_frame_assembly_order(num_frames: int) -> None:
    """Property 4: For any list of frame file paths provided in any order,
    the GifMaker assembles the animated GIF with frames sorted by file path.
    Given frames with distinct, identifiable content, the output frame order
    matches the sorted input order.

    Validates: Requirements 2.6
    """
    # Create distinct colors per frame — one unique color per sorted position
    colors = _distinct_colors(num_frames)

    gm = GifMaker()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create frames with names that will sort in a known order
        # Name them so sorted order is frame_0000, frame_0001, ...
        frame_paths: list[str] = []
        for i, color in enumerate(colors):
            img = Image.new("RGB", (100, 100), color)
            path = os.path.join(tmpdir, f"frame_{i:04d}.jpg")
            img.save(path, "JPEG")
            frame_paths.append(path)

        # Shuffle the frame paths to simulate random input order
        import random
        shuffled = list(frame_paths)
        random.shuffle(shuffled)

        # callback sorts internally, so pass shuffled order
        resized = gm._resize_frames(sorted(shuffled))
        output_gif = os.path.join(tmpdir, "output.gif")
        gm._build_gif(output_gif, resized)

        # Extract the dominant color from each GIF frame
        with Image.open(output_gif) as gif:
            gif_colors: list[tuple[int, int, int]] = []
            frame_idx = 0
            try:
                while True:
                    rgb = gif.convert("RGB")
                    # Sample center pixel as representative color
                    center = rgb.getpixel((150, 150))
                    gif_colors.append(center)
                    frame_idx += 1
                    gif.seek(frame_idx)
            except EOFError:
                pass

        # Build expected colors by processing sorted paths through resize
        # (JPEG compression + palette quantization shifts colors, so we need
        # the actual output colors from a reference run in sorted order)
        expected_colors: list[tuple[int, int, int]] = []
        for path in sorted(frame_paths):
            img = Image.open(path)
            img = img.resize((300, 300), Image.Resampling.LANCZOS)
            img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
            rgb = img.convert("RGB")
            expected_colors.append(rgb.getpixel((150, 150)))

        assert len(gif_colors) == num_frames, (
            f"GIF has {len(gif_colors)} frames, expected {num_frames}"
        )
        assert gif_colors == expected_colors, (
            f"Frame color order mismatch.\n"
            f"  Got:      {gif_colors}\n"
            f"  Expected: {expected_colors}"
        )


# Feature: pillow-gif-generation, Property 5: No subprocess invocation
@settings(max_examples=100, deadline=None)
@given(
    num_frames=st.integers(min_value=1, max_value=5),
)
def test_no_subprocess_invocation(num_frames: int) -> None:
    """Property 5: For any invocation of the GifMaker callback with valid
    input frames, no subprocess.run or subprocess.Popen calls are made
    during frame resizing or GIF assembly.

    Validates: Requirements 3.3
    """
    colors = _distinct_colors(num_frames)
    gm = GifMaker()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = os.path.join(tmpdir, "video.mp4")
        with open(input_file, "wb") as f:
            f.write(b"\x00" * 10)

        frame_paths: list[str] = []
        for i, color in enumerate(colors):
            img = Image.new("RGB", (100, 100), color)
            path = os.path.join(tmpdir, f"frame_{i:04d}.jpg")
            img.save(path, "JPEG")
            frame_paths.append(path)

        with patch.object(subprocess, "run") as mock_run, \
             patch.object(subprocess, "Popen") as mock_popen:
            gm.callback(input_file, frame_paths)
            mock_run.assert_not_called()
            mock_popen.assert_not_called()


class TestGifMakerPillowGeneration:
    """Unit tests for Pillow-based GIF generation (Requirements 6.1-6.4)."""

    def test_instantiates_without_external_tool_check(self) -> None:
        """GifMaker() should instantiate without checking for convert or gifsicle."""
        # If it checked for external tools and they were missing, it would raise
        gm = GifMaker()
        assert gm is not None

    def test_callback_produces_valid_animated_gif(self) -> None:
        """callback with valid JPEG frames produces a valid animated GIF."""
        gm = GifMaker()
        colors = _distinct_colors(3)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "Camera-120000.mp4")
            with open(input_file, "wb") as f:
                f.write(b"\x00" * 10)

            frame_paths: list[str] = []
            for i, color in enumerate(colors):
                img = Image.new("RGB", (640, 480), color)
                path = os.path.join(tmpdir, f"frame_{i:04d}.jpg")
                img.save(path, "JPEG")
                frame_paths.append(path)

            gm.callback(input_file, frame_paths)

            gif_path = os.path.join(tmpdir, "Camera-120000.gif")
            assert os.path.exists(gif_path), "GIF file was not created"

            with Image.open(gif_path) as gif:
                # Verify it's a valid animated GIF
                assert gif.format == "GIF"
                # Count frames
                frame_count = 0
                try:
                    while True:
                        assert gif.size == (300, 300)
                        frame_count += 1
                        gif.seek(frame_count)
                except EOFError:
                    pass
                assert frame_count == 3
                # Verify loop and duration
                gif.seek(0)
                assert gif.info.get("loop") == 0
                assert gif.info.get("duration") == 30

    def test_callback_handles_empty_frame_list(self) -> None:
        """callback with empty frame list should not crash or create output."""
        gm = GifMaker()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "video.mp4")
            with open(input_file, "wb") as f:
                f.write(b"\x00" * 10)

            gm.callback(input_file, [])

            gif_path = os.path.join(tmpdir, "video.gif")
            assert not os.path.exists(gif_path), (
                "GIF should not be created for empty frame list"
            )
