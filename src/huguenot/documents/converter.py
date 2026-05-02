from __future__ import annotations

import shutil
import subprocess  # nosec B404
from pathlib import Path


class LibreOfficeConverter:
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or shutil.which("soffice") or shutil.which("libreoffice")

    def libreoffice_available(self) -> bool:
        return self.executable is not None

    def convert_docx_to_pdf(self, docx_path: Path, output_dir: Path) -> Path:
        if self.executable is None:
            raise FileNotFoundError("LibreOffice command-line executable was not found.")

        output_dir.mkdir(parents=True, exist_ok=True)
        command = [
            self.executable,
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
