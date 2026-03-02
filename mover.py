import os
import subprocess
import time


class Mover:
    input_folder: str
    output_folder: str
    stabilize_delay: int
    file_sizes: dict[str, int]

    def __init__(self, input_folder: str, output_folder: str, stabilize_delay: int) -> None:
        self.input_folder = os.path.expanduser(os.path.expandvars(input_folder))
        self.output_folder = os.path.expanduser(os.path.expandvars(output_folder))
        self.stabilize_delay = stabilize_delay
        self.file_sizes = {}

    def move(self) -> None:
        for filename in os.listdir(self.input_folder):
            print(f"Scanning {filename}")
            path = os.path.join(self.input_folder, filename)
            if os.path.isdir(path) and not filename.startswith('.'):
                self._scan_subfolder(filename)

        time.sleep(self.stabilize_delay)

        for filename in os.listdir(self.input_folder):
            print(f"Rescanning {filename}")
            path = os.path.join(self.input_folder, filename)
            if os.path.isdir(path) and not filename.startswith('.'):
                self._scan_subfolder_move(filename)

    def _scan_subfolder(self, folder: str) -> None:
        path = os.path.join(self.input_folder, folder)
        print(f"Scanning Subfolder {path}")
        for filename in os.listdir(path):
            filepath = os.path.expanduser(os.path.join(self.input_folder, folder, filename))
            if not filepath.endswith('.mp4'):
                continue
            if os.path.isfile(filepath):
                self.file_sizes[filepath] = os.path.getsize(filepath)

    def _scan_subfolder_move(self, folder: str) -> None:
        path = os.path.join(self.input_folder, folder)
        print(f"Re-Scanning Subfolder {path}")
        for filename in os.listdir(path):
            src = os.path.expanduser(os.path.join(self.input_folder, folder, filename))
            if not src.endswith('.mp4'):
                continue
            print(f"Checking for stable size of {folder}/{filename}")
            if os.path.isfile(src) and self.file_sizes.get(src) == os.path.getsize(src):
                print("File is of stable size and can be moved and remuxed.")
                transformed = self._date_transform(folder)
                dst = os.path.expanduser(
                    os.path.join(self.output_folder, transformed, filename)
                )
                output_dir = os.path.expanduser(
                    os.path.join(self.output_folder, transformed)
                )
                os.makedirs(output_dir, exist_ok=True)
                self._remux_move(src, dst)

    def _date_transform(self, date_string: str) -> str:
        if len(date_string) == 8:
            return date_string[4:8] + date_string[0:4]
        else:
            return date_string

    def _remux_move(self, in_filename: str, out_filename: str) -> None:
        cmd = [
            "ffmpeg", "-i", in_filename,
            "-vcodec", "copy", "-acodec", "copy",
            "-y", out_filename
        ]
        result = subprocess.run(cmd)
        if result.returncode == 0:
            os.unlink(in_filename)
        else:
            print(f'Error remuxing "{in_filename}" to "{out_filename}"')
