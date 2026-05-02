from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ICON_SIZES = (16, 32, 64, 128, 256)


def generate_icons(asset_dir: Path | None = None) -> list[Path]:
    root = asset_dir or Path(__file__).resolve().parent / "assets"
    source = root / "huguenot-inn-icon.png"
    if not source.exists():
        raise FileNotFoundError(source)

    magick = shutil.which("magick")
    generated: list[Path] = []
    for size in ICON_SIZES:
        output = root / f"huguenot-inn-icon-{size}.png"
        if magick:
            subprocess.run(  # noqa: S603 - controlled executable from PATH, fixed arguments, local build asset only.
                [
                    magick,
                    str(source),
                    "-alpha",
                    "set",
                    "-channel",
                    "RGBA",
                    "-fuzz",
                    "8%",
                    "-fill",
                    "none",
                    "-draw",
                    "color 0,0 floodfill",
                    "-resize",
                    f"{size}x{size}",
                    "-fuzz",
                    "8%",
                    "-fill",
                    "none",
                    "-draw",
                    "color 0,0 floodfill",
                    str(output),
                ],
                check=True,
            )
        else:
            output.write_bytes(source.read_bytes())
        generated.append(output)
    return generated


if __name__ == "__main__":
    for path in generate_icons():
        print(path)
