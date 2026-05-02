import importlib.util
from pathlib import Path

from huguenot.ui.about import ABOUT_METADATA, about_icon_path


def test_about_metadata_contains_required_notice() -> None:
    assert ABOUT_METADATA.application_name == "Huguenot Inn"
    assert ABOUT_METADATA.version
    assert "GPLv3" in ABOUT_METADATA.license_notice
    assert ABOUT_METADATA.author == "Nikhil Somaru"
    assert ABOUT_METADATA.contact == "nikhil@capebar.co.za"


def test_packaged_icon_source_matches_new_icon() -> None:
    assert Path("packaging/assets/huguenot-inn-icon.png").read_bytes() == Path("examples/new_icon.png").read_bytes()


def test_pyinstaller_spec_can_build_from_png_icon_source() -> None:
    spec = Path("packaging/huguenot-inn.spec").read_text()
    assert "ICON_PNG_PATH" in spec
    assert "ICON_ICNS_PATH if ICON_ICNS_PATH.exists() else ICON_PNG_PATH" in spec
    assert "generate_icons" in spec
    assert "huguenot-inn-icon.png" in spec
    assert 'collect_submodules("docx2pdf")' in spec


def test_about_uses_generated_small_icon() -> None:
    path = about_icon_path()
    assert path.name == "huguenot-inn-icon-64.png"
    assert path.exists()
    assert path.stat().st_size < Path("packaging/assets/huguenot-inn-icon.png").stat().st_size


def test_icon_generation_sizes_are_declared() -> None:
    spec = importlib.util.spec_from_file_location("generate_icons", "packaging/generate_icons.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.ICON_SIZES == (16, 32, 64, 128, 256)
    for size in module.ICON_SIZES:
        assert Path(f"packaging/assets/huguenot-inn-icon-{size}.png").exists()


def test_main_window_title_constant_is_huguenot_inn() -> None:
    from huguenot.ui.app import APP_WINDOW_TITLE

    assert APP_WINDOW_TITLE == "Huguenot Inn"


def test_platform_identity_sets_tk_appname_and_macos_name() -> None:
    from huguenot.ui.platform import configure_app_identity

    calls = []

    class FakeTk:
        def call(self, *args):
            calls.append(args)
            if args == ("tk", "windowingsystem"):
                return "aqua"
            return ""

    class FakeRoot:
        tk = FakeTk()

    configure_app_identity(FakeRoot(), "Huguenot Inn")

    assert ("tk", "appname", "Huguenot Inn") in calls
    assert ("tk::mac::SetApplicationName", "Huguenot Inn") in calls


def test_platform_root_identity_options_set_tk_base_name() -> None:
    from huguenot.ui.platform import root_identity_options

    assert root_identity_options("Huguenot Inn") == {"baseName": "Huguenot Inn"}


def test_main_app_initializes_tk_with_root_identity_options() -> None:
    source = Path("src/huguenot/ui/app.py").read_text()

    assert "root_identity_options(APP_WINDOW_TITLE)" in source
    assert "super().__init__(**root_identity_options(APP_WINDOW_TITLE))" in source


def test_platform_identity_ignores_unsupported_tcl_commands() -> None:
    import tkinter as tk

    from huguenot.ui.platform import configure_app_identity

    class FakeTk:
        def call(self, *_args):
            raise tk.TclError("unsupported")

    class FakeRoot:
        tk = FakeTk()

    configure_app_identity(FakeRoot(), "Huguenot Inn")


def test_pyinstaller_spec_preserves_macos_bundle_display_name() -> None:
    spec = Path("packaging/huguenot-inn.spec").read_text()

    assert '"CFBundleName": APP_NAME' in spec
    assert '"CFBundleDisplayName": APP_NAME' in spec


def test_icon_generation_uses_new_icon_and_resize_only(monkeypatch, tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("generate_icons", "packaging/generate_icons.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    source_dir = tmp_path / "examples"
    asset_dir = tmp_path / "assets"
    source_dir.mkdir()
    asset_dir.mkdir()
    source = source_dir / "new_icon.png"
    source.write_bytes(b"icon")
    commands = []

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/magick" if name == "magick" else None)

    def fake_run(command, **_kwargs):
        commands.append(command)
        Path(command[-1]).write_bytes(b"resized")
        return object()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    generated = module.generate_icons(asset_dir)

    assert len(generated) == len(module.ICON_SIZES)
    assert all(str(source) in command for command in commands)
    flattened = " ".join(part for command in commands for part in command)
    assert "-resize" in flattened
    assert "-fuzz" not in flattened
    assert "floodfill" not in flattened
    assert "-fill" not in flattened


def test_icon_generation_without_magick_reuses_existing_assets_or_fails(monkeypatch, tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("generate_icons", "packaging/generate_icons.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    source_dir = tmp_path / "examples"
    asset_dir = tmp_path / "assets"
    source_dir.mkdir()
    asset_dir.mkdir()
    (source_dir / "new_icon.png").write_bytes(b"large-source")
    for size in module.ICON_SIZES:
        (asset_dir / f"huguenot-inn-icon-{size}.png").write_bytes(f"prebuilt-{size}".encode())

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)

    generated = module.generate_icons(asset_dir)

    assert all(path.read_bytes().startswith(b"prebuilt-") for path in generated)
