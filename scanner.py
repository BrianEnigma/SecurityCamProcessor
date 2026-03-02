"""Core scanner engine and plugin base classes for SecurityCamProcessor."""

import glob
import os
import shutil
import subprocess


class Callback:
    """Base class for file-level processing plugins."""

    def needs_processing(self, input_file: str) -> bool:
        """Return True if this callback needs to process the given file."""
        return False

    def callback(self, input_file: str, frames: list[str]) -> None:
        """Process the given input file with the provided extracted frames."""
        pass


class DirectoryCallback:
    """Base class for directory-level processing plugins."""

    def needs_processing(self, input_dir: str) -> bool:
        """Return True if this callback needs to process the given directory."""
        return False

    def callback(self, input_dir: str) -> None:
        """Process the given directory."""
        pass


class Scanner:
    """Core engine that traverses directories, extracts frames, and dispatches to plugins."""

    directory: str
    input_extension: str
    callback_list: list[Callback]
    directory_callback_list: list[DirectoryCallback]

    def __init__(
        self,
        directory: str,
        input_extension: str,
        callback_list: list[Callback],
        directory_callback_list: list[DirectoryCallback],
    ) -> None:
        self.directory = os.path.expanduser(os.path.expandvars(os.path.abspath(directory)))
        self.input_extension = input_extension
        self.callback_list = list(callback_list)
        self.directory_callback_list = list(directory_callback_list)
        if not self._is_ffmpeg_present():
            raise RuntimeError("ffmpeg is required")

    def scan(self) -> None:
        """Run full two-phase scan: files first, then directories."""
        self._scan_dir_for_files(self.directory)
        self._scan_dir_for_folders(self.directory)

    def _is_ffmpeg_present(self) -> bool:
        """Check if ffmpeg is available on the system."""
        result: subprocess.CompletedProcess[bytes] = subprocess.run(
            ["which", "ffmpeg"], capture_output=True
        )
        return result.returncode == 0 and len(result.stdout.strip()) > 0

    def _timecode_string(self, seconds: int) -> str:
        """Convert seconds to HH:MM:SS.000 timecode format."""
        hours: int = seconds // 3600
        remainder: int = seconds % 3600
        minutes: int = remainder // 60
        secs: int = remainder % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.000"

    def _extract_frames(
        self, video_filename: str, extract_period: int, tmp_location: str
    ) -> None:
        """Extract frames from video at given intervals using ffmpeg."""
        seconds: int = 0
        counter: int = 0
        print(f"Extracting frames from {video_filename}")
        while True:
            timecode: str = self._timecode_string(seconds)
            filename: str = os.path.join(tmp_location, f"img{counter:05d}.jpg")
            cmd: list[str] = [
                "ffmpeg", "-loglevel", "16",
                "-ss", timecode,
                "-i", video_filename,
                "-frames:v", "1",
                filename,
            ]
            print(f"{timecode}\r", end="")
            result: subprocess.CompletedProcess[bytes] = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                break
            if not os.path.exists(filename):
                break
            seconds += extract_period
            counter += 1

    def _load_frames(self, folder: str) -> list[str]:
        """Read sorted img*.jpg files from the given directory."""
        pattern: str = os.path.join(folder, "img*.jpg")
        matches: list[str] = sorted(glob.glob(pattern))
        return [os.path.abspath(f) for f in matches]

    def _scan_dir_for_files(self, directory_name: str) -> None:
        """Recursively scan for matching files, extract frames, invoke callbacks."""
        try:
            entries: list[str] = os.listdir(directory_name)
        except OSError:
            return

        file_list: list[str] = []
        for item in entries:
            if not item or item.startswith("."):
                continue
            full_path: str = os.path.abspath(os.path.join(directory_name, item))
            if os.path.isdir(full_path):
                self._scan_dir_for_files(full_path)
                continue
            if not full_path.endswith(self.input_extension):
                continue
            any_need_processing: bool = False
            for cb in self.callback_list:
                if cb.needs_processing(full_path):
                    any_need_processing = True
            if any_need_processing:
                file_list.append(full_path)

        if file_list:
            file_list.sort()
            temp_folder: str = "/tmp/tagger/"
            for full_path in file_list:
                if os.path.exists(temp_folder):
                    shutil.rmtree(temp_folder)
                os.makedirs(temp_folder)
                self._extract_frames(full_path, 1, temp_folder)
                frames: list[str] = self._load_frames(temp_folder)
                for cb in self.callback_list:
                    cb.callback(full_path, frames)

    def _scan_dir_for_folders(self, directory_name: str) -> None:
        """Depth-first recursive traversal, invoke directory callbacks."""
        directory_name = os.path.abspath(directory_name)
        try:
            entries: list[str] = os.listdir(directory_name)
        except OSError:
            return

        for item in entries:
            if not item or item.startswith("."):
                continue
            full_path: str = os.path.abspath(os.path.join(directory_name, item))
            if os.path.isdir(full_path):
                self._scan_dir_for_folders(full_path)
                for dcb in self.directory_callback_list:
                    if dcb.needs_processing(full_path):
                        dcb.callback(full_path)

        # Finally, process the outermost folder
        for dcb in self.directory_callback_list:
            if dcb.needs_processing(directory_name):
                dcb.callback(directory_name)
