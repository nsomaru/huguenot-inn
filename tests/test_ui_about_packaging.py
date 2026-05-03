import importlib.util
import subprocess
import time
from pathlib import Path

from huguenot.ui.about import ABOUT_METADATA, about_icon_path


def test_about_metadata_contains_required_notice() -> None:
    assert ABOUT_METADATA.application_name == "Huguenot Inn"
    assert ABOUT_METADATA.version
    assert "GPLv3" in ABOUT_METADATA.license_notice
    assert ABOUT_METADATA.author == "Nikhil Somaru"
    assert ABOUT_METADATA.contact == "nikhil@capebar.co.za"


def test_packaged_icon_source_is_tracked_release_asset() -> None:
    icon_path = Path("packaging/assets/huguenot-inn-icon.png")

    assert icon_path.is_file()
    tracked = subprocess.run(["git", "ls-files", str(icon_path)], check=True, capture_output=True, text=True).stdout
    assert str(icon_path) in tracked.splitlines()
    assert "examples/new_icon.png" not in Path("packaging/generate_icons.py").read_text()


def test_pyinstaller_spec_can_build_from_png_icon_source() -> None:
    spec = Path("packaging/huguenot-inn.spec").read_text()
    assert "ICON_PNG_PATH" in spec
    assert "ICON_ICNS_PATH if ICON_ICNS_PATH.exists() else ICON_PNG_PATH" in spec
    assert "generate_icons" in spec
    assert "huguenot-inn-icon.png" in spec
    assert 'collect_submodules("docx2pdf")' in spec


def test_pyinstaller_spec_bundles_yoyo_sqlite_backend_metadata() -> None:
    spec = Path("packaging/huguenot-inn.spec").read_text()

    assert "copy_metadata" in spec
    assert 'copy_metadata("yoyo-migrations")' in spec
    assert '"yoyo.backends.core.sqlite3"' in spec


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


def test_write_if_changed_preserves_identical_file_mtime(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("generate_icons", "packaging/generate_icons.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    path = tmp_path / "icon.png"
    path.write_bytes(b"same")
    before = path.stat().st_mtime_ns
    time.sleep(0.001)

    changed = module._write_if_changed(path, b"same")

    assert changed is False
    assert path.stat().st_mtime_ns == before
    assert module._write_if_changed(path, b"different") is True
    assert path.read_bytes() == b"different"


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


def test_platform_macos_quit_routes_to_close_callback() -> None:
    from huguenot.ui.platform import configure_macos_quit

    calls = []

    class FakeTk:
        def call(self, *args):
            calls.append(args)
            if args == ("tk", "windowingsystem"):
                return "aqua"
            return ""

    class FakeRoot:
        tk = FakeTk()

        def createcommand(self, name, command):
            calls.append(("createcommand", name, command))

    close = object()
    configure_macos_quit(FakeRoot(), close)  # type: ignore[arg-type]

    assert ("createcommand", "tk::mac::Quit", close) in calls


def test_platform_root_identity_options_set_tk_base_name() -> None:
    from huguenot.ui.platform import root_identity_options

    assert root_identity_options("Huguenot Inn") == {"baseName": "Huguenot Inn"}


def test_main_app_initializes_tk_with_root_identity_options() -> None:
    source = Path("src/huguenot/ui/app.py").read_text()

    assert "root_identity_options(APP_WINDOW_TITLE)" in source
    assert "super().__init__(**root_identity_options(APP_WINDOW_TITLE))" in source


def test_main_app_wires_close_paths_to_single_callback() -> None:
    source = Path("src/huguenot/ui/app.py").read_text()

    assert 'self.protocol("WM_DELETE_WINDOW", self._close_application)' in source
    assert 'file_menu.add_command(label="Exit", command=self._close_application)' in source
    assert "configure_macos_quit(self, self._close_application)" in source


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


def test_icon_generation_uses_committed_asset_and_resize_only(monkeypatch, tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("generate_icons", "packaging/generate_icons.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    source_dir = tmp_path / "packaging" / "assets"
    asset_dir = tmp_path / "generated-assets"
    source_dir.mkdir(parents=True)
    asset_dir.mkdir()
    source = source_dir / "huguenot-inn-icon.png"
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
    assert all(Path(command[-1]).name.startswith("tmp") for command in commands)


def test_icon_generation_without_magick_reuses_existing_assets_or_fails(monkeypatch, tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("generate_icons", "packaging/generate_icons.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    source_dir = tmp_path / "packaging" / "assets"
    asset_dir = tmp_path / "assets"
    source_dir.mkdir(parents=True)
    asset_dir.mkdir()
    (source_dir / "huguenot-inn-icon.png").write_bytes(b"large-source")
    for size in module.ICON_SIZES:
        (asset_dir / f"huguenot-inn-icon-{size}.png").write_bytes(f"prebuilt-{size}".encode())

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)

    generated = module.generate_icons(asset_dir)

    assert all(path.read_bytes().startswith(b"prebuilt-") for path in generated)


def test_macos_dmg_artifact_name_contract() -> None:
    script = Path("scripts/build_macos_dmg.sh").read_text()

    assert "Huguenot-Inn-${VERSION}-macOS-arm64.dmg" in script


def test_macos_script_preserves_unsigned_build() -> None:
    combined = Path("scripts/build_macos_dmg.sh").read_text() + Path("packaging/huguenot-inn.spec").read_text()

    assert "codesign_identity=None" in combined
    assert "notarytool" not in combined.lower()
    assert "altool" not in combined.lower()


def test_macos_icon_generation_compares_outputs_before_replacing() -> None:
    script = Path("scripts/build_macos_dmg.sh").read_text()

    assert "replace_if_changed" in script
    assert "cmp -s" in script
    assert 'tmp_icon="$ICONSET/${filename%.png}.tmp.png"' in script
    assert 'TMP_ICON_ICNS="${ICON_ICNS%.icns}.tmp.icns"' in script


def test_packaging_static_audit_has_no_local_network_permission_triggers() -> None:
    spec = Path("packaging/huguenot-inn.spec").read_text()

    assert "NSLocalNetworkUsageDescription" not in spec
    assert "NSBonjourServices" not in spec
    assert "entitlements_file=None" in spec


def test_app_source_static_audit_has_no_direct_local_network_apis() -> None:
    source_paths = list(Path("src/huguenot").rglob("*.py")) + [Path("packaging/pyinstaller_entry.py")]
    combined = "\n".join(path.read_text() for path in source_paths)

    forbidden = ("socket.", "http.server", "urllib.request", "requests.", "asyncio.start_server")
    assert all(token not in combined for token in forbidden)
