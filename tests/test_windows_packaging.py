from __future__ import annotations

from pathlib import Path


def test_windows_build_script_uses_pyinstaller_and_wix() -> None:
    script = Path("scripts/build_windows_msi.ps1").read_text()

    assert "pyinstaller" in script.lower()
    assert "wix build" in script.lower()


def test_windows_wix_source_packages_app_directory() -> None:
    source = Path("packaging/windows/huguenot-inn.wxs").read_text()

    assert "$(var.SourceDir)" in source
    assert "Files" in source
    assert 'Directory="INSTALLFOLDER"' in source


def test_windows_msi_uses_x64_architecture() -> None:
    script = Path("scripts/build_windows_msi.ps1").read_text()

    assert "-arch x64" in script.lower()


def test_windows_artifact_name_contract() -> None:
    workflow = Path(".github/workflows/release.yml").read_text()
    script = Path("scripts/build_windows_msi.ps1").read_text()

    assert "Huguenot-Inn-${{ needs.build-windows-msi.outputs.version }}-Windows-x64.msi" in workflow
    assert "Huguenot-Inn-$Version-Windows-x64.msi" in script


def test_windows_workflow_makes_global_wix_tool_available() -> None:
    workflow = Path(".github/workflows/release.yml").read_text()

    assert "dotnet tool install --global wix" in workflow
    assert "$env:GITHUB_PATH" in workflow
    assert "\\.dotnet\\tools" in workflow


def test_windows_workflow_pins_wix_before_v7_eula_requirement() -> None:
    workflow = Path(".github/workflows/release.yml").read_text()

    assert "dotnet tool install --global wix --version 6.0.2" in workflow
    assert "-acceptEula" not in workflow
    assert "wix7" not in workflow


def test_windows_workflow_prints_wix_version_for_release_debugging() -> None:
    workflow = Path(".github/workflows/release.yml").read_text()

    assert "$env:PATH" in workflow
    assert "wix --version" in workflow


def test_windows_installer_is_unsigned_for_now() -> None:
    combined = (
        Path("scripts/build_windows_msi.ps1").read_text() + Path("packaging/windows/huguenot-inn.wxs").read_text()
    )

    assert "signtool" not in combined.lower()
    assert "certificate" not in combined.lower()
