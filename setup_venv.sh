#!/usr/bin/env bash
set -euo pipefail

PYTHON_MIN_VERSION="3.10"
VENV_DIR=".venv"

# Check Python 3.10+ is available
python3 -c "
import sys
if sys.version_info < (3, 10):
    print(f'Error: Python ${PYTHON_MIN_VERSION}+ required, found {sys.version}')
    sys.exit(1)
print(f'Found Python {sys.version}')
"

# Create virtual environment
python3 -m venv "$VENV_DIR"
echo "Created virtual environment in $VENV_DIR"

# Activate and install dependencies
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Virtual environment ready. Activate with:"
echo "  source $VENV_DIR/bin/activate"
