# PDF Bundle Numberer

Small Tkinter GUI app for creating numbered PDF bundles.

Features:

- drag and drop multiple PDFs
- combine them into one PDF
- add readable page numbers
- create PDF bookmarks / table of contents
- auto-detect case citations for authority bundles
- generate a Word authorities index
- create and reopen persisted matters with South African court metadata
- generate a matter bundle with a front authorities index, or keep the editable `.docx` index and PDF bundle separate

## Install from source

```bash
python -m pip install .
```

## Matters and local data

Use **File > New Matter** to create a matter, or **File > Open/Select Matter** to reopen one. Matters are stored in a local SQLite database under the operating system's app-data location for `Huguenot Inn`. On first startup, migrations create the schema and seed a curated South African court/header list. User-added courts and header lines are saved in the same database.

When no matter is active, bundle and authorities-index generation keeps the original behavior. When a matter is active:

- **Create combined numbered PDF** generates a single PDF with the matter-style authorities index at the front and page-range links into the bundle.
- **Create PDF bundle only** generates the numbered PDF bundle without a front index.
- **Create authorities index (.docx)** generates the editable matter index document.

LibreOffice is used when available for higher-fidelity `.docx` to PDF conversion of the matter index. If LibreOffice is not installed or conversion fails, the app prompts the user and falls back to a pure-Python PDF renderer.

## Development

The project uses `uv` for dependency management and the quality gates.

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
uv run bandit -r src
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
