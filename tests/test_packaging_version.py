from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

import huguenot


def load_release_module():
    spec = importlib.util.spec_from_file_location("release_artifacts", "scripts/release_artifacts.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_normalize_version_tag_removes_single_leading_v() -> None:
    module = load_release_module()

    assert module.normalize_version_tag("v0.4.1a") == "0.4.1a"


def test_normalize_version_tag_accepts_plain_version_for_local_scripts() -> None:
    module = load_release_module()

    assert module.normalize_version_tag("0.4.1a") == "0.4.1a"


def test_project_versions_match() -> None:
    module = load_release_module()

    assert module.read_project_version(Path.cwd()) == huguenot.__version__
    assert module.read_runtime_version(Path.cwd()) == huguenot.__version__


def test_validate_release_version_rejects_mismatched_tag() -> None:
    module = load_release_module()

    with pytest.raises(ValueError, match="does not match"):
        module.validate_release_version("v9.9.9", Path.cwd())


def test_expected_release_artifact_names_are_version_derived() -> None:
    module = load_release_module()

    assert module.expected_release_artifact_names("0.4.1a") == (
        "Huguenot-Inn-0.4.1a-Linux-x86_64.flatpak",
        "Huguenot-Inn-0.4.1a-macOS-arm64.dmg",
        "Huguenot-Inn-0.4.1a-Windows-x64.msi",
    )


def test_release_artifact_validator_requires_exact_three_files(tmp_path: Path) -> None:
    module = load_release_module()
    for name in module.expected_release_artifact_names("0.4.1a"):
        (tmp_path / name).write_bytes(b"artifact")

    assert module.validate_release_artifacts(tmp_path, "0.4.1a") == tuple(
        tmp_path / name for name in module.expected_release_artifact_names("0.4.1a")
    )

    (tmp_path / "unexpected.zip").write_bytes(b"extra")
    with pytest.raises(ValueError, match="Unexpected release artifacts"):
        module.validate_release_artifacts(tmp_path, "0.4.1a")
