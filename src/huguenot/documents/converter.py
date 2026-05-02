from __future__ import annotations

import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path


class LibreOfficeConverter:
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or self.find_executable()
        self._available_cache: bool | None = None

    @staticmethod
    def find_executable() -> str | None:
        for command in ("soffice", "libreoffice"):
            executable = shutil.which(command)
            if executable:
                return executable
        for candidate in (
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
            Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice",
        ):
            if candidate.exists():
                return str(candidate)
        return None

    def libreoffice_available(self) -> bool:
        if self.executable is None:
            return False
        if self._available_cache is None:
            try:
                subprocess.run(  # nosec B603
                    [self.executable, "--headless", "--version"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except Exception:
                self._available_cache = False
            else:
                self._available_cache = True
        return self._available_cache

    def convert_docx_to_pdf(self, docx_path: Path, output_dir: Path) -> Path:
        if self.executable is None:
            raise FileNotFoundError("LibreOffice command-line executable was not found.")

        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="huguenot-libreoffice-profile-") as profile_dir:
            command = [
                self.executable,
                f"-env:UserInstallation={Path(profile_dir).as_uri()}",
                "--headless",
                "--convert-to",
                "pdf:writer_pdf_Export",
                "--outdir",
                str(output_dir),
                str(docx_path),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)  # nosec B603
        output_path = output_dir / f"{docx_path.stem}.pdf"
        if not output_path.exists():
            raise FileNotFoundError(f"LibreOffice did not create expected PDF: {output_path}")
        return output_path
