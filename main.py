#!/usr/bin/env python3
"""CLI entry point and process guard for SecurityCamProcessor."""

import os
import subprocess
import sys

import yaml

from gifmaker import GifMaker
from mover import Mover
from mover_ftp import MoverFtp
from scanner import Scanner
from summarizer import Summarizer
from tagger import Tagger


def is_already_running() -> bool:
    """Check if another instance of the processor is already running via pgrep."""
    result: subprocess.CompletedProcess[bytes] = subprocess.run(
        ["pgrep", "-f", "main.py"],
        capture_output=True,
    )
    output: str = result.stdout.decode().strip()
    return len(output) > 0


def _ftp_source_folder() -> str:
    """Return the expanded FTP source folder from settings.yml, or "" if unset."""
    try:
        with open("settings.yml", "r") as f:
            settings: dict[str, object] = yaml.safe_load(f) or {}
    except OSError:
        return ""
    raw: object = settings.get("ftp_source_folder", "")
    if not isinstance(raw, str) or not raw:
        return ""
    return os.path.expanduser(os.path.expandvars(raw))


def main() -> None:
    """Run the full SecurityCamProcessor pipeline."""
    if len(sys.argv) != 3:
        print("Usage: main.py {input directory} {output directory}")
        sys.exit(1)

    if is_already_running():
        print("This script is already running.")
        sys.exit(0)

    input_dir: str = sys.argv[1]
    output_dir: str = sys.argv[2]

    mover: Mover = Mover(input_dir, output_dir, 2)
    mover.move()

    ftp_source: str = _ftp_source_folder()
    if ftp_source and os.path.isdir(ftp_source):
        mover_ftp: MoverFtp = MoverFtp(ftp_source, output_dir, 2)
        mover_ftp.move()

    tagger: Tagger = Tagger()
    gifmaker: GifMaker = GifMaker()
    summarizer: Summarizer = Summarizer()
    scanner: Scanner = Scanner(output_dir, ".mp4", [tagger, gifmaker], [summarizer])
    scanner.scan()


if __name__ == "__main__":
    main()
