# Huguenot Inn

Huguenot Inn is a small Tkinter desktop app for creating numbered PDF bundles and South African litigation authorities indexes.

## Features

- Drag and drop multiple PDF, DOCX, or RTF source documents into the bundle list.
- Reorder, remove, clear, edit titles, add separator headings, and auto-detect title-cased South African authority/case citations, including common Afrikaans particles.
- Combine PDFs into a **Final Court Bundle** numbered PDF.
- Create a **Counsel's Bundle** with per-source flag colours, opaque coloured number boxes, coloured page-range markers, and physical flag-position markers.
- Add readable page numbers with configurable position, size, and margin.
- Create PDF bookmarks / table of contents for combined bundles, including separator sections where added.
- Generate a standalone Word authorities index with page ranges.
- Run **AI Analyse** to cache Docling document IR locally in parquet; the **Analysis** column shows whether each source is missing, cached, or currently being analysed.
- Create and reopen persisted matters with South African court metadata.
- Configure saved flag colours from **Tools > Flags** and inspect/clear local cache usage from **Tools > Disk usage**.
- Generate a matter bundle with a front authorities index, or keep the editable `.docx` index and PDF bundle separate.
- Create invisible hyperlinks from front-index rows to the correct authority pages in the combined PDF.
- Use internal roman page labels for front-index pages while bundled authorities restart at Arabic page 1.
- Choose the PDF index renderer from **ReportLab (default)**, **LibreOffice**, or **Microsoft Word**.
- Choose the index output font from a searchable system-font dropdown; Times New Roman is the default with safe backend fallbacks.
- Render matter headers with court lines, bold case number, party tables, superscript party ordinals, and tramline heading rules based on `examples/header_example.docx`.
- Use deterministic ReportLab PDF rendering by default, with explicit LibreOffice or Microsoft Word/docx2pdf conversion when available.
- Warn when newly added PDFs appear to duplicate an authority already in the list, with **Add Anyway**, **Skip**, and **Skip all N duplicates** choices.
- Display application/version/license details from **Help > About Huguenot Inn**.

## Install from source

```bash
python -m pip install .
```

## Matters and local data

Use **File > New Matter** to create a matter, or **File > Open/Select Matter** to reopen one. Matters are stored in a local SQLite database under the operating system's app-data location for `Huguenot Inn`. On first startup, migrations create the schema and seed a curated South African court/header list. User-added courts and header lines are saved in the same database.

When no matter is active, bundle and authorities-index generation keeps the original no-matter behavior. When a matter is active:

- **Final Court Bundle** generates the existing single PDF with the matter-style authorities index at the front, page-range links into the bundle, PDF outline ToC entries, and visible page numbering that starts at the first attached authority document. Matter outputs default to filenames such as `first-applicant_v_first-respondent_AUTHORITIES_BUNDLE.pdf`.
- **Counsel's Bundle** generates a colour-flagged bundle for physical preparation, using the saved flag palette for page-number boxes, page-range right borders, and printable flag marker positions.
- **Create PDF bundle only** generates the numbered PDF bundle without a front index.
- **Create authorities index (.docx)** generates the editable matter index document.

ReportLab is the default renderer for matter-index PDFs. LibreOffice remains available as an explicit higher-fidelity `.docx` to PDF conversion option; the app detects LibreOffice from PATH, common macOS app-bundle locations, Linux package/Flatpak export locations, and common Windows install directories, probes whether it can run headlessly, and uses an isolated temporary LibreOffice profile during conversion. Microsoft Word conversion is also available through `docx2pdf` on Windows/macOS when Microsoft Word is installed; it is not a Linux renderer.

## Advanced output options

The **Advanced** pane controls matter-index output behavior:

- **PDF index renderer**
  - **ReportLab (default)**: use the pure-Python renderer directly.
  - **LibreOffice**: require LibreOffice and fail visibly if conversion is unavailable.
  - **Microsoft Word**: use `docx2pdf`, which requires Microsoft Word on Windows or macOS.
- **Index font**
  - Defaults to Times New Roman.
  - Provides a searchable dropdown of system fonts.
  - DOCX/LibreOffice output uses the chosen family directly.
  - ReportLab maps common choices to built-in PDF fonts and falls back deterministically when needed.
- **Disable physical flag markers**
  - Turns off printable sticky-note marker positions for Counsel's Bundle while preserving the colour styling.

## Output formatting

Matter index outputs aim to match the supplied header example closely:

- first and second court header lines are rendered;
- `CASE NO:` and the case number are bold;
- parties are rendered in a two-column table instead of tabbed text;
- party ordinal suffixes such as `1st`, `2nd`, and `3rd` use superscript;
- document headings use horizontal tramline rules aligned to the parties table;
- tramline rules are spaced away from the heading so the header has more breathing room;
- long authority titles wrap inside table cells;
- wrapped authority titles receive a small hanging indent;
- DOCX table cells include extra padding for readability;
- DOCX, LibreOffice-rendered PDF, and ReportLab-rendered PDF indexes all include page ranges.

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
- macOS command line tools that provide `hdiutil`, `sips`, `iconutil`, and `magick`

Install the application and build-only packaging tools:

```bash
python -m pip install -e ".[packaging]"
```

Build the DMG:

```bash
scripts/build_macos_dmg.sh
```

The output is written to `dist/Huguenot-Inn-<version>-macOS-arm64.dmg`.

## Release workflow

Pushing a version tag such as `v0.4.6.2a` runs `.github/workflows/release.yml`. The tag version must match both `pyproject.toml` and `huguenot.__version__`. CI generates the Flatpak Python dependency manifest from `packaging/flatpak/requirements.txt`, builds unsigned artifacts for the three supported formats, and publishes a GitHub release with generated notes:

- `Huguenot-Inn-<version>-Linux-x86_64.flatpak`
- `Huguenot-Inn-<version>-macOS-arm64.dmg`
- `Huguenot-Inn-<version>-Windows-x64.msi`

The release job validates that exactly those three artifacts are present before calling `gh release create --generate-notes --verify-tag`. Signing, notarization, auto-updates, and non-Flatpak Linux packages are intentionally out of scope for this pass.


The PyInstaller build includes packaged migration files, application icon assets, and Docling runtime modules/data/metadata. Set `HUGUENOT_DOCLING_SMOKE_PDF=/path/to/file.pdf` on the packaged executable to run a non-GUI Docling smoke analysis before release. During the PyInstaller build, `packaging/generate_icons.py` uses Magick to generate smaller icon PNGs from the committed icon source for packaged UI use, preserving existing generated files when their bytes are unchanged. The source PNG is expected to already have its background removed; the build does not perform background cleanup.

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

This app is not code signed or notarized in this packaging pass. macOS Gatekeeper may warn that it cannot verify the developer.

If macOS blocks the first launch, use one of Apple's standard unsigned-app flows:

- Control-click or right-click `Huguenot Inn.app`, choose **Open**, then confirm **Open**.
- Or open **System Settings → Privacy & Security** and use the **Open Anyway** option for `Huguenot Inn` after the blocked launch attempt.

Only open apps from sources you trust.

### Verify the DMG shape

After building, you can verify the agreed artifact shape without running app functionality:

```bash
DMG="dist/Huguenot-Inn-0.3.0a-macOS-arm64.dmg"
hdiutil attach "$DMG"
ls -la "/Volumes/Huguenot Inn"
test -d "/Volumes/Huguenot Inn/Huguenot Inn.app"
test "$(readlink "/Volumes/Huguenot Inn/Applications")" = "/Applications"
hdiutil detach "/Volumes/Huguenot Inn"
```
