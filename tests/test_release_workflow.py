from __future__ import annotations

from pathlib import Path


def workflow_text() -> str:
    return Path(".github/workflows/release.yml").read_text()


def test_release_workflow_runs_only_for_version_tags() -> None:
    text = workflow_text()

    assert "push:" in text
    assert "tags:" in text
    assert "'v*'" in text or '"v*"' in text
    assert "branches:" not in text


def test_release_workflow_has_expected_jobs() -> None:
    text = workflow_text()

    for job in ("build-flatpak", "build-macos-dmg", "build-windows-msi", "publish-release"):
        assert f"{job}:" in text


def test_release_workflow_uses_minimal_permissions() -> None:
    text = workflow_text()

    assert "permissions:" in text
    assert "contents: read" in text
    assert "contents: write" in text


def test_release_workflow_generates_release_notes_and_verifies_tag() -> None:
    text = workflow_text()

    assert "gh release create" in text
    assert "--generate-notes" in text
    assert "--verify-tag" in text
    assert "GH_TOKEN: ${{ github.token }}" in text


def test_release_workflow_downloads_and_validates_three_artifacts() -> None:
    text = workflow_text()

    assert "actions/download-artifact" in text
    assert "scripts/release_artifacts.py validate-artifacts" in text
    for pattern in (
        "Huguenot-Inn-${{ needs.build-flatpak.outputs.version }}-Linux-x86_64.flatpak",
        "Huguenot-Inn-${{ needs.build-macos-dmg.outputs.version }}-macOS-arm64.dmg",
        "Huguenot-Inn-${{ needs.build-windows-msi.outputs.version }}-Windows-x64.msi",
    ):
        assert pattern in text


def test_release_workflow_pins_python_for_python_steps() -> None:
    text = workflow_text()

    assert "actions/setup-python@v6" in text
    assert text.count("python-version: '3.11'") == 4


def test_release_workflow_uses_node24_actions() -> None:
    text = workflow_text()

    assert "actions/checkout@v6" in text
    assert "actions/upload-artifact@v7" in text
    assert "actions/download-artifact@v8" in text
