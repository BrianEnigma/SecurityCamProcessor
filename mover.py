import os
import subprocess
import time


class Mover:
    """Moves security camera clips from an input tree to an organized output tree.

    The mover scans date-named subfolders of ``input_folder`` for ``.mp4`` clips,
    waits for their sizes to stabilize (so that files still being written by the
    camera are not moved mid-recording), then remuxes each stable clip into a
    date-organized subfolder of ``output_folder``.

    Attributes:
        input_folder: Absolute path to the source directory containing date-named
            subfolders of clips. User (``~``) and environment variables are expanded.
        output_folder: Absolute path to the destination directory. User (``~``) and
            environment variables are expanded.
        stabilize_delay: Seconds to wait between the initial scan and the rescan,
            used to detect files whose size is no longer changing.
        file_sizes: Maps each discovered clip's absolute path to the byte size
            recorded during the initial scan, used to detect stable files.
    """

    input_folder: str
    output_folder: str
    stabilize_delay: int
    file_sizes: dict[str, int]

    def __init__(self, input_folder: str, output_folder: str, stabilize_delay: int) -> None:
        """Initialize the mover and normalize the input/output paths.

        Args:
            input_folder: Source directory containing date-named subfolders of clips.
            output_folder: Destination directory for organized, remuxed clips.
            stabilize_delay: Seconds to wait between the initial scan and rescan
                before deciding whether a file's size has stabilized.
        """
        # Expand both ~ and environment variables so callers can use paths like
        # "~/videos" or "$HOME/videos".
        self.input_folder = os.path.expanduser(os.path.expandvars(input_folder))
        self.output_folder = os.path.expanduser(os.path.expandvars(output_folder))
        self.stabilize_delay = stabilize_delay
        self.file_sizes = {}

    def move(self) -> None:
        """Run a full scan/wait/move cycle over all input subfolders.

        Performs an initial pass to record the size of every clip, waits
        ``stabilize_delay`` seconds, then rescans and moves any clip whose size
        did not change. Hidden folders (those starting with ``.``) are skipped.
        """
        # First pass: record the current size of every clip so we have a baseline.
        for filename in os.listdir(self.input_folder):
            print(f"Scanning {filename}")
            path = os.path.join(self.input_folder, filename)
            if os.path.isdir(path) and not filename.startswith('.'):
                self._scan_subfolder(filename)

        # Give any in-progress recordings time to finish being written.
        time.sleep(self.stabilize_delay)

        # Second pass: move only the clips whose size matched the baseline.
        for filename in os.listdir(self.input_folder):
            print(f"Rescanning {filename}")
            path = os.path.join(self.input_folder, filename)
            if os.path.isdir(path) and not filename.startswith('.'):
                self._scan_subfolder_move(filename)

    def _scan_subfolder(self, folder: str) -> None:
        """Record the size of every ``.mp4`` clip in a single subfolder.

        Populates ``file_sizes`` with the current byte size of each clip so that
        a later rescan can detect whether the file is still growing.

        Args:
            folder: Name of the subfolder (relative to ``input_folder``) to scan.
        """
        path = os.path.join(self.input_folder, folder)
        print(f"Scanning Subfolder {path}")
        for filename in os.listdir(path):
            filepath = os.path.expanduser(os.path.join(self.input_folder, folder, filename))
            # Only track mp4 clips; ignore other files (thumbnails, metadata, etc.).
            if not filepath.endswith('.mp4'):
                continue
            if os.path.isfile(filepath):
                self.file_sizes[filepath] = os.path.getsize(filepath)

    def _scan_subfolder_move(self, folder: str) -> None:
        """Move clips in a subfolder whose size has stabilized since the first scan.

        For each ``.mp4`` whose current size matches the size recorded in
        ``file_sizes``, the destination directory is created (named by the
        date-transformed folder name) and the clip is remuxed and moved there.

        Args:
            folder: Name of the subfolder (relative to ``input_folder``) to process.
        """
        path = os.path.join(self.input_folder, folder)
        print(f"Re-Scanning Subfolder {path}")
        for filename in os.listdir(path):
            src = os.path.expanduser(os.path.join(self.input_folder, folder, filename))
            if not src.endswith('.mp4'):
                continue
            print(f"Checking for stable size of {folder}/{filename}")
            # A file is considered safe to move only if its size is unchanged
            # from the initial scan, indicating the recording is complete.
            if os.path.isfile(src) and self.file_sizes.get(src) == os.path.getsize(src):
                print("File is of stable size and can be moved and remuxed.")
                # Convert the folder's date format for the output directory name.
                transformed = self._date_transform(folder)
                dst = os.path.expanduser(
                    os.path.join(self.output_folder, transformed, filename)
                )
                output_dir = os.path.expanduser(
                    os.path.join(self.output_folder, transformed)
                )
                # Ensure the destination date folder exists before moving.
                os.makedirs(output_dir, exist_ok=True)
                self._remux_move(src, dst)

    def _date_transform(self, date_string: str) -> str:
        """Reorder an 8-character ``MMDDYYYY`` folder name into ``YYYYMMDD``.

        Args:
            date_string: The subfolder name. Expected to be 8 characters in
                ``MMDDYYYY`` form.

        Returns:
            The rearranged ``YYYYMMDD`` string, or the original value unchanged
            if it is not exactly 8 characters long.
        """
        if len(date_string) == 8:
            # MMDDYYYY -> YYYYMMDD (take the year, then the month+day).
            return date_string[4:8] + date_string[0:4]
        else:
            return date_string

    def _remux_move(self, in_filename: str, out_filename: str) -> None:
        """Remux a clip to the destination and delete the source on success.

        Uses ffmpeg to copy the video and audio streams (no re-encoding) into a
        fresh container at ``out_filename``. The source file is removed only if
        ffmpeg exits successfully; otherwise an error is printed and the source
        is left in place.

        Args:
            in_filename: Absolute path to the source clip.
            out_filename: Absolute path where the remuxed clip should be written.
        """
        # "-vcodec copy -acodec copy" remuxes without re-encoding; "-y" overwrites
        # any existing output file.
        cmd = [
            "ffmpeg", "-i", in_filename,
            "-vcodec", "copy", "-acodec", "copy",
            "-y", out_filename
        ]
        result = subprocess.run(cmd)
        if result.returncode == 0:
            # Only delete the original once the remux succeeded.
            os.unlink(in_filename)
        else:
            print(f'Error remuxing "{in_filename}" to "{out_filename}"')
