#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_SCRIPT="$REPO_ROOT/scripts/build_app.sh"
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

Without --build-from-source, this installer requires a prebuilt
SWinyDLSafariApp.app in the install folder. To compile the Safari app wrapper,
run ./scripts/build_app.sh first, or use ./install.sh --build-from-source.
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
  APP_PATH="$PREBUILT_APP_PATH"
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
- ad-hoc sign and verify the Safari app bundle
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
- run ./scripts/build_app.sh to regenerate the Safari Xcode project
- build SWinyDLSafariApp.app into this install folder

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

register_safari_extension() {
  EXTENSION_PATH="$APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex"
  LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"

  note "Registering the SWinyDL Safari extension with macOS..."
  if [ -x "$LSREGISTER" ]; then
    "$LSREGISTER" -f -R -trusted "$APP_PATH" 2>/dev/null || true
  fi

  if command -v pluginkit >/dev/null 2>&1; then
    pluginkit -a "$EXTENSION_PATH" 2>/dev/null || true
    if pluginkit -mAvvv -p com.apple.Safari.web-extension 2>/dev/null | grep -q "com.davidsiroky.swinydl.SafariApp.Extension"; then
      note "Safari can see the SWinyDL extension. Enable it in Safari Settings > Extensions."
    else
      note "Safari has not listed the extension yet. Open the SWinyDL Safari app once, then check Safari Settings > Extensions."
    fi
  fi
}

require_prebuilt_or_explicit_build() {
  if [ "$BUILD_FROM_SOURCE" -eq 1 ]; then
    if [ ! -x "$BUILD_SCRIPT" ]; then
      cat >&2 <<EOF
Error: This runtime release folder does not include source-build files.

Developer source build:
  Clone https://github.com/david00769/swinydl, then run ./install.sh --build-from-source
  from the source checkout.
EOF
      exit 1
    fi
    return 0
  fi

  if [ -d "$PREBUILT_APP_PATH" ]; then
    return 0
  fi

  cat >&2 <<EOF
Error: This folder does not contain a prebuilt SWinyDLSafariApp.app.

Normal install:
  Download the latest SWinyDL-vX.Y.Z.dmg from GitHub Releases, open it, drag the SWinyDL
  folder out of the DMG, then run ./install.sh from that copied folder.

Developer source build:
  Run ./scripts/build_app.sh first, then run ./install.sh.
  You can also use ./install.sh --build-from-source as a shortcut.
EOF
  exit 1
}

sign_app_bundle() {
  if [ ! -x /usr/bin/codesign ]; then
    note "codesign was not found; skipping local ad-hoc app signing."
    return 0
  fi

  note "Ad-hoc signing the SWinyDL app bundle..."
  EXTENSION_PATH="$APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex"
  SIGNING_TMP_DIR="$(mktemp -d)"
  APP_ENTITLEMENTS="$SIGNING_TMP_DIR/app.entitlements.plist"
  EXTENSION_ENTITLEMENTS="$SIGNING_TMP_DIR/extension.entitlements.plist"

  if ! /usr/bin/codesign -d --entitlements :- "$EXTENSION_PATH" > "$EXTENSION_ENTITLEMENTS" 2>/dev/null; then
    rm -rf "$SIGNING_TMP_DIR"
    error_exit "Unable to read the bundled extension entitlements. Download the latest DMG, or rebuild from source before running install.sh."
  fi

  if ! /usr/bin/codesign -d --entitlements :- "$APP_PATH" > "$APP_ENTITLEMENTS" 2>/dev/null; then
    rm -rf "$SIGNING_TMP_DIR"
    error_exit "Unable to read the bundled app entitlements. Download the latest DMG, or rebuild from source before running install.sh."
  fi

  if ! /usr/bin/codesign --force --sign - --entitlements "$EXTENSION_ENTITLEMENTS" "$EXTENSION_PATH"; then
    rm -rf "$SIGNING_TMP_DIR"
    error_exit "Unable to sign $EXTENSION_PATH. If you are installing from the DMG, drag the SWinyDL folder out of the DMG first and run ./install.sh from the copied folder."
  fi

  if ! /usr/bin/codesign --force --sign - --entitlements "$APP_ENTITLEMENTS" "$APP_PATH"; then
    rm -rf "$SIGNING_TMP_DIR"
    error_exit "Unable to sign $APP_PATH. If you are installing from the DMG, drag the SWinyDL folder out of the DMG first and run ./install.sh from the copied folder."
  fi
  rm -rf "$SIGNING_TMP_DIR"

  /usr/bin/codesign --verify --deep --strict "$APP_PATH" || error_exit "The SWinyDL app bundle did not pass signature verification."
}

require_prebuilt_or_explicit_build
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
  note "Building SWinyDLSafariApp from source..."
  "$BUILD_SCRIPT"
fi

[ -d "$APP_PATH" ] || error_exit "Build completed without producing $APP_PATH."
[ -d "$APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex" ] || error_exit "The built app is missing the embedded Safari extension bundle."
[ -f "$APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex/Contents/Resources/manifest.json" ] || error_exit "The Safari extension is missing its WebExtension manifest. Download the latest DMG, or rebuild with ./scripts/build_app.sh."
sign_app_bundle
clear_app_quarantine
register_safari_extension

note "Running SWinyDL doctor..."
"$VENV_PYTHON" -m swinydl.main doctor

note "Opening the SWinyDL Safari app..."
open "$APP_PATH"
note "Opening Safari..."
open -a Safari

cat <<EOF

SWinyDL install completed.

Next steps:
1. In Safari, open Settings > Advanced and turn on "Show features for web developers".
2. Open Settings > Developer and turn on "Allow unsigned extensions". macOS will ask for your password.
3. Open Settings > Extensions and enable "SWinyDL Safari".
4. If the extension does not appear, quit and reopen the SWinyDL Safari app from this folder, or run ./install.sh again.
5. Open a logged-in Canvas or Echo360 page in Safari.
6. Use the SWinyDL extension popup to load the course and launch jobs.

Safari resets "Allow unsigned extensions" when Safari quits, so repeat steps 2
and 3 after each Safari restart while SWinyDL is unsigned.

Do not double-click the .appex file directly. Safari discovers the extension
through the containing SWinyDLSafariApp.app after that app has been opened.

The app is at:
  $APP_PATH

If you later update from GitHub Releases, download the newer DMG and run:
  ./install.sh

To rebuild locally from source, run:
  ./install.sh --build-from-source

EOF
