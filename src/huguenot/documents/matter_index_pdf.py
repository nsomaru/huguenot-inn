from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

import fitz

from huguenot.domain import BundleIndexEntry, BundleIndexRow, DocumentHeaderInput, Matter, PDFItem

from .authorities_index import (
    create_matter_authorities_index_docx,
    create_matter_authorities_index_docx_from_rows,
    get_index_entries,
)
from .converter import DocxToPdfConverter, LibreOfficeConverter
from .reportlab_index import ReportLabIndexRenderer
from .settings import FontResolver, PDFRenderer, RendererPreference, choose_pdf_renderer

LOGGER = logging.getLogger(__name__)


def render_matter_index_pdf(
    matter: Matter,
    document_header: DocumentHeaderInput,
    pdf_items: list[PDFItem],
    output_path: Path,
    *,
    converter: DocxToPdfConverter | None = None,
    renderer_preference: RendererPreference | None = None,
    font_name: str | None = None,
    index_entries: Sequence[BundleIndexEntry] | None = None,
    index_rows: Sequence[BundleIndexRow] | None = None,
    colour_page_ranges: bool = False,
) -> tuple[bool, list[dict[str, int | float]]]:
    converter = converter or LibreOfficeConverter()
    renderer_preference = renderer_preference or RendererPreference()
    font = FontResolver().resolve(font_name)
    try:
        renderer = choose_pdf_renderer(
            renderer_preference, libreoffice_available=lambda: _converter_available(converter)
        )
    except RuntimeError:
        raise

    if renderer is PDFRenderer.LIBREOFFICE:
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
                    font_name=font.family,
                    index_entries=index_entries,
                    index_rows=index_rows,
                    colour_page_ranges=colour_page_ranges,
                ),
            )
            return True, links
        except Exception as exc:
            if renderer_preference.renderer is PDFRenderer.LIBREOFFICE:
                raise
            # Fall back rather than failing the user-facing bundle generation path.
            LOGGER.info("LibreOffice matter index rendering failed; falling back to ReportLab: %s", exc)

    renderer = ReportLabIndexRenderer(font=font)
    links = _render_with_bundle_page_numbers(
        output_path,
        lambda path, start_page: renderer.render_pdf(
            matter,
            document_header,
            pdf_items,
            path,
            start_page=start_page,
            index_entries=index_entries,
            index_rows=index_rows,
            colour_page_ranges=colour_page_ranges,
        ),
    )
    return False, links


def render_matter_index_pdf_from_rows(
    matter: Matter,
    document_header: DocumentHeaderInput,
    pdf_items: list[PDFItem],
    index_rows: Sequence[BundleIndexRow],
    output_path: Path,
    *,
    converter: DocxToPdfConverter | None = None,
    renderer_preference: RendererPreference | None = None,
    font_name: str | None = None,
    colour_page_ranges: bool = False,
) -> tuple[bool, list[dict[str, int | float]]]:
    return render_matter_index_pdf(
        matter,
        document_header,
        pdf_items,
        output_path,
        converter=converter,
        renderer_preference=renderer_preference,
        font_name=font_name,
        index_rows=index_rows,
        colour_page_ranges=colour_page_ranges,
    )


def _converter_available(converter: DocxToPdfConverter) -> bool:
    return converter.converter_available()


def _render_with_bundle_page_numbers(
    output_path: Path,
    render: Callable[[Path, int], list[dict[str, int | float]]],
) -> list[dict[str, int | float]]:
    return render(output_path, 1)


def _render_with_libreoffice(
    matter: Matter,
    document_header: DocumentHeaderInput,
    pdf_items: list[PDFItem],
    output_path: Path,
    converter: DocxToPdfConverter,
    *,
    start_page: int,
    font_name: str,
    index_entries: Sequence[BundleIndexEntry] | None,
    index_rows: Sequence[BundleIndexRow] | None,
    colour_page_ranges: bool,
) -> list[dict[str, int | float]]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        docx_path = tmp_path / "matter_index.docx"
        if index_rows is not None:
            create_matter_authorities_index_docx_from_rows(
                matter,
                document_header,
                index_rows,
                docx_path,
                font_name=font_name,
                colour_page_ranges=colour_page_ranges,
            )
        else:
            create_matter_authorities_index_docx(
                matter,
                document_header,
                pdf_items,
                docx_path,
                start_page=start_page,
                font_name=font_name,
                index_entries=index_entries,
                colour_page_ranges=colour_page_ranges,
            )
        converted_pdf = converter.convert_docx_to_pdf(docx_path, tmp_path)
        output_path.write_bytes(converted_pdf.read_bytes())

    entries = index_rows if index_rows is not None else index_entries
    entries = entries if entries is not None else get_index_entries(pdf_items, start_page=start_page)
    return _find_page_range_links(output_path, entries, start_page=start_page)


def _find_page_range_links(
    index_pdf_path: Path,
    index_entries: Sequence[BundleIndexRow],
    *,
    start_page: int,
) -> list[dict[str, int | float]]:
    doc = fitz.open(index_pdf_path)
    links: list[dict[str, int | float]] = []
    try:
        for entry in index_entries:
            if not isinstance(entry, BundleIndexEntry):
                continue
            item = entry.item
            page_range = entry.page_range
            texts = (item.title, page_range.display())
            found = False
            for page_index in range(doc.page_count):
                page = doc[page_index]
                for text in texts:
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
