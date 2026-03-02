# SecurityCamProcessor (Python)

A pluggable post-processing pipeline for security camera videos. Recursively scans directories of video files and applies a chain of plugins: frame extraction via ffmpeg, animated GIF generation, AWS Rekognition tagging, and HTML summary pages. Also handles file movement and remuxing from camera output folders to a date-organized archive.

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) — frame extraction and video remuxing
- [ImageMagick](https://imagemagick.org/) (`convert`) — frame resizing
- [gifsicle](https://www.lcdf.org/gifsicle/) — animated GIF assembly
- AWS credentials configured for Rekognition (see Configuration below)

## Setup

### Option A: Setup script

```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

This checks for Python 3.10+, creates a `.venv` virtual environment, and installs all dependencies.

### Option B: Manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

Copy the sample settings file and fill in your AWS credentials:

```bash
cp settings-sample.yml settings.yml
```

Edit `settings.yml` with your values:

```yaml
access_key_id: YOUR_ACCESS_KEY
secret_access_key: YOUR_SECRET_KEY
region: us-west-2
flagged_tags:
  - human
  - humans
  - person
  - people
stopwords:
  - plant
  - building
  # ... additional tags to ignore
```

- `flagged_tags` — labels that indicate high-importance detections (e.g., people)
- `stopwords` — labels treated as background noise and excluded from important tags

## Usage

```bash
source .venv/bin/activate
python main.py <input_directory> <output_directory>
```

The pipeline:

1. Moves and remuxes stable `.mp4` files from `input_directory` into date-organized subfolders under `output_directory`
2. Scans `output_directory` for `.mp4` files, extracts frames, and runs:
   - Tagger — sends frames to AWS Rekognition, writes `.json` metadata
   - GifMaker — generates `.gif` timelapse thumbnails
   - Summarizer — produces `index.html` summary pages per directory

A process guard prevents multiple instances from running simultaneously.

## Project Structure

```
SecurityCamProcessor.Python/
├── main.py                 # CLI entry point and process guard
├── scanner.py              # Core engine, Callback/DirectoryCallback base classes
├── gifmaker.py             # GIF timelapse plugin
├── tagger.py               # AWS Rekognition tagging plugin
├── metadata.py             # Filename timestamp extraction
├── summarizer.py           # HTML summary generation plugin
├── mover.py                # File movement and remuxing
├── settings-sample.yml     # Sample configuration
├── requirements.txt        # Python dependencies
├── setup_venv.sh           # Virtual environment setup script
├── mypy.ini                # mypy strict mode configuration
├── py.typed                # PEP 561 type hint marker
├── archive.sh              # Archive older recordings to long-term storage
├── previews/               # Live camera preview system
│   ├── GenPreviews.sh      # Capture RTSP thumbnails
│   ├── index.html          # Preview grid page
│   ├── start_web_server.sh # Start nginx Docker container
│   └── config-example.sh   # Sample camera configuration
└── tests/                  # Test suite (pytest + Hypothesis)
```

## Testing

```bash
source .venv/bin/activate
pytest
```

## Type Checking

```bash
mypy --config-file mypy.ini *.py
```

All modules are fully type-annotated and pass `mypy --strict`.

## Archive Script

Move older date-stamped recording folders to a long-term archive location, keeping the five most recent:

```bash
bash archive.sh <recordings_folder> <archive_folder>
```

## Preview System

Capture live thumbnails from RTSP camera streams and serve them via a web page:

1. Copy `previews/config-example.sh` to `previews/config.sh` and configure your cameras
2. Run `previews/GenPreviews.sh` to capture thumbnails
3. Run `previews/start_web_server.sh` to serve the preview page on port 8080
