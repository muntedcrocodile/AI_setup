#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing packages..."
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE"
fi

echo "Setup complete."