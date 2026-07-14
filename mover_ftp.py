import os
import time

from mover import Mover


class MoverFtp(Mover):
    """Moves camera clips uploaded via FTP into a date-organized output tree.

    Unlike :class:`Mover`, the FTP source directory is flat: every clip lives
    directly in ``input_folder`` with no date-named subfolders. This mover:

    * deletes any stray ``.jpg`` files left behind by the camera's FTP upload,
    * waits for each ``.mp4`` file's size to stabilize so that clips still being
      uploaded are not moved mid-write (the same stability check as
      :class:`Mover`), and
    * remuxes each stable clip into a dated subfolder of ``output_folder``,
      deriving the date from the filename.

    Source files are expected to be named ``{name}_YYYYMMDDHHMMSS.mp4`` (for
    example ``Back Yard_00_20260713113642.mp4``). The ``YYYYMMDD`` portion of the
    trailing timestamp is used as the destination subfolder name.

    Attributes are inherited from :class:`Mover`.
    """

    def move(self) -> None:
        """Run a full delete/scan/wait/move cycle over the flat FTP folder.

        Deletes all ``.jpg`` files, records the size of every ``.mp4`` clip,
        waits ``stabilize_delay`` seconds, then remuxes and moves any clip whose
        size did not change into its dated destination subfolder.
        """
        # Remove any JPEG stills the camera dropped alongside the video clips.
        for filename in os.listdir(self.input_folder):
            if filename.lower().endswith('.jpg'):
                path = os.path.join(self.input_folder, filename)
                if os.path.isfile(path):
                    print(f"Deleting {filename}")
                    os.unlink(path)

        # First pass: record the current size of every clip as a baseline.
        for filename in os.listdir(self.input_folder):
            print(f"Scanning {filename}")
            src = os.path.join(self.input_folder, filename)
            if os.path.isfile(src) and src.endswith('.mp4'):
                self.file_sizes[src] = os.path.getsize(src)

        # Give any in-progress FTP uploads time to finish being written.
        time.sleep(self.stabilize_delay)

        # Second pass: move only the clips whose size matched the baseline.
        for filename in os.listdir(self.input_folder):
            print(f"Rescanning {filename}")
            src = os.path.join(self.input_folder, filename)
            if not (os.path.isfile(src) and src.endswith('.mp4')):
                continue
            print(f"Checking for stable size of {filename}")
            # A file is safe to move only if its size is unchanged from the
            # initial scan, indicating the upload is complete.
            if self.file_sizes.get(src) == os.path.getsize(src):
                subfolder = self._date_from_filename(filename)
                if subfolder is None:
                    print(f"Could not parse a date from {filename}; skipping")
                    continue
                print("File is of stable size and can be moved and remuxed.")
                output_dir = os.path.join(self.output_folder, subfolder)
                # Ensure the destination date folder exists before moving.
                os.makedirs(output_dir, exist_ok=True)
                dst = os.path.join(output_dir, filename)
                self._remux_move(src, dst)

    def _date_from_filename(self, filename: str) -> str | None:
        """Extract the ``YYYYMMDD`` destination subfolder from a clip filename.

        Filenames follow the pattern ``{name}_YYYYMMDDHHMMSS.mp4`` where the
        portion after the final underscore is a 14-digit timestamp.

        Args:
            filename: The clip's base filename (no directory component), e.g.
                ``Back Yard_00_20260713113642.mp4``.

        Returns:
            The 8-character ``YYYYMMDD`` date string, or ``None`` if the filename
            does not contain a valid trailing timestamp.
        """
        # Strip the extension, then take the segment after the last underscore.
        base = filename[:-len('.mp4')] if filename.endswith('.mp4') else filename
        timestamp = base.rsplit('_', 1)[-1]
        if len(timestamp) == 14 and timestamp.isdigit():
            return timestamp[:8]
        return None
