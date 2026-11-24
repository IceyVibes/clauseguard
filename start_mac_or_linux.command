#!/usr/bin/env bash
# ClauseGuard - TRUE one-click starter for macOS / Linux.
# Double-click this file in Finder (macOS) or run `./start_mac_or_linux.command`.
#
# What this does, in order:
#   1. Creates a local Python virtual environment if one doesn't exist yet.
#   2. Installs the required packages (first run only; needs internet once).
#   3. Starts the local FastAPI backend and the demo website.
#   4. Opens Chrome with the ClauseGuard extension ALREADY LOADED - no manual
#      "Load unpacked" steps needed - using a separate, temporary Chrome
#      profile so it never touches your normal Chrome profile/tabs and
#      works even if you already have Chrome open elsewhere.
#
# No model training happens here - this expects backend/models/ to already
# contain the pre-trained classifier (copied over from the original machine).

set -e
cd "$(dirname "$0")"

echo "=== ClauseGuard - one-click start (no Docker/Podman needed) ==="

PYTHON_BIN="python3.11"
if ! command -v $PYTHON_BIN >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

if [ ! -d ".venv" ]; then
  echo "Setting up the environment for the first time (this can take a few minutes)..."
  "$PYTHON_BIN" -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip -q
  ./.venv/bin/pip install -r backend/requirements.txt -q
fi

if [ ! -f "backend/models/clause_classifier.joblib" ] || [ ! -d "backend/models/minilm" ]; then
  echo ""
  echo "ERROR: backend/models/ does not contain the trained model."
  echo "Copy the backend/models/ folder from the original machine (it already"
  echo "has minilm/, clause_classifier.joblib and model_metadata.json)."
  echo "Training from scratch on a low-memory laptop is not recommended."
  read -p "Press Enter to close..."
  exit 1
fi

echo "Starting the local API (http://127.0.0.1:8000) ..."
./.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > /tmp/clauseguard_api.log 2>&1 &
API_PID=$!

echo "Starting the demo website (http://127.0.0.1:5500) ..."
./.venv/bin/python demo/serve_demo.py > /tmp/clauseguard_demo.log 2>&1 &
DEMO_PID=$!

cleanup() {
  echo ""
  echo "Stopping ClauseGuard..."
  kill $API_PID $DEMO_PID 2>/dev/null
}
trap cleanup EXIT

sleep 6

EXTENSION_PATH="$(pwd)/extension"
CHROME_APP="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ -x "$CHROME_APP" ]; then
  echo "Launching Chrome with ClauseGuard already loaded (separate temporary profile)..."
  "$CHROME_APP" \
    --user-data-dir="/tmp/ClauseGuardChromeProfile" \
    --disable-extensions-except="$EXTENSION_PATH" \
    --load-extension="$EXTENSION_PATH" \
    --no-first-run --no-default-browser-check \
    "http://127.0.0.1:5500/index.html" &
else
  echo ""
  echo "Could not find Chrome automatically. Opening the Scenario Lab in your"
  echo "default browser instead - you'll need to load the extension manually:"
  echo "  1. Open chrome://extensions  2. Enable Developer mode"
  echo "  3. Click 'Load unpacked'  4. Select the 'extension' folder"
  open "http://127.0.0.1:5500/index.html" 2>/dev/null || xdg-open "http://127.0.0.1:5500/index.html" 2>/dev/null
fi

echo ""
echo "ClauseGuard is running."
echo "  Scenario Lab: http://127.0.0.1:5500/index.html"
echo "  API health:   http://127.0.0.1:8000/health"
echo ""
echo "Keep this window open while testing. Press Ctrl+C or close this window to stop."
wait
