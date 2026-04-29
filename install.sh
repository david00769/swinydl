#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_ROOT="$REPO_ROOT/safari/.build"
BUILD_OUTPUT_DIR="$BUILD_ROOT/Debug"
DERIVED_DATA_DIR="$BUILD_ROOT/DerivedData"
BUILD_APP_PATH="$BUILD_OUTPUT_DIR/SWinyDLSafariApp.app"
PREBUILT_APP_PATH="$REPO_ROOT/SWinyDLSafariApp.app"
BUILD_FROM_SOURCE=0

for arg in "$@"; do
  case "$arg" in
    --build-from-source)
      BUILD_FROM_SOURCE=1
      ;;
    -h|--help)
      cat <<EOF
Usage: ./install.sh [--build-from-source]

Without --build-from-source, this installer uses a prebuilt SWinyDLSafariApp.app
when one is present in the install folder. Source checkouts without a prebuilt
app still build the app locally.
EOF
      exit 0
      ;;
    *)
      printf 'Error: Unknown option: %s\n' "$arg" >&2
      exit 1
      ;;
  esac
done

if [ "$BUILD_FROM_SOURCE" -eq 0 ] && [ -d "$PREBUILT_APP_PATH" ]; then
  USE_PREBUILT_APP=1
  APP_PATH="$PREBUILT_APP_PATH"
else
  USE_PREBUILT_APP=0
  APP_PATH="$BUILD_APP_PATH"
fi

# Finder and other GUI launch paths often omit Homebrew and user-local tool paths.
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$PATH"
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
- install Homebrew if it is missing and you approve
- install uv and ffmpeg with Homebrew if they are missing and you approve
- run uv sync
- bootstrap the staged CoreML model bundles if needed
- run 'swinydl doctor'
- open the app and Safari so you can enable the unsigned Safari extension

EOF
  if [ "$USE_PREBUILT_APP" -eq 1 ]; then
    cat <<EOF
This install includes a prebuilt app, so it will not compile SWinyDL locally.

EOF
  else
    cat <<EOF
This install will also:
- install xcodegen with Homebrew if it is missing and you approve
- verify xcode-select and Xcode first-launch readiness
- regenerate the Safari Xcode project
- build SWinyDLSafariApp.app into $BUILD_OUTPUT_DIR

EOF
  fi
  cat <<EOF
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
  command -v "$1" >/dev/null 2>&1 || error_exit "$2 Current PATH: $PATH"
}

load_homebrew_shellenv() {
  if command -v brew >/dev/null 2>&1; then
    eval "$(brew shellenv)"
    return 0
  fi

  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
    return 0
  fi

  if [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
    return 0
  fi

  return 1
}

confirm_yes() {
  prompt="$1"
  default_yes="$2"

  if [ ! -t 0 ]; then
    return 1
  fi

  printf '%s ' "$prompt"
  read -r answer
  case "$answer" in
    [Yy]|[Yy][Ee][Ss])
      return 0
      ;;
    "")
      [ "$default_yes" = "yes" ]
      return
      ;;
    *)
      return 1
      ;;
  esac
}

ensure_homebrew() {
  load_homebrew_shellenv && return 0

  if ! confirm_yes "Homebrew is required but was not found. Install Homebrew now? [y/N]" "no"; then
    error_exit "Homebrew is required. Install it with: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  fi

  note "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  load_homebrew_shellenv || error_exit "Homebrew installation finished, but brew was still not found on PATH."
}

ensure_homebrew_tools() {
  missing_tools=""

  for tool in "$@"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      missing_tools="$missing_tools $tool"
    fi
  done

  [ -z "$missing_tools" ] && return 0

  ensure_homebrew

  if ! confirm_yes "Install missing required tools with Homebrew:$missing_tools? [Y/n]" "yes"; then
    error_exit "Missing required tools:$missing_tools. Install them with: brew install$missing_tools"
  fi

  note "Installing missing required tools with Homebrew:$missing_tools"
  brew install $missing_tools
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

clear_app_quarantine() {
  if command -v xattr >/dev/null 2>&1; then
    note "Clearing downloaded-file quarantine from the SWinyDL app if present..."
    xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || true
  fi
}

confirm_continue
if [ "$USE_PREBUILT_APP" -eq 1 ]; then
  ensure_homebrew_tools uv ffmpeg
else
  ensure_homebrew_tools uv ffmpeg xcodegen
fi
require_command uv "uv is required. Install uv first with 'brew install uv' or Astral's installer, then re-run this script."
require_command ffmpeg "ffmpeg is required. Install ffmpeg and ensure it is on PATH."
if [ "$USE_PREBUILT_APP" -eq 0 ]; then
  require_command xcodegen "xcodegen is required. Install xcodegen and ensure it is on PATH."
  ensure_xcode_ready
fi

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

if [ "$USE_PREBUILT_APP" -eq 1 ]; then
  note "Using prebuilt SWinyDLSafariApp at $APP_PATH ..."
else
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
fi

[ -d "$APP_PATH" ] || error_exit "Build completed without producing $APP_PATH."
[ -d "$APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex" ] || error_exit "The built app is missing the embedded Safari extension bundle."
clear_app_quarantine

note "Running SWinyDL doctor..."
"$VENV_PYTHON" -m swinydl.main doctor

note "Opening the SWinyDL Safari app..."
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

The app is at:
  $APP_PATH

If you later update from GitHub Releases, download the newer DMG and run:
  ./install.sh

To rebuild locally from source, run:
  ./install.sh --build-from-source

EOF
