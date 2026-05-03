#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:-${GITHUB_REF_NAME:-}}"

if [ -z "$VERSION" ]; then
  VERSION="$(
    cd "$REPO_ROOT"
    python3 - <<'PY'
from swinydl.version import __version__
print(f"v{__version__}")
PY
  )"
fi

case "$VERSION" in
  v*) ;;
  *) VERSION="v$VERSION" ;;
esac

BUILD_ROOT="$REPO_ROOT/dist/build"
STAGE_PARENT="$REPO_ROOT/dist/release/$VERSION"
STAGE_ROOT="$STAGE_PARENT/SWinyDL"
DMG_PATH="$REPO_ROOT/dist/SWinyDL-$VERSION.dmg"
RUNNER_PACKAGE="$REPO_ROOT/swift/ParakeetCoreMLRunner"

rm -rf "$STAGE_PARENT" "$DMG_PATH"
mkdir -p "$STAGE_ROOT"

cd "$REPO_ROOT"

APP_PATH="$STAGE_ROOT/SWinyDLSafariApp.app"
"$REPO_ROOT/scripts/build_app.sh" \
  --configuration Release \
  --build-root "$BUILD_ROOT" \
  --output "$APP_PATH" \
  --version "${VERSION#v}"

[ -d "$APP_PATH" ] || {
  printf 'Expected built app at %s\n' "$APP_PATH" >&2
  exit 1
}
[ -d "$APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex" ] || {
  printf 'Built app is missing the embedded Safari extension.\n' >&2
  exit 1
}
[ -f "$APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex/Contents/Resources/manifest.json" ] || {
  printf 'Built app is missing the Safari WebExtension manifest.\n' >&2
  exit 1
}

command -v swift >/dev/null 2>&1 || {
  printf 'swift is required to build release CoreML runner binaries.\n' >&2
  exit 1
}
[ -d "$RUNNER_PACKAGE" ] || {
  printf 'Missing Swift runner package at %s\n' "$RUNNER_PACKAGE" >&2
  exit 1
}

printf 'Building release CoreML runner binaries...\n'
swift build --package-path "$RUNNER_PACKAGE" -c release --product parakeet-coreml-runner
swift build --package-path "$RUNNER_PACKAGE" -c release --product speaker-diarizer-coreml-runner
RUNNER_BIN_DIR="$(swift build --package-path "$RUNNER_PACKAGE" -c release --show-bin-path)"
mkdir -p "$STAGE_ROOT/bin"
for runner in parakeet-coreml-runner speaker-diarizer-coreml-runner; do
  [ -x "$RUNNER_BIN_DIR/$runner" ] || {
    printf 'Expected built runner at %s\n' "$RUNNER_BIN_DIR/$runner" >&2
    exit 1
  }
  ditto "$RUNNER_BIN_DIR/$runner" "$STAGE_ROOT/bin/$runner"
  /usr/bin/codesign --force --sign - "$STAGE_ROOT/bin/$runner"
done

for path in \
  install.sh \
  pyproject.toml \
  uv.lock \
  LICENSE \
  THIRD_PARTY_NOTICES.md
do
  [ -e "$path" ] || {
    printf 'Missing required release file: %s\n' "$path" >&2
    exit 1
  }
  ditto "$path" "$STAGE_ROOT/$path"
done
chmod +x "$STAGE_ROOT/install.sh"

ditto docs/release-install.md "$STAGE_ROOT/README.md"
ditto docs/user-guide.md "$STAGE_ROOT/USER-GUIDE.md"
ditto safari/SWinyDLSafariExtension/Resources/WebExtension "$STAGE_ROOT/WebExtension"
(
  cd "$STAGE_ROOT"
  /usr/bin/zip -qry SWinyDL-WebExtension.zip WebExtension
)

for dir in swinydl; do
  [ -d "$dir" ] || {
    printf 'Missing required runtime directory: %s\n' "$dir" >&2
    exit 1
  }
  rsync -a \
    --exclude '.cache/' \
    --exclude '__pycache__/' \
    "$dir" "$STAGE_ROOT/"
done
if [ -d vendor ]; then
  rsync -a \
    --exclude '.cache/' \
    --exclude '__pycache__/' \
    vendor "$STAGE_ROOT/"
else
  mkdir -p "$STAGE_ROOT/vendor"
fi

/usr/bin/xattr -cr "$STAGE_ROOT" 2>/dev/null || true

REQUIRED_PAYLOAD_PATHS=(
  "SWinyDLSafariApp.app"
  "SWinyDLSafariApp.app/Contents/PlugIns/SWinyDLSafariExtension.appex/Contents/Resources/manifest.json"
  "install.sh"
  "pyproject.toml"
  "uv.lock"
  "README.md"
  "USER-GUIDE.md"
  "WebExtension/manifest.json"
  "SWinyDL-WebExtension.zip"
  "bin/parakeet-coreml-runner"
  "bin/speaker-diarizer-coreml-runner"
  "swinydl"
  "swinydl/main.py"
  "swinydl/version.py"
  "vendor"
)
for required_path in "${REQUIRED_PAYLOAD_PATHS[@]}"; do
  if [ ! -e "$STAGE_ROOT/$required_path" ]; then
    printf 'Release package is missing required payload: %s\n' "$required_path" >&2
    exit 1
  fi
done
[ -x "$STAGE_ROOT/install.sh" ] || {
  printf 'Release install.sh is not executable.\n' >&2
  exit 1
}
[ -x "$STAGE_ROOT/bin/parakeet-coreml-runner" ] || {
  printf 'Release parakeet runner is not executable.\n' >&2
  exit 1
}
[ -x "$STAGE_ROOT/bin/speaker-diarizer-coreml-runner" ] || {
  printf 'Release speaker diarizer runner is not executable.\n' >&2
  exit 1
}

UNEXPECTED_ZIP="$(find "$STAGE_ROOT" -type f -name '*.zip' ! -name 'SWinyDL-WebExtension.zip' -print -quit)"
if [ -n "$UNEXPECTED_ZIP" ]; then
  printf 'Unexpected nested zip in release package: %s\n' "$UNEXPECTED_ZIP" >&2
  exit 1
fi

hdiutil create \
  -volname "SWinyDL $VERSION" \
  -srcfolder "$STAGE_PARENT" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

printf '%s\n' "$DMG_PATH"
