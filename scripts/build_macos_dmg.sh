#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Huguenot Inn"
APP_BUNDLE="dist/${APP_NAME}.app"
ICON_PNG="packaging/assets/huguenot-inn-icon.png"
ICON_ICNS="packaging/assets/huguenot-inn-icon.icns"
ICONSET="build/huguenot-inn.iconset"
DMG_STAGE="build/dmg-root"
SPEC_FILE="packaging/huguenot-inn.spec"

fail() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

replace_if_changed() {
  local source_path="$1"
  local target_path="$2"
  if [[ -f "$target_path" ]] && cmp -s "$source_path" "$target_path"; then
    rm -f "$source_path"
    return
  fi
  mv "$source_path" "$target_path"
}

[[ "$(uname -s)" == "Darwin" ]] || fail "macOS is required to build the Huguenot Inn DMG."
[[ "$(uname -m)" == "arm64" ]] || fail "Only Apple Silicon (arm64) macOS builds are in scope for this first pass."

command_exists python || fail "python is required. Create/activate a Python 3.11+ virtual environment first."
command_exists pyinstaller || fail "PyInstaller is missing. Install build tooling with: python -m pip install -e '.[packaging]'"
command_exists hdiutil || fail "hdiutil is required and should be available on macOS."
command_exists sips || fail "sips is required to convert the app icon and should be available on macOS."
command_exists iconutil || fail "iconutil is required to create .icns icons and should be available on macOS."

[[ -f "$ICON_PNG" ]] || fail "Missing committed PNG icon source: $ICON_PNG"
[[ -f "$SPEC_FILE" ]] || fail "Missing PyInstaller spec: $SPEC_FILE"

VERSION="$(python - <<'PY'
from pathlib import Path
import tomllib
with Path('pyproject.toml').open('rb') as f:
    print(tomllib.load(f)['project']['version'])
PY
)"
DMG_PATH="dist/Huguenot-Inn-${VERSION}-macOS-arm64.dmg"

printf 'Building %s %s for macOS arm64...\n' "$APP_NAME" "$VERSION"

rm -rf build "dist/${APP_NAME}" "$APP_BUNDLE" "$DMG_STAGE" "$DMG_PATH"
mkdir -p "$ICONSET" "$DMG_STAGE" dist

# Deterministically convert the committed PNG source into a macOS .icns file.
ICON_SIZES=(
  "16 16 icon_16x16.png"
  "32 32 icon_16x16@2x.png"
  "32 32 icon_32x32.png"
  "64 64 icon_32x32@2x.png"
  "128 128 icon_128x128.png"
  "256 256 icon_128x128@2x.png"
  "256 256 icon_256x256.png"
  "512 512 icon_256x256@2x.png"
  "512 512 icon_512x512.png"
  "1024 1024 icon_512x512@2x.png"
)
for icon_size in "${ICON_SIZES[@]}"; do
  read -r height width filename <<<"$icon_size"
  tmp_icon="$ICONSET/${filename}.tmp"
  sips -z "$height" "$width" "$ICON_PNG" --out "$tmp_icon" >/dev/null
  replace_if_changed "$tmp_icon" "$ICONSET/$filename"
done
TMP_ICON_ICNS="${ICON_ICNS}.tmp"
iconutil -c icns "$ICONSET" -o "$TMP_ICON_ICNS"
replace_if_changed "$TMP_ICON_ICNS" "$ICON_ICNS"

pyinstaller --noconfirm --clean "$SPEC_FILE"

[[ -d "$APP_BUNDLE" ]] || fail "PyInstaller did not create $APP_BUNDLE"

cp -R "$APP_BUNDLE" "$DMG_STAGE/"
ln -s /Applications "$DMG_STAGE/Applications"

hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$DMG_STAGE" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

[[ -s "$DMG_PATH" ]] || fail "DMG was not created or is empty: $DMG_PATH"

printf 'Created %s\n' "$DMG_PATH"
