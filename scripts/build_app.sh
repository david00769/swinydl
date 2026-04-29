#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIGURATION="Debug"
BUILD_ROOT="$REPO_ROOT/safari/.build"
OUTPUT_APP_PATH="$REPO_ROOT/SWinyDLSafariApp.app"

usage() {
  cat <<EOF
Usage: ./scripts/build_app.sh [--configuration Debug|Release] [--build-root PATH] [--output PATH]

Builds SWinyDLSafariApp.app and its embedded Safari extension from source.
The default output is:
  $OUTPUT_APP_PATH
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --configuration)
      [ "$#" -ge 2 ] || {
        printf 'Error: --configuration requires a value.\n' >&2
        exit 1
      }
      CONFIGURATION="$2"
      shift 2
      ;;
    --build-root)
      [ "$#" -ge 2 ] || {
        printf 'Error: --build-root requires a value.\n' >&2
        exit 1
      }
      BUILD_ROOT="$2"
      shift 2
      ;;
    --output)
      [ "$#" -ge 2 ] || {
        printf 'Error: --output requires a value.\n' >&2
        exit 1
      }
      OUTPUT_APP_PATH="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Error: Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$CONFIGURATION" in
  Debug|Release) ;;
  *)
    printf 'Error: --configuration must be Debug or Release.\n' >&2
    exit 1
    ;;
esac

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'Error: %s is required for source builds.\n' "$1" >&2
    exit 1
  }
}

require_command xcodegen
require_command xcodebuild

if ! xcode-select -p >/dev/null 2>&1; then
  printf 'Error: Xcode command line tools are not configured. Run xcode-select --install first.\n' >&2
  exit 1
fi

if ! xcodebuild -checkFirstLaunchStatus >/dev/null 2>&1; then
  printf "Error: Xcode first-launch tasks are incomplete. Open Xcode once or run 'sudo xcodebuild -license accept' and 'sudo xcodebuild -runFirstLaunch'.\n" >&2
  exit 1
fi

BUILD_OUTPUT_DIR="$BUILD_ROOT/$CONFIGURATION"
DERIVED_DATA_DIR="$BUILD_ROOT/DerivedData"
BUILT_APP_PATH="$BUILD_OUTPUT_DIR/SWinyDLSafariApp.app"

cd "$REPO_ROOT"

printf 'Generating Safari Xcode project...\n'
xcodegen generate --spec safari/project.yml

printf 'Building SWinyDLSafariApp.app (%s)...\n' "$CONFIGURATION"
mkdir -p "$BUILD_OUTPUT_DIR" "$DERIVED_DATA_DIR"
xcodebuild \
  -project safari/SWinyDLSafari.xcodeproj \
  -scheme SWinyDLSafariApp \
  -configuration "$CONFIGURATION" \
  -derivedDataPath "$DERIVED_DATA_DIR" \
  CONFIGURATION_BUILD_DIR="$BUILD_OUTPUT_DIR" \
  CODE_SIGNING_ALLOWED=NO \
  build

[ -d "$BUILT_APP_PATH" ] || {
  printf 'Error: Expected built app at %s\n' "$BUILT_APP_PATH" >&2
  exit 1
}
[ -d "$BUILT_APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex" ] || {
  printf 'Error: Built app is missing the embedded Safari extension.\n' >&2
  exit 1
}

printf 'Ad-hoc signing built app bundle...\n'
/usr/bin/codesign --force --deep --sign - "$BUILT_APP_PATH"
/usr/bin/codesign --verify --deep --strict "$BUILT_APP_PATH"

rm -rf "$OUTPUT_APP_PATH"
mkdir -p "$(dirname "$OUTPUT_APP_PATH")"
ditto "$BUILT_APP_PATH" "$OUTPUT_APP_PATH"

printf '%s\n' "$OUTPUT_APP_PATH"
