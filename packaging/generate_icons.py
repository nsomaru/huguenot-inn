from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ICON_SIZES = (16, 32, 64, 128, 256)


def generate_icons(asset_dir: Path | None = None) -> list[Path]:
    root = asset_dir or PROJECT_ROOT / "packaging" / "assets"
    source = PROJECT_ROOT / "examples" / "new_icon.png"
    if not source.exists():
        raise FileNotFoundError(source)

    root.mkdir(parents=True, exist_ok=True)
    app_icon = root / "huguenot-inn-icon.png"
    if app_icon.resolve() != source.resolve():
        app_icon.write_bytes(source.read_bytes())

    magick = shutil.which("magick")
    generated: list[Path] = []
    for size in ICON_SIZES:
        output = root / f"huguenot-inn-icon-{size}.png"
        if magick:
            subprocess.run(  # noqa: S603 - controlled executable from PATH, fixed arguments, local build asset only.
                [magick, str(source), "-resize", f"{size}x{size}", str(output)],
                check=True,
            )
        elif not output.exists():
            raise FileNotFoundError(
                f"ImageMagick 'magick' was not found and pre-generated icon asset is missing: {output}"
            )
        generated.append(output)
    return generated


if __name__ == "__main__":
    for path in generate_icons():
        print(path)
