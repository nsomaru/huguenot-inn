#!/usr/bin/env python3
"""Release version and artifact validation helpers for CI."""

from __future__ import annotations

import argparse
import ast
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def normalize_version_tag(tag: str) -> str:
    """Return the project version represented by a tag or local version string."""
    return tag[1:] if tag.startswith("v") else tag


def read_project_version(project_root: Path = PROJECT_ROOT) -> str:
    with (project_root / "pyproject.toml").open("rb") as file:
        return str(tomllib.load(file)["project"]["version"])


def read_runtime_version(project_root: Path = PROJECT_ROOT) -> str:
    init_path = project_root / "src" / "huguenot" / "__init__.py"
    tree = ast.parse(init_path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    raise ValueError(f"Could not find __version__ in {init_path}")


def validate_release_version(tag: str, project_root: Path = PROJECT_ROOT) -> str:
    version = normalize_version_tag(tag)
    project_version = read_project_version(project_root)
    runtime_version = read_runtime_version(project_root)
    if version != project_version:
        raise ValueError(f"Tag version {version!r} does not match pyproject.toml version {project_version!r}.")
    if version != runtime_version:
        raise ValueError(f"Tag version {version!r} does not match huguenot.__version__ {runtime_version!r}.")
    return version


def expected_release_artifact_names(version: str) -> tuple[str, str, str]:
    return (
        f"Huguenot-Inn-{version}-Linux-x86_64.flatpak",
        f"Huguenot-Inn-{version}-macOS-arm64.dmg",
        f"Huguenot-Inn-{version}-Windows-x64.msi",
    )


def validate_release_artifacts(directory: Path, version: str) -> tuple[Path, Path, Path]:
    expected_names = expected_release_artifact_names(version)
    expected = tuple(directory / name for name in expected_names)
    missing = [path.name for path in expected if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise ValueError(f"Missing release artifacts: {', '.join(missing)}")

    expected_name_set = set(expected_names)
    actual = {path.name for path in directory.iterdir() if path.is_file()}
    unexpected = sorted(actual - expected_name_set)
    if unexpected:
        raise ValueError(f"Unexpected release artifacts: {', '.join(unexpected)}")
    return expected


def _version_command(args: argparse.Namespace) -> int:
    print(validate_release_version(args.tag, PROJECT_ROOT))
    return 0


def _artifacts_command(args: argparse.Namespace) -> int:
    for path in validate_release_artifacts(Path(args.directory), args.version):
        print(path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(required=True)

    version_parser = subparsers.add_parser("validate-version")
    version_parser.add_argument("tag")
    version_parser.set_defaults(func=_version_command)

    artifacts_parser = subparsers.add_parser("validate-artifacts")
    artifacts_parser.add_argument("version")
    artifacts_parser.add_argument("directory")
    artifacts_parser.set_defaults(func=_artifacts_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
