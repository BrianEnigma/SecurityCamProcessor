"""GIF timelapse generation plugin for SecurityCamProcessor."""

import os
import subprocess

from scanner import Callback


class GifMaker(Callback):
    """Converts extracted video frames into an animated GIF timelapse."""

    def __init__(self) -> None:
        super().__init__()
        if not self._is_convert_present():
            raise RuntimeError("ImageMagick convert is required")

    def _is_convert_present(self) -> bool:
        """Check if ImageMagick convert is available on the system."""
        result: subprocess.CompletedProcess[bytes] = subprocess.run(
            ["which", "convert"], capture_output=True
        )
        return result.returncode == 0 and len(result.stdout.strip()) > 0

    def needs_processing(self, input_file: str) -> bool:
        """Return True if a .gif file does not exist for this input."""
        output_file: str = os.path.splitext(input_file)[0] + ".gif"
        return not os.path.exists(output_file)

    def callback(self, input_file: str, frames: list[str]) -> None:
        """Resize frames and combine into an animated GIF."""
        output_file: str = os.path.splitext(input_file)[0] + ".gif"
        if not os.path.exists(input_file):
            return
        if os.path.exists(output_file):
            return

        print(f"{input_file} => {output_file}")
        frames_resized: list[str] = self._convert_frames(frames)
        self._build_gif(output_file, frames_resized)

    def _convert_frames(self, frames: list[str]) -> list[str]:
        """Resize each frame to 300x300 via ImageMagick convert."""
        resized: list[str] = []
        for filename in frames:
            outfile: str = os.path.splitext(filename)[0] + ".gif"
            resized.append(outfile)
            subprocess.run(
                ["convert", "-resize", "300x300", filename, outfile],
                capture_output=True,
            )
        return resized

    def _build_gif(self, output_file: str, frames_resized: list[str]) -> None:
        """Combine resized frames into a single animated GIF via gifsicle."""
        cmd: list[str] = [
            "gifsicle", "--merge",
            "--delay", "3",
            "--loopcount=0",
            "--optimize",
            "--colors", "256",
        ]
        for f in sorted(frames_resized):
            cmd.append(f)
        with open(output_file, "wb") as out:
            subprocess.run(cmd, stdout=out, stderr=subprocess.DEVNULL)
