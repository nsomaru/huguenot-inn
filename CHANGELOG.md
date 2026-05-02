# Changelog

All notable changes to **Huguenot Inn** are documented here.

## [Unreleased]

### Added

- Added a tag-triggered GitHub Actions release workflow that builds unsigned Linux Flatpak, macOS DMG, and Windows MSI artifacts and publishes a GitHub release with generated notes.
- Added release-version and artifact-set validation helpers so pushed version tags must match the project/runtime version and releases attach exactly the three expected artifacts.
- Added Flatpak packaging metadata, generated Python dependency manifest support, and Windows PyInstaller/WiX MSI packaging configuration.

### Fixed

- Extended LibreOffice detection to cover Linux package paths, Linux Flatpak exports, and common Windows installation directories while preserving PATH and macOS bundle precedence.

### Tests

- Added regression coverage for release workflow shape, version/artifact validation, Flatpak packaging contracts, Windows MSI packaging contracts, macOS unsigned artifact naming, and Windows/Linux LibreOffice detection.

## [0.4.1a] - 2026-05-02

### Fixed

- Fixed PyInstaller startup migrations by bundling the `yoyo-migrations` entry-point metadata and SQLite backend module required for yoyo backend discovery in frozen builds.

### Tests

- Added regression coverage for PyInstaller yoyo SQLite backend packaging requirements.

## [0.4.0a] - 2026-05-02

### Fixed

- Fixed macOS/Tk application identity at root-window initialization so the app menu bar uses **Huguenot Inn** instead of inheriting the `python3` process name where supported.

### Tests

- Added regression coverage for pre-initialization Tk root naming while preserving existing macOS app-name and PyInstaller bundle display-name checks.

## [0.3.1a] - 2026-05-02

### Fixed

- Fixed duplicate-citation review launched from drag-and-drop by deferring duplicate handling until after the native drop callback returns.
- Hardened the duplicate-citation modal lifecycle so it waits for visibility before grabbing input and reliably releases the grab after a decision.

### Tests

- Added regression coverage for deferred drag-and-drop duplicate handling and duplicate modal grab/release behavior.

## [0.3.0a] - 2026-05-02

### Added

- Added duplicate authority warning flow when newly added PDFs have identical detected citations/titles.
  - Users can add the duplicate anyway, skip it, or skip all remaining duplicates in the add flow.
- Added matter-based output names and front-index ToC roots such as `first-applicant_v_first-respondent_AUTHORITIES_BUNDLE.pdf`.
- Added modular Microsoft Word/docx2pdf conversion support for Windows/macOS systems with Microsoft Word installed.

### Changed

- Default matter-index PDF rendering now uses ReportLab for deterministic output.
- Updated the main application window title to **Huguenot Inn**.
- Regenerated packaged icon assets from `examples/new_icon.png`.
- Removed automated icon background cleanup; provided PNGs are now treated as already background-removed.
- Increased DOCX tramline spacing and table-cell padding for more readable authorities indexes.
- Preserved existing no-matter bundle defaults and PDF bundle behavior.

### Fixed

- Fixed cramped DOCX matter headers where tramlines sat too close to the heading.
- Fixed generic matter output filenames by deriving defaults from the first bringing and opposing parties.

### Verification

- Planned verification: Ruff formatting, Ruff lint, Pyright, Pytest, and Bandit before release completion.

## [0.2.0a] - 2026-05-02

### Added

- Added an **Advanced** pane to the main window.
  - Users can now choose the PDF index renderer: **Automatic**, **LibreOffice**, or **ReportLab**.
  - Users can now choose the index font from a searchable system-font dropdown.
  - The default index output font is now **Times New Roman**, with deterministic fallbacks where a backend cannot use that exact face.
- Added **Help > About Huguenot Inn**.
  - Displays the application icon, current version, GPLv3 notice, author, and contact details.
  - Uses a generated smaller icon asset for the modal.
- Added packaged icon generation for the PyInstaller build.
  - Magick generates 16, 32, 64, 128, and 256 pixel icon variants from the main icon.
  - Generated icon variants are included as PyInstaller data assets.
- Added renderer/font settings code for resolving renderer choice, font fallback, and system font discovery.
- Added regression tests for renderer choice, font fallback, PDF links, DOCX structure, About metadata, icon packaging, and PyInstaller spec behavior.

### Changed

- Replaced the application icon with the new icon from `examples/new_icon.png`.
- Cleaned the icon by making only the outer white border transparent while preserving the white interior artwork.
- Matter bundle page numbering now starts at the first attached document, not at the front index/document-index pages.
  - Front index pages remain unnumbered.
  - Attached documents visibly start at page 1.
  - Existing no-matter bundle numbering behavior remains unchanged.
- Matter index page ranges now match the attached-document page-numbering scheme.
  - DOCX, LibreOffice-rendered PDF, and ReportLab-rendered PDF indexes use visible bundle page ranges starting from 1.
- Matter index headers now more closely follow `examples/header_example.docx`.
  - Court line 1 and court line 2 are rendered in all matter index outputs.
  - The parties header is constructed as a table rather than tab-aligned text.
  - The document heading uses horizontal “tram line” rules.
  - Tramlines align with the parties table edges in both LibreOffice/DOCX and ReportLab outputs.
  - ReportLab tramlines are spaced away from the heading text so they do not intersect it.
- Party ordinal suffixes now render as superscript in DOCX/LibreOffice and ReportLab matter headers.
- `CASE NO:` and its value are bold in all matter index output paths.
- DOCX/LibreOffice authorities tables now use fixed widths, cell margins, compact spacing, wrapping-friendly layout, and hanging indents for wrapped authority titles.
- ReportLab authorities tables now wrap long case names within the item cell and indent continuation lines for readability.
- Combined matter bundles now persist PDF outline/table-of-contents entries for the front index and every attached authority.
- Invisible index hyperlinks now target the correct physical pages while preserving visible page-number semantics.
- PyInstaller packaging now tolerates missing `.icns` by falling back to the PNG icon source and packaging the icon assets.

### Fixed

- Fixed missing PDF outline ToC entries in combined matter bundles.
- Fixed missing PDF outline ToC behavior when LibreOffice is used for the front index renderer.
- Fixed LibreOffice detection on macOS by checking common app-bundle executable locations and probing `--headless --version`.
- Fixed LibreOffice conversion reliability on macOS by using an isolated temporary user profile for headless conversion.
- Fixed DOCX/LibreOffice party ordinal suffixes rendering too low by using true superscript formatting at normal text size.
- Fixed ReportLab party ordinal suffixes by drawing the suffix as a superscript-style text segment.
- Fixed ReportLab heading tramlines intersecting the heading text.
- Fixed DOCX/LibreOffice table text overrun and unattractive row spacing.
- Fixed About modal icon sizing by using the generated 64 pixel asset.

### Verification

- Verified with Ruff formatting, Ruff lint, Pyright, Pytest, Bandit, PyInstaller build, and LibreOffice smoke artifacts.

## [0.1.0] - Initial release

### Added

- Added the core Tkinter desktop application for combining PDF files into a single numbered bundle.
- Added drag-and-drop PDF import using `tkinterdnd2`.
- Added controls for page number position, page number font size, and page number margin.
- Added readable page-number boxes directly onto combined PDF pages.
- Added PDF bookmark/table-of-contents generation for standard combined bundles.
- Added automatic title detection for authority/case PDFs.
- Added manual editing and ordering of PDF ToC/index item titles.
- Added move up, move down, remove, and clear list controls for selected PDFs.
- Added standalone Word authorities index generation.
- Added persisted matter support with local SQLite storage.
  - Matters can be created, reopened, selected, and cleared.
  - Matter data includes court name, optional second court header line, proceeding type, case number, bringing parties, and opposing parties.
  - Startup migrations create and update the local database non-interactively.
  - A curated South African court/header list is seeded for matter creation.
- Added matter-specific authorities index generation.
  - Matter indexes include court metadata, case number, party labels, document heading, authority rows, and page ranges.
  - Users can generate an editable `.docx` matter index.
  - Users can create a combined matter PDF bundle with a front authorities index.
- Added LibreOffice-backed `.docx` to PDF conversion for higher-fidelity matter index rendering when LibreOffice is available.
- Added a pure-Python ReportLab PDF renderer fallback when LibreOffice is unavailable.
- Added PyMuPDF-based PDF combining, numbering, bookmark, link, and page-count utilities.
- Added macOS packaging support with PyInstaller and a DMG build script.
- Added packaged migration files so startup database migrations work in installed builds.
- Added project quality gates for formatting, linting, type checking, testing, and static security scanning.
