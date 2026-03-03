"""GIF timelapse generation plugin for SecurityCamProcessor."""

import os

from PIL import Image
from scanner import Callback


class GifMaker(Callback):
    """Converts extracted video frames into an animated GIF timelapse."""

    def __init__(self) -> None:
        super().__init__()


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
        resized_images: list[Image.Image] = self._resize_frames(sorted(frames))
        self._build_gif(output_file, resized_images)

    def _resize_frames(self, frames: list[str]) -> list[Image.Image]:
        """Open each JPEG frame, resize to 300x300 with LANCZOS, convert to palette mode."""
        images: list[Image.Image] = []
        for filename in frames:
            img: Image.Image = Image.open(filename)
            img = img.resize((300, 300), Image.Resampling.LANCZOS)
            img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
            images.append(img)
        return images

    def _build_gif(self, output_file: str, images: list[Image.Image]) -> None:
        """Save list of PIL Images as animated GIF with 30ms delay and infinite loop."""
        if not images:
            return
        first: Image.Image = images[0]
        rest: list[Image.Image] = images[1:]
        first.save(
            output_file,
            save_all=True,
            append_images=rest,
            duration=30,
            loop=0,
        )
