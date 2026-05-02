from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable
from pathlib import Path

import fitz

from huguenot.domain import DocumentHeaderInput, Matter, PDFItem

from .authorities_index import create_matter_authorities_index_docx, get_index_entries
from .converter import LibreOfficeConverter
from .reportlab_index import ReportLabIndexRenderer

LOGGER = logging.getLogger(__name__)


def render_matter_index_pdf(
    matter: Matter,
    document_header: DocumentHeaderInput,
    pdf_items: list[PDFItem],
    output_path: Path,
    *,
    converter: LibreOfficeConverter | None = None,
) -> tuple[bool, list[dict[str, int | float]]]:
    converter = converter or LibreOfficeConverter()
    if converter.libreoffice_available():
        try:
            links = _render_with_bundle_page_numbers(
                output_path,
                lambda path, start_page: _render_with_libreoffice(
                    matter,
                    document_header,
                    pdf_items,
                    path,
                    converter,
                    start_page=start_page,
                ),
            )
            return True, links
        except Exception as exc:
            # Fall back rather than failing the user-facing bundle generation path.
            LOGGER.info("LibreOffice matter index rendering failed; falling back to ReportLab: %s", exc)

    renderer = ReportLabIndexRenderer()
    links = _render_with_bundle_page_numbers(
        output_path,
        lambda path, start_page: renderer.render_pdf(
            matter,
            document_header,
            pdf_items,
            path,
            start_page=start_page,
        ),
    )
    return False, links


def _render_with_bundle_page_numbers(
    output_path: Path,
    render: Callable[[Path, int], list[dict[str, int | float]]],
) -> list[dict[str, int | float]]:
    with tempfile.TemporaryDirectory() as tmp:
        draft_path = Path(tmp) / "draft-index.pdf"
        render(draft_path, 1)
        first_document_page = _pdf_page_count(draft_path) + 1
    return render(output_path, first_document_page)


def _pdf_page_count(path: Path) -> int:
    doc = fitz.open(path)
    try:
        return doc.page_count
    finally:
        doc.close()


def _render_with_libreoffice(
    matter: Matter,
    document_header: DocumentHeaderInput,
    pdf_items: list[PDFItem],
    output_path: Path,
    converter: LibreOfficeConverter,
    *,
    start_page: int,
) -> list[dict[str, int | float]]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        docx_path = tmp_path / "matter_index.docx"
        create_matter_authorities_index_docx(matter, document_header, pdf_items, docx_path, start_page=start_page)
        converted_pdf = converter.convert_docx_to_pdf(docx_path, tmp_path)
        output_path.write_bytes(converted_pdf.read_bytes())

    return _find_page_range_links(output_path, pdf_items, start_page=start_page)


def _find_page_range_links(
    index_pdf_path: Path,
    pdf_items: list[PDFItem],
    *,
    start_page: int,
) -> list[dict[str, int | float]]:
    doc = fitz.open(index_pdf_path)
    links: list[dict[str, int | float]] = []
    try:
        for _number, _item, page_range in get_index_entries(pdf_items, start_page=start_page):
            text = page_range.display()
            found = False
            for page_index in range(doc.page_count):
                page = doc[page_index]
                for rect in page.search_for(text):
                    links.append(
                        {
                            "index_page": page_index,
                            "target_page": page_range.start - start_page,
                            "x0": rect.x0,
                            "y0": rect.y0,
                            "x1": rect.x1,
                            "y1": rect.y1,
                        }
                    )
                    found = True
                    break
                if found:
                    break
            if not found:
                # Keep numbering stable for diagnostics; ReportLab fallback has stronger link geometry.
                links.append(
                    {
                        "index_page": 0,
                        "target_page": page_range.start - start_page,
                        "x0": 0,
                        "y0": 0,
                        "x1": 0,
                        "y1": 0,
                    }
                )
    finally:
        doc.close()
    return [link for link in links if float(link["x1"]) > float(link["x0"])]
