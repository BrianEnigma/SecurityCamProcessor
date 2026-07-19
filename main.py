#!/usr/bin/env python3
"""CLI entry point and process guard for SecurityCamProcessor."""

import subprocess
import sys

from gifmaker import GifMaker
from mover import Mover
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

    tagger: Tagger = Tagger()
    gifmaker: GifMaker = GifMaker()
    summarizer: Summarizer = Summarizer()
    scanner: Scanner = Scanner(output_dir, ".mp4", [tagger, gifmaker], [summarizer])
    scanner.scan()


if __name__ == "__main__":
    main()
