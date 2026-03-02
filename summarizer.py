"""HTML summary generation plugin for SecurityCamProcessor."""

import json
import os
import subprocess
from datetime import date
from typing import Any, IO

from scanner import DirectoryCallback

SUMMARIZER_HEADER: str = """<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-type" content="text/html; charset=utf-8">
    <title>Security Cam Summary</title>
    <style type="text/css" media="screen">
        div.subdirectory {
            width:300px;
            margin:10px;
            padding:0;
            vertical-align:top;
        }
        div.summary {
            display:inline-block;
            width:300px;
            margin:10px;
            padding:0;
            vertical-align:top;
        }
        img.gif_thumbnail {
            width:300px;
            height:169px;
            border:none;
            margin:0;
            padding:0;
        }
        div.thumbnail {
            display:block;
        }
        div.gap {
            width:50%;
            font-size:85%;
            font-family:monospace;
        }
        div.gapWarning {
            background-color:#ccf;
            font-weight:bold;
        }
        div.gapError {
            background-color:#00f;
            color:#ff0;
            font-weight:bold;
        }
        div.filename {
            display:block;
            width:50%;
        }
        div.filename > a {
            font-size:50%;
            color:black;
            text-decoration:none;
        }
        div.duration {
            display:block;
            width:50%;
            float:right;
            text-align:right;
            font-family:monospace;
        }
        div.durationWarning {
            background-color:#ff0;
            font-weight:bold;
        }
        div.durationError {
            background-color:#f00;
            color:#ff0;
            font-weight:bold;
        }
        div.subdirectory > a {
            color:blue;
            font-size:16pt;
        }
        div.flagged {
            width:300px;
            display:block;
            font-weight:bold;
            color:red;
            background-color:#ffffcc;
        }
        div.important {
            width:300px;
            display:block;
        }
        ul.tags {
            list-style:none;
            padding:0;
        }
        span.timespan {
            font-size:85%;
            font-family:monospace;
        }
    </style>
    
</head>
<body id="summarizer" onload="">
"""

SUMMARIZER_FOOTER: str = """</body>
</html>
"""

MIN_DURATION_WARN: int = 30
MIN_DURATION_ERROR: int = 60
MAX_GAP_ERROR: int = 0
MAX_GAP_WARN: int = 15


class Summarizer(DirectoryCallback):
    """Reads generated JSON metadata and GIF files to produce HTML summary pages."""

    def __init__(self) -> None:
        super().__init__()

    def _read_json_list(self, directory_name: str) -> list[str]:
        """Return sorted list of absolute paths to .json files in directory."""
        directory_name = os.path.expanduser(os.path.expandvars(os.path.abspath(directory_name)))
        result: list[str] = []
        for item in os.listdir(directory_name):
            if not item or item.startswith("."):
                continue
            full_path: str = os.path.abspath(os.path.join(directory_name, item))
            if os.path.isdir(full_path):
                continue
            if not full_path.endswith(".json"):
                continue
            result.append(full_path)
        result.sort()
        return result

    def _read_subdirectory_list(self, directory_name: str) -> list[str]:
        """Return reverse-sorted list of subdirectory names in directory."""
        directory_name = os.path.expanduser(os.path.expandvars(os.path.abspath(directory_name)))
        result: list[str] = []
        for item in os.listdir(directory_name):
            if not item or item.startswith("."):
                continue
            full_path: str = os.path.abspath(os.path.join(directory_name, item))
            if not os.path.isdir(full_path):
                continue
            result.append(item)
        result.sort()
        result.reverse()
        return result

    def _format_time(self, seconds: int | None, include_am_pm: bool) -> str:
        """Format seconds since midnight into H:MM:SS with optional am/pm suffix."""
        if seconds is None or seconds < 0:
            return "err:err:err"
        hours: int = seconds // 3600
        remainder: int = seconds % 3600
        minutes: int = remainder // 60
        secs: int = remainder % 60
        ampm: str = "am"
        if hours > 12:
            ampm = "pm"
            hours -= 12
        result: str = f"{hours}:{minutes:02d}:{secs:02d}"
        if include_am_pm:
            result += ampm
        return result

    def _print_tag_list(
        self,
        f: IO[str],
        tags: dict[str, int] | None,
        class_container: str,
        class_item: str,
        class_percent: str,
    ) -> None:
        """Write an HTML tag list block."""
        f.write(f'<div class="{class_container}"><ul class="tags tags_{class_container}">')
        if tags is not None:
            for tag, percent in tags.items():
                f.write("<li>")
                f.write(f'<span class="{class_item}">{tag}</span>')
                f.write(f'<span class="{class_percent}">({percent}%)</span>')
                f.write("</li>")
        f.write("</ul></div>")

    def _write_json_to_html(self, f: IO[str], json_file_name: str) -> None:
        """Write an HTML block for a single JSON metadata entry."""
        image_filename: str = os.path.basename(json_file_name.replace(".json", ".gif"))
        video_filename: str = os.path.basename(json_file_name.replace(".json", ".mp4"))
        with open(json_file_name, "r") as jf:
            data: dict[str, Any] = json.load(jf)

        duration_val: int = int(data.get("duration", 0) or 0)
        since_val: int | None = data.get("since", None)

        duration_extra: str = ""
        if duration_val >= MIN_DURATION_WARN:
            duration_extra = "durationWarning"
        if duration_val >= MIN_DURATION_ERROR:
            duration_extra = "durationError"

        summary_extra: str = ""
        if duration_val < MIN_DURATION_WARN:
            summary_extra = "summaryShort"
        if duration_val >= MIN_DURATION_ERROR:
            summary_extra = "summaryLong"

        gap_extra: str = ""
        if since_val is not None:
            if int(since_val) <= MAX_GAP_WARN:
                gap_extra = "gapWarning"
            if int(since_val) <= MAX_GAP_ERROR:
                gap_extra = "gapError"

        f.write(f'<div class="summary {summary_extra}">')
        f.write('<div class="thumbnail">')
        f.write(
            f'<a href="{video_filename}"><img src="{image_filename}" '
            f'class="gif_thumbnail" alt="animated thumbnail"/></a>'
        )
        if since_val is not None and int(since_val) >= 0:
            f.write(
                f'<div class="gap {gap_extra}">Gap: '
                f"{self._format_time(int(since_val), False)}</div>"
            )
        else:
            f.write('<div class="gap gapWarning">Gap: UNDEFINED</div>')
        f.write(
            f'<div class="duration {duration_extra}">'
            f"{self._format_time(duration_val, False)}</div>"
        )
        time_start: int = int(data.get("time_start", -1) or -1)
        time_end: int = int(data.get("time_end", -1) or -1)
        f.write(
            f'<div class="filename"><a href="{video_filename}">{video_filename}</a>'
            f'<br /><span class="timespan">'
            f"{self._format_time(time_start, True)} &mdash; "
            f"{self._format_time(time_end, True)}</span></div>"
        )
        f.write("</div>")
        flagged: dict[str, int] | None = data.get("flagged_tags")
        self._print_tag_list(f, flagged, "flagged", "flagged_tag", "flagged_tag_percent")
        important: dict[str, int] | None = data.get("important_tags")
        self._print_tag_list(f, important, "important", "important_tag", "important_tag_percent")
        f.write("</div>\n\n")

    def _write_directory_to_html(
        self, f: IO[str], input_dir: str, directory_name: str
    ) -> None:
        """Write an HTML block for a subdirectory link."""
        full_path: str = os.path.join(input_dir, directory_name)
        try:
            result: subprocess.CompletedProcess[bytes] = subprocess.run(
                ["du", "-sh", full_path],
                capture_output=True,
                text=False,
            )
            size: str = result.stdout.decode().strip().split("\t")[0].strip()
        except Exception:
            size = "?"

        parsed_name: str = directory_name
        if len(directory_name) == 8:
            try:
                y: str = directory_name[0:4]
                m: str = directory_name[4:6]
                d: str = directory_name[6:8]
                dt: date = date(int(y), int(m), int(d))
                dow: str = dt.strftime("%A")
                parsed_name = f"{dow} {y}-{m}-{d}"
            except (ValueError, IndexError):
                pass

        f.write('<div class="subdirectory">')
        f.write(
            f'<a href="{directory_name}/index.html">{parsed_name}</a>'
            f" &mdash; {size}"
        )
        f.write("</div>")

    def needs_processing(self, input_dir: str) -> bool:
        """Return True if no index.html exists or JSON count changed."""
        summary_file: str = os.path.join(
            os.path.expanduser(os.path.expandvars(os.path.abspath(input_dir))),
            "summarizer.txt",
        )
        index_file: str = os.path.join(
            os.path.expanduser(os.path.expandvars(os.path.abspath(input_dir))),
            "index.html",
        )
        if not os.path.exists(index_file):
            return True
        count_expected: int = -1
        count_actual: int = len(self._read_json_list(input_dir))
        if count_actual == 0:
            count_actual = -2
        if os.path.exists(summary_file):
            with open(summary_file, "r") as f:
                count_expected = int(f.readline().strip())
        return count_actual != count_expected

    def callback(self, input_dir: str) -> None:
        """Generate index.html with subdirectory links and JSON metadata entries."""
        input_dir = os.path.expanduser(os.path.expandvars(os.path.abspath(input_dir)))
        summary_file: str = os.path.join(input_dir, "summarizer.txt")
        index_file: str = os.path.join(input_dir, "index.html")
        print(f"Summarizing {index_file}")

        write_count: int = 0
        subdirectories: list[str] = self._read_subdirectory_list(input_dir)
        json_files: list[str] = self._read_json_list(input_dir)

        with open(index_file, "w") as f:
            f.write(SUMMARIZER_HEADER)
            for subdirectory in subdirectories:
                self._write_directory_to_html(f, input_dir, subdirectory)
            for json_file in json_files:
                self._write_json_to_html(f, json_file)
                write_count += 1
            if subdirectories:
                screen_file: str = os.path.join(input_dir, "screen.png")
                cmd: str = f'screencapture -x "{screen_file}"'
                os.system(cmd)
                f.write(
                    '<p><a href="screen.png"><img src="screen.png" '
                    'style="width:75%; display:block; margin:0 auto;" /></a></p>'
                )
                try:
                    df_result: subprocess.CompletedProcess[bytes] = subprocess.run(
                        ["df", "-h", "/"], capture_output=True, text=False
                    )
                    df_output: str = df_result.stdout.decode()
                except Exception:
                    df_output = ""
                f.write(f"<pre>{df_output}</pre>")
            f.write(SUMMARIZER_FOOTER)

        with open(summary_file, "w") as f:
            f.write(str(write_count))
