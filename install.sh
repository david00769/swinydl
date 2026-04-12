#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_ROOT="$REPO_ROOT/safari/.build"
BUILD_OUTPUT_DIR="$BUILD_ROOT/Debug"
DERIVED_DATA_DIR="$BUILD_ROOT/DerivedData"
APP_PATH="$BUILD_OUTPUT_DIR/SWinyDLSafariApp.app"
note() {
  printf '%s\n' "$1"
}

error_exit() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

show_install_plan() {
  cat <<EOF
SWinyDL installer

This script will:
- verify uv, ffmpeg, xcodegen, xcode-select, and Xcode first-launch readiness
- run uv sync
- bootstrap the staged CoreML model bundles if needed
- regenerate the Safari Xcode project
- build SWinyDLSafariApp.app into $BUILD_OUTPUT_DIR
- run 'swinydl doctor'
- open the built app and Safari so you can enable the unsigned Safari extension

Press Enter to continue, or Ctrl-C to cancel.
EOF
}

confirm_continue() {
  if [ -t 0 ]; then
    show_install_plan
    read -r
  fi
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || error_exit "$2"
}

ensure_xcode_ready() {
  require_command xcode-select "Xcode command line tools are required. Install Xcode or run xcode-select --install first."
  require_command xcodebuild "xcodebuild is required. Install Xcode or the Xcode command line tools first."

  if ! xcode-select -p >/dev/null 2>&1; then
    error_exit "Xcode command line tools are not configured. Install Xcode or run xcode-select --install, then re-run this installer."
  fi

  if ! xcodebuild -checkFirstLaunchStatus >/dev/null 2>&1; then
    error_exit "Xcode first-launch tasks are incomplete. Open Xcode once or run 'sudo xcodebuild -license accept' and 'sudo xcodebuild -runFirstLaunch', then re-run this installer."
  fi
}

require_command uv "uv is required. Install uv first."
require_command ffmpeg "ffmpeg is required. Install ffmpeg and ensure it is on PATH."
require_command xcodegen "xcodegen is required. Install xcodegen and ensure it is on PATH."
ensure_xcode_ready
confirm_continue

cd "$REPO_ROOT"

note "Syncing Python dependencies with uv..."
uv sync

VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
[ -x "$VENV_PYTHON" ] || error_exit "Expected uv to create $VENV_PYTHON, but it was not found."
"$VENV_PYTHON" - <<'PY' >/dev/null 2>&1 || error_exit "SWinyDL requires a Python 3.11 or newer virtual environment."
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY

note "Bootstrapping local CoreML model bundles..."
"$VENV_PYTHON" -m swinydl.main bootstrap-models

note "Generating the Safari Xcode project..."
xcodegen generate --spec safari/project.yml

note "Building SWinyDLSafariApp into $BUILD_OUTPUT_DIR ..."
mkdir -p "$BUILD_OUTPUT_DIR" "$DERIVED_DATA_DIR"
xcodebuild \
  -project safari/SWinyDLSafari.xcodeproj \
  -scheme SWinyDLSafariApp \
  -configuration Debug \
  -derivedDataPath "$DERIVED_DATA_DIR" \
  CONFIGURATION_BUILD_DIR="$BUILD_OUTPUT_DIR" \
  CODE_SIGNING_ALLOWED=NO \
  build

[ -d "$APP_PATH" ] || error_exit "Build completed without producing $APP_PATH."
[ -d "$APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex" ] || error_exit "The built app is missing the embedded Safari extension bundle."

note "Running SWinyDL doctor..."
"$VENV_PYTHON" -m swinydl.main doctor

note "Opening the built SWinyDL Safari app..."
open "$APP_PATH"
note "Opening Safari..."
open -a Safari

cat <<EOF

SWinyDL install completed.

Next steps:
1. In Safari, open Settings > Extensions.
2. Enable "SWinyDL Safari".
3. If the extension does not appear, enable Safari's Develop menu and turn on "Allow Unsigned Extensions".
4. Open a logged-in Canvas or Echo360 page in Safari.
5. Use the SWinyDL extension popup to load the course and launch jobs.

The built app is at:
  $APP_PATH

If you later update the repo from GitHub Releases, rebuild with:
  ./install.sh

EOF
