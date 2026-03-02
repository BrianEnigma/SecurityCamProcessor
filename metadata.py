"""Filename metadata extraction for security camera videos."""

import os
import re
from typing import TypedDict


class MetadataResult(TypedDict):
    time_start: int
    time_end: int
    duration: int


class Metadata:
    """Parses security camera filenames to extract timing information."""

    @staticmethod
    def extract_times(filename: str) -> MetadataResult:
        """Extract start time, end time, and duration from a camera filename.

        Filenames are of the format ``CameraName-HHMMSS-HHMMSS.ext``.

        Returns a dict with keys ``time_start``, ``time_end``, ``duration``
        (all in seconds since midnight).  Returns -1 for any component that
        cannot be parsed.
        """
        basename = os.path.basename(filename)

        result: MetadataResult = {"time_start": -1, "time_end": -1, "duration": -1}

        # Match start timestamp: -HHMMSS- (six digits between two hyphens)
        start_match = re.search(r"-(\d{2})(\d{2})(\d{2})-", basename)
        if start_match:
            h, m, s = int(start_match.group(1)), int(start_match.group(2)), int(start_match.group(3))
            result["time_start"] = h * 3600 + m * 60 + s

        # Match end timestamp: -HHMMSS. (six digits between a hyphen and a dot)
        end_match = re.search(r"-(\d{2})(\d{2})(\d{2})\.", basename)
        if end_match:
            h, m, s = int(end_match.group(1)), int(end_match.group(2)), int(end_match.group(3))
            result["time_end"] = h * 3600 + m * 60 + s

        if result["time_start"] != -1 and result["time_end"] != -1:
            duration = result["time_end"] - result["time_start"]
            if duration < 0:
                duration += 86400
            result["duration"] = duration

        return result
