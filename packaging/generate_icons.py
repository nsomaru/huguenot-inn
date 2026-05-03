from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ICON_SIZES = (16, 32, 64, 128, 256)


def _write_if_changed(path: Path, data: bytes) -> bool:
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def _replace_if_changed(path: Path, generated_path: Path) -> bool:
    changed = _write_if_changed(path, generated_path.read_bytes())
    generated_path.unlink(missing_ok=True)
    return changed


def generate_icons(asset_dir: Path | None = None) -> list[Path]:
    root = asset_dir or PROJECT_ROOT / "packaging" / "assets"
    source = PROJECT_ROOT / "packaging" / "assets" / "huguenot-inn-icon.png"
    if not source.exists():
        raise FileNotFoundError(source)

    root.mkdir(parents=True, exist_ok=True)
    app_icon = root / "huguenot-inn-icon.png"
    if app_icon.resolve() != source.resolve():
        _write_if_changed(app_icon, source.read_bytes())

    magick = shutil.which("magick")
    generated: list[Path] = []
    for size in ICON_SIZES:
        output = root / f"huguenot-inn-icon-{size}.png"
        if magick:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=root) as handle:
                temp_output = Path(handle.name)
            subprocess.run(  # noqa: S603 - controlled executable from PATH, fixed arguments, local build asset only.
                [magick, str(source), "-resize", f"{size}x{size}", str(temp_output)],
                check=True,
            )
            _replace_if_changed(output, temp_output)
        elif not output.exists():
            raise FileNotFoundError(
                f"ImageMagick 'magick' was not found and pre-generated icon asset is missing: {output}"
            )
        generated.append(output)
    return generated


if __name__ == "__main__":
    for path in generate_icons():
        print(path)
