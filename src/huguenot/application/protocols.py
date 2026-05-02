from __future__ import annotations

from pathlib import Path
from typing import Protocol

from huguenot.domain import Court, DocumentHeaderInput, Matter, PDFItem


class MatterRepository(Protocol):
    def save(self, matter: Matter) -> Matter: ...
    def list_matters(self) -> list[Matter]: ...
    def get(self, matter_id: int) -> Matter | None: ...
    def set_last_active(self, matter_id: int | None) -> None: ...
    def get_last_active(self) -> Matter | None: ...


class CourtRepository(Protocol):
    def list_courts(self) -> list[Court]: ...
    def list_header_lines(self) -> list[str]: ...
    def add_court(self, name: str, header_line_2: str | None = None) -> Court: ...
    def add_header_line(self, line: str) -> str: ...


class IndexRenderer(Protocol):
    def render_docx(
        self,
        matter: Matter,
        document_header: DocumentHeaderInput,
        pdf_items: list[PDFItem],
        output_path: Path,
    ) -> None: ...

    def render_pdf(
        self,
        matter: Matter,
        document_header: DocumentHeaderInput,
        pdf_items: list[PDFItem],
        output_path: Path,
        *,
        start_page: int = 1,
    ) -> list[dict[str, int | float]]: ...


class PdfBundler(Protocol):
    def combine_number_and_add_toc(
        self,
        pdf_items: list[PDFItem],
        output_path: Path,
        position: str,
        font_size: int,
        margin: int,
    ) -> None: ...

    def combine_with_front_index(
        self,
        pdf_items: list[PDFItem],
        index_pdf_path: Path,
        index_links: list[dict[str, int | float]],
        output_path: Path,
        position: str,
        font_size: int,
        margin: int,
        *,
        toc_root_title: str = "Index",
    ) -> None: ...


class DocumentConverter(Protocol):
    def converter_available(self) -> bool: ...
    def convert_docx_to_pdf(self, docx_path: Path, output_dir: Path) -> Path: ...
