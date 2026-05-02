import importlib.util
import subprocess
from pathlib import Path

from huguenot.ui.about import ABOUT_METADATA, about_icon_path


def test_about_metadata_contains_required_notice() -> None:
    assert ABOUT_METADATA.application_name == "Huguenot Inn"
    assert ABOUT_METADATA.version
    assert "GPLv3" in ABOUT_METADATA.license_notice
    assert ABOUT_METADATA.author == "Nikhil Somaru"
    assert ABOUT_METADATA.contact == "nikhil@capebar.co.za"


def test_packaged_icon_source_matches_new_icon() -> None:
    source_size = Path("packaging/assets/huguenot-inn-icon.png").stat().st_size
    original_size = Path("examples/new_icon.png").stat().st_size
    assert source_size != original_size
    pixel = subprocess.run(
        ["magick", "packaging/assets/huguenot-inn-icon.png", "-format", "%[pixel:p{0,0}]", "info:"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert pixel == "srgba(0,0,0,0)"


def test_pyinstaller_spec_can_build_from_png_icon_source() -> None:
    spec = Path("packaging/huguenot-inn.spec").read_text()
    assert "ICON_PNG_PATH" in spec
    assert "ICON_ICNS_PATH if ICON_ICNS_PATH.exists() else ICON_PNG_PATH" in spec
    assert "generate_icons" in spec
    assert "huguenot-inn-icon.png" in spec


def test_about_uses_generated_small_icon() -> None:
    path = about_icon_path()
    assert path.name == "huguenot-inn-icon-64.png"
    assert path.exists()
    assert path.stat().st_size < Path("packaging/assets/huguenot-inn-icon.png").stat().st_size
    pixel = subprocess.run(
        ["magick", str(path), "-format", "%[pixel:p{0,0}]", "info:"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert pixel == "srgba(0,0,0,0)"


def test_icon_generation_sizes_are_declared() -> None:
    spec = importlib.util.spec_from_file_location("generate_icons", "packaging/generate_icons.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.ICON_SIZES == (16, 32, 64, 128, 256)
    for size in module.ICON_SIZES:
        assert Path(f"packaging/assets/huguenot-inn-icon-{size}.png").exists()
