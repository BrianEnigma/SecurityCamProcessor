"""AWS Rekognition tagging plugin for SecurityCamProcessor."""

import json
import os
from typing import Any

import boto3
import yaml

from metadata import Metadata, MetadataResult
from scanner import Callback

SKIP_THRESHOLD: int = 120


class Tagger(Callback):
    """Sends sampled video frames to AWS Rekognition for label detection."""

    settings: dict[str, Any]
    client: Any  # boto3 Rekognition client
    tags: dict[str, int]
    flagged_tags: list[str]
    stopwords: list[str]
    previous_item_time: int
    partitions: int

    def __init__(self) -> None:
        super().__init__()
        self.tags = {}
        self.previous_item_time = -9999
        self.partitions = 5
        self.settings = {}
        self.flagged_tags = []
        self.stopwords = []
        if not self._load_settings():
            raise RuntimeError("bad config")

    def _load_settings(self) -> bool:
        """Load settings.yml and initialize boto3 Rekognition client."""
        with open("settings.yml", "r") as f:
            self.settings = yaml.safe_load(f)
        self.stopwords = self.settings.get("stopwords", [])
        self.flagged_tags = self.settings.get("flagged_tags", [])

        access_key: str = self.settings.get("access_key_id", "")
        secret_key: str = self.settings.get("secret_access_key", "")
        region: str = self.settings.get("region", "")

        if not access_key or not secret_key:
            print("AWS credentials not found in settings.yml")
            return False
        if not region:
            print("AWS region not found in settings.yml")
            return False

        self.client = boto3.client(
            "rekognition",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        return True

    def _add_tag(self, name: str, confidence: int) -> None:
        """Add or update a tag, keeping the highest confidence value."""
        name = name.lower()
        if name in self.tags:
            self.tags[name] = max(self.tags[name], confidence)
        else:
            self.tags[name] = confidence

    def _process_frame(self, filename: str) -> None:
        """Send a single frame to Rekognition and collect labels."""
        with open(filename, "rb") as f:
            contents: bytes = f.read(5000000)

        response: dict[str, Any] = self.client.detect_labels(
            Image={"Bytes": contents},
            MaxLabels=20,
            MinConfidence=70,
        )

        label_string: str = ""
        for label in response.get("Labels", []):
            name: str = label["Name"]
            confidence: int = int(label["Confidence"])
            label_string += f"'{name}:{confidence}%' "
            self._add_tag(name, confidence)
        print(f"{filename} : {label_string}")

    def _select_frames(self, sorted_frames: list[str]) -> list[str]:
        """Select a subset of frames for Rekognition analysis."""
        if len(sorted_frames) <= 6:
            return list(sorted_frames)

        check_frames: list[str] = []
        span: int = len(sorted_frames) // self.partitions
        check_frames.append(sorted_frames[5])
        counter: int = span - 1
        while counter < len(sorted_frames):
            check_frames.append(sorted_frames[counter])
            counter += span
        return check_frames

    def needs_processing(self, input_file: str) -> bool:
        """Return True if .json file does not exist for this input."""
        output_file: str = os.path.splitext(input_file)[0] + ".json"
        return not os.path.exists(output_file)

    def callback(self, input_file: str, frames: list[str]) -> None:
        """Process frames through Rekognition and write tagged JSON output."""
        self.tags = {}
        output_file: str = os.path.splitext(input_file)[0] + ".json"
        if not os.path.exists(input_file):
            return
        if os.path.exists(output_file):
            return

        print(f"{input_file} => {output_file}")

        flagged: dict[str, int] = {}
        important: dict[str, int] = {}
        ignored: dict[str, int] = {}

        times: MetadataResult = Metadata.extract_times(input_file)
        current_item_time: int = times["time_start"]

        sorted_frames: list[str] = sorted(frames)
        check_frames: list[str] = self._select_frames(sorted_frames)

        for frame in check_frames:
            self._process_frame(frame)

        for tag, percent in self.tags.items():
            if tag in self.flagged_tags:
                flagged[tag] = percent
            elif tag in self.stopwords:
                ignored[tag] = percent
            else:
                important[tag] = percent

        json_hash: dict[str, Any] = {
            "flagged_tags": flagged,
            "important_tags": important,
            "ignored_tags": ignored,
            "time_start": times["time_start"],
            "time_end": times["time_end"],
            "duration": times["duration"],
            "since": current_item_time - self.previous_item_time,
        }

        with open(output_file, "w") as f:
            f.write(json.dumps(json_hash, indent=4))

        self.previous_item_time = times["time_end"]
