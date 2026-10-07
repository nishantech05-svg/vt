#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer must be run on a Mac."
  read -r -p "Press Return to close."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required only to build the app. Install Python 3, then run this installer again."
  echo "Download: https://www.python.org/downloads/macos/"
  read -r -p "Press Return to close."
  exit 1
fi

echo "Building VoiceType for this Mac. The first build may take several minutes."
python3 -m venv .build-venv
source .build-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm voice_type.spec

APP_DIR="$HOME/Applications"
mkdir -p "$APP_DIR"
if [[ -d "$APP_DIR/VoiceType.app" ]]; then
  rm -rf "$APP_DIR/VoiceType.app"
fi
ditto "$PROJECT_DIR/dist/VoiceType.app" "$APP_DIR/VoiceType.app"
open "$APP_DIR/VoiceType.app"

echo "VoiceType is installed in $APP_DIR."
echo "Allow Microphone and Accessibility access when macOS asks."
read -r -p "Press Return to close."
