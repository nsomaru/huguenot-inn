from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class PDFRenderer(StrEnum):
    AUTOMATIC = "automatic"
    LIBREOFFICE = "libreoffice"
    REPORTLAB = "reportlab"


@dataclass(frozen=True)
class RendererPreference:
    renderer: PDFRenderer = PDFRenderer.AUTOMATIC


@dataclass(frozen=True)
class ResolvedIndexFont:
    family: str
    reportlab_regular: str
    reportlab_bold: str


class FontResolver:
    def __init__(self, available_fonts: Callable[[], list[str]] | None = None) -> None:
        self._available_fonts = available_fonts or list_system_fonts

    def resolve(self, requested: str | None = None) -> ResolvedIndexFont:
        available = self._available_fonts()
        available_by_lower = {font.lower(): font for font in available}
        requested = (requested or "").strip()
        if requested and requested.lower() in available_by_lower:
            family = available_by_lower[requested.lower()]
        elif "times new roman" in available_by_lower:
            family = available_by_lower["times new roman"]
        elif available:
            family = sorted(available, key=str.lower)[0]
        else:
            family = "Times New Roman"

        regular, bold = reportlab_font_names(family)
        return ResolvedIndexFont(family=family, reportlab_regular=regular, reportlab_bold=bold)


def reportlab_font_names(family: str) -> tuple[str, str]:
    if family.lower() in {"times new roman", "times", "times-roman"}:
        return "Times-Roman", "Times-Bold"
    if family.lower() in {"helvetica", "arial"}:
        return "Helvetica", "Helvetica-Bold"
    if family.lower() == "courier":
        return "Courier", "Courier-Bold"
    # System font discovery gives family names, but ReportLab needs registered
    # PDF font names. Keep output deterministic unless font registration is added.
    return "Times-Roman", "Times-Bold"


def list_system_fonts() -> list[str]:
    try:
        import tkinter as tk
        from tkinter import font

        root = tk.Tk()
        root.withdraw()
        try:
            return sorted(set(font.families(root)))
        finally:
            root.destroy()
    except Exception:
        return ["Times New Roman", "Helvetica", "Courier"]


def choose_pdf_renderer(preference: RendererPreference, *, libreoffice_available: Callable[[], bool]) -> PDFRenderer:
    if preference.renderer is PDFRenderer.REPORTLAB:
        return PDFRenderer.REPORTLAB
    if preference.renderer is PDFRenderer.LIBREOFFICE:
        if not libreoffice_available():
            raise RuntimeError("LibreOffice is not available or usable for PDF conversion.")
        return PDFRenderer.LIBREOFFICE
    return PDFRenderer.REPORTLAB
