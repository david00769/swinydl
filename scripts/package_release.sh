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
BUILD_OUTPUT_DIR="$BUILD_ROOT/Release"
DERIVED_DATA_DIR="$BUILD_ROOT/DerivedData"
STAGE_PARENT="$REPO_ROOT/dist/release/$VERSION"
STAGE_ROOT="$STAGE_PARENT/SWinyDL"
DMG_PATH="$REPO_ROOT/dist/SWinyDL-$VERSION.dmg"

rm -rf "$STAGE_PARENT" "$DMG_PATH"
mkdir -p "$BUILD_OUTPUT_DIR" "$DERIVED_DATA_DIR" "$STAGE_ROOT"

cd "$REPO_ROOT"

xcodegen generate --spec safari/project.yml
xcodebuild \
  -project safari/SWinyDLSafari.xcodeproj \
  -scheme SWinyDLSafariApp \
  -configuration Release \
  -derivedDataPath "$DERIVED_DATA_DIR" \
  CONFIGURATION_BUILD_DIR="$BUILD_OUTPUT_DIR" \
  CODE_SIGNING_ALLOWED=NO \
  build

APP_PATH="$BUILD_OUTPUT_DIR/SWinyDLSafariApp.app"
[ -d "$APP_PATH" ] || {
  printf 'Expected built app at %s\n' "$APP_PATH" >&2
  exit 1
}
[ -d "$APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex" ] || {
  printf 'Built app is missing the embedded Safari extension.\n' >&2
  exit 1
}

/usr/bin/codesign --force --deep --sign - "$APP_PATH"
/usr/bin/codesign --verify --deep --strict "$APP_PATH"

ditto "$APP_PATH" "$STAGE_ROOT/SWinyDLSafariApp.app"

for path in \
  install.sh \
  run.sh \
  app.py \
  swinydl.py \
  pyproject.toml \
  uv.lock \
  README.md \
  LICENSE \
  THIRD_PARTY_NOTICES.md
do
  [ -e "$path" ] && ditto "$path" "$STAGE_ROOT/$path"
done

for dir in docs safari swift swinydl vendor; do
  [ -d "$dir" ] && rsync -a \
    --exclude '.build/' \
    --exclude '.cache/' \
    --exclude 'DerivedData/' \
    --exclude '__pycache__/' \
    --exclude 'xcuserdata/' \
    --exclude '*.xcuserstate' \
    --exclude 'safari/.build/' \
    "$dir" "$STAGE_ROOT/"
done

/usr/bin/xattr -cr "$STAGE_ROOT" 2>/dev/null || true

hdiutil create \
  -volname "SWinyDL $VERSION" \
  -srcfolder "$STAGE_PARENT" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

printf '%s\n' "$DMG_PATH"
