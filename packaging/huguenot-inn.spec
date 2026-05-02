# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Huguenot Inn macOS app bundle."""

from pathlib import Path
import importlib.util
import tomllib

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

APP_NAME = "Huguenot Inn"
BUNDLE_IDENTIFIER = "com.nikhilsomaru.huguenotinn"
PROJECT_ROOT = Path(SPECPATH).parent
ICON_PNG_PATH = PROJECT_ROOT / "packaging" / "assets" / "huguenot-inn-icon.png"
ICON_ICNS_PATH = PROJECT_ROOT / "packaging" / "assets" / "huguenot-inn-icon.icns"
ICON_PATH = ICON_ICNS_PATH if ICON_ICNS_PATH.exists() else ICON_PNG_PATH
ENTRY_PATH = PROJECT_ROOT / "packaging" / "pyinstaller_entry.py"
SRC_PATH = PROJECT_ROOT / "src"
VERSION = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())["project"]["version"]

generate_icons_spec = importlib.util.spec_from_file_location("generate_icons", PROJECT_ROOT / "packaging" / "generate_icons.py")
generate_icons_module = importlib.util.module_from_spec(generate_icons_spec)
generate_icons_spec.loader.exec_module(generate_icons_module)
GENERATED_ICON_PATHS = generate_icons_module.generate_icons(PROJECT_ROOT / "packaging" / "assets")

# tkinterdnd2 ships platform-specific tkdnd Tcl/native-library resources that
# PyInstaller may not infer from imports alone. Keep them explicit in the spec.
datas = collect_data_files("tkinterdnd2")
datas += collect_data_files("huguenot.persistence", includes=["migrations/*.sql"])
datas += [(str(ICON_PNG_PATH), "assets")]
datas += [(str(path), "assets") for path in GENERATED_ICON_PATHS]
hiddenimports = collect_submodules("tkinterdnd2")
hiddenimports += collect_submodules("docx2pdf")


a = Analysis(
    [str(ENTRY_PATH)],
    pathex=[str(SRC_PATH)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=str(ICON_PATH),
    bundle_identifier=BUNDLE_IDENTIFIER,
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
    },
)
