# PDF Bundle Numberer

Small Tkinter GUI app for creating numbered PDF bundles.

Features:

- drag and drop multiple PDFs
- combine them into one PDF
- add readable page numbers
- create PDF bookmarks / table of contents
- auto-detect case citations for authority bundles
- generate a Word authorities index

## Install from source

```bash
python -m pip install .
```

## Build the macOS DMG

The packaging flow creates an unsigned Apple Silicon macOS disk image for **Huguenot Inn**.

### Prerequisites

- Apple Silicon Mac (`arm64`)
- Python 3.11 or newer
- An active virtual environment
- macOS command line tools that provide `hdiutil`, `sips`, and `iconutil`

Install the application and build-only packaging tools:

```bash
python -m pip install -e ".[packaging]"
```

Build the DMG:

```bash
scripts/build_macos_dmg.sh
```

The output is written to `dist/Huguenot-Inn-<version>-macOS-arm64.dmg`.

### DMG layout

The first-pass DMG uses a basic drag-to-Applications layout:

- volume name: `Huguenot Inn`
- root item: `Huguenot Inn.app`
- root item: `Applications` symlink pointing to `/Applications`

Custom Finder backgrounds, saved window positioning, code signing, notarization, CI automation, Intel builds, and universal builds are intentionally out of scope for this packaging pass.

### Install from the DMG

1. Open the generated `.dmg`.
2. Drag `Huguenot Inn.app` onto `Applications`.
3. Launch `Huguenot Inn` from Applications.

### Opening the unsigned app

This app is not code signed or notarized in the first packaging pass. macOS Gatekeeper may warn that it cannot verify the developer.

If macOS blocks the first launch, use one of Apple's standard unsigned-app flows:

- Control-click or right-click `Huguenot Inn.app`, choose **Open**, then confirm **Open**.
- Or open **System Settings → Privacy & Security** and use the **Open Anyway** option for `Huguenot Inn` after the blocked launch attempt.

Only open apps from sources you trust.

### Verify the DMG shape

After building, you can verify the agreed artifact shape without running app functionality:

```bash
DMG="dist/Huguenot-Inn-0.1.0-macOS-arm64.dmg"
hdiutil attach "$DMG"
ls -la "/Volumes/Huguenot Inn"
test -d "/Volumes/Huguenot Inn/Huguenot Inn.app"
test "$(readlink "/Volumes/Huguenot Inn/Applications")" = "/Applications"
hdiutil detach "/Volumes/Huguenot Inn"
```
