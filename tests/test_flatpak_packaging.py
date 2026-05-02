from __future__ import annotations

from pathlib import Path


def test_flatpak_manifest_declares_app_id() -> None:
    manifest = Path("packaging/flatpak/com.nikhilsomaru.HuguenotInn.yml").read_text()

    assert "id: com.nikhilsomaru.HuguenotInn" in manifest


def test_flatpak_manifest_uses_gnome_runtime_and_sdk() -> None:
    manifest = Path("packaging/flatpak/com.nikhilsomaru.HuguenotInn.yml").read_text()

    assert "runtime: org.gnome.Platform" in manifest
    assert "sdk: org.gnome.Sdk" in manifest
    assert "runtime-version:" in manifest
    assert "runtime-version: master" not in manifest


def test_flatpak_manifest_builds_python_app_from_source_or_wheel() -> None:
    manifest = Path("packaging/flatpak/com.nikhilsomaru.HuguenotInn.yml").read_text()

    assert "huguenot-inn" in manifest
    assert "pip install" in manifest
    assert "pyinstaller" not in manifest.lower()


def test_flatpak_manifest_exports_desktop_metadata() -> None:
    for path in (
        Path("packaging/flatpak/com.nikhilsomaru.HuguenotInn.desktop"),
        Path("packaging/flatpak/com.nikhilsomaru.HuguenotInn.metainfo.xml"),
        Path("packaging/assets/huguenot-inn-icon-256.png"),
    ):
        assert path.exists()


def test_flatpak_artifact_name_contract() -> None:
    workflow = Path(".github/workflows/release.yml").read_text()
    script = Path("scripts/release_artifacts.py").read_text()

    assert "Huguenot-Inn-${{ needs.build-flatpak.outputs.version }}-Linux-x86_64.flatpak" in workflow
    assert "Huguenot-Inn-{version}-Linux-x86_64.flatpak" in script


def test_flatpak_manifest_includes_generated_python_dependencies() -> None:
    manifest = Path("packaging/flatpak/com.nikhilsomaru.HuguenotInn.yml").read_text()
    requirements = Path("packaging/flatpak/requirements.txt").read_text()
    workflow = Path(".github/workflows/release.yml").read_text()

    assert "python3-dependencies.json" in manifest
    assert "flatpak-pip-generator" in workflow
    assert "--requirements-file=packaging/flatpak/requirements.txt" in workflow
    for dependency in (
        "hatchling",
        "platformdirs",
        "pymupdf",
        "python-docx",
        "reportlab",
        "yoyo-migrations",
        "tkinterdnd2",
        "docx2pdf",
    ):
        assert dependency in requirements
