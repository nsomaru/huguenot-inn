from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import tempfile
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol


class DocxToPdfConverter(Protocol):
    def converter_available(self) -> bool: ...
    def convert_docx_to_pdf(self, docx_path: Path, output_dir: Path) -> Path: ...


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
        for candidate in LibreOfficeConverter.executable_candidates():
            if candidate.exists():
                return str(candidate)
        return None

    @staticmethod
    def executable_candidates() -> tuple[Path, ...]:
        candidates = [
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
            Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice",
            Path("/usr/bin/libreoffice"),
            Path("/usr/local/bin/libreoffice"),
            Path("/snap/bin/libreoffice"),
            Path("/var/lib/flatpak/exports/bin/org.libreoffice.LibreOffice"),
            Path.home() / ".local/share/flatpak/exports/bin/org.libreoffice.LibreOffice",
        ]
        for env_name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            base = os.environ.get(env_name)
            if base:
                candidates.append(Path(base) / "LibreOffice" / "program" / "soffice.exe")
        return tuple(candidates)

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

    def converter_available(self) -> bool:
        return self.libreoffice_available()

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


class Docx2PdfConverter:
    def __init__(self, import_module: Callable[[str], Any] = import_module) -> None:
        self._import_module = import_module

    def converter_available(self) -> bool:
        try:
            self._import_module("docx2pdf")
        except ModuleNotFoundError:
            return False
        return True

    def convert_docx_to_pdf(self, docx_path: Path, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{docx_path.stem}.pdf"
        try:
            docx2pdf = self._import_module("docx2pdf")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Microsoft Word conversion requires the optional docx2pdf package and Microsoft Word "
                "on Windows or macOS."
            ) from exc

        try:
            docx2pdf.convert(str(docx_path), str(output_path))
        except Exception as exc:
            raise RuntimeError(
                "Microsoft Word conversion failed. Ensure Microsoft Word is installed and docx2pdf is supported "
                "on this platform."
            ) from exc
        if not output_path.exists():
            raise FileNotFoundError(f"docx2pdf did not create expected PDF: {output_path}")
        return output_path
