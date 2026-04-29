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

rm -rf "$STAGE_PARENT" "$DMG_PATH"
mkdir -p "$STAGE_ROOT"

cd "$REPO_ROOT"

APP_PATH="$STAGE_ROOT/SWinyDLSafariApp.app"
"$REPO_ROOT/scripts/build_app.sh" \
  --configuration Release \
  --build-root "$BUILD_ROOT" \
  --output "$APP_PATH"

[ -d "$APP_PATH" ] || {
  printf 'Expected built app at %s\n' "$APP_PATH" >&2
  exit 1
}
[ -d "$APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex" ] || {
  printf 'Built app is missing the embedded Safari extension.\n' >&2
  exit 1
}

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

for dir in docs safari scripts swift swinydl vendor; do
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
