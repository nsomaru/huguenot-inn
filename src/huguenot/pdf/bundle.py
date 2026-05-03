from __future__ import annotations

import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import fitz

from huguenot.domain import (
    DEFAULT_NUMBER_FONT_SIZE,
    DEFAULT_NUMBER_MARGIN,
    DEFAULT_NUMBER_POSITION,
    NUMBER_POSITIONS,
    BundleIndexEntry,
    PDFItem,
    build_bundle_index_entries,
    normalize_flag_colour,
)
from huguenot.domain.legal_titles import normalize_legal_display_title

from .authority_detection import clean_filename_title

POSITIONS = NUMBER_POSITIONS


@dataclass(frozen=True)
class NumberBoxSize:
    width: float
    height: float


@dataclass(frozen=True)
class PdfBundleRenderOptions:
    flag_colours: Sequence[str] | None = None
    physical_flag_markers: bool = False
    number_fill_opacity: float = 1.0


def get_pdf_page_count(path: Path) -> int:
    doc = fitz.open(path)
    try:
        return doc.page_count
    finally:
        doc.close()


def get_number_box(
    page_rect: fitz.Rect, position: str, box_width: float, box_height: float, margin: float
) -> fitz.Rect:
    position_lower = position.lower()
    if "left" in position_lower:
        x0 = page_rect.x0 + margin
    elif "right" in position_lower:
        x0 = page_rect.x1 - margin - box_width
    else:
        x0 = page_rect.x0 + (page_rect.width - box_width) / 2

    if "top" in position_lower:
        y0 = page_rect.y0 + margin
    else:
        y0 = page_rect.y1 - margin - box_height
    return fitz.Rect(x0, y0, x0 + box_width, y0 + box_height)


def number_box_size(text: str, *, font_size: int, fontname: str = "hebo") -> NumberBoxSize:
    text_width = fitz.get_text_length(text, fontname=fontname, fontsize=font_size)
    horizontal_padding = font_size * 0.75
    return NumberBoxSize(
        width=max(font_size * 2.25, text_width + horizontal_padding * 2),
        height=font_size * 1.85,
    )


def draw_page_number(
    page: fitz.Page,
    number: int,
    position: str = DEFAULT_NUMBER_POSITION,
    font_size: int = DEFAULT_NUMBER_FONT_SIZE,
    margin: int = DEFAULT_NUMBER_MARGIN,
    *,
    fill_colour: str | None = None,
    fill_opacity: float = 1.0,
) -> None:
    text = str(number)
    page_rect = page.rect
    fontname = "hebo"
    text_width = fitz.get_text_length(text, fontname=fontname, fontsize=font_size)
    box_size = number_box_size(text, font_size=font_size, fontname=fontname)
    box = get_number_box(page_rect, position, box_size.width, box_size.height, margin)
    fill = None if fill_colour is None else _hex_to_rgb(fill_colour)
    page.draw_rect(
        box,
        color=(0, 0, 0),
        fill=fill,
        width=0.6,
        stroke_opacity=0.65,
        fill_opacity=fill_opacity if fill is not None else 0,
    )
    x = box.x0 + (box.width - text_width) / 2
    y = box.y0 + (box.height + font_size * 0.70) / 2
    page.insert_text(
        fitz.Point(x, y),
        text,
        fontsize=font_size,
        fontname=fontname,
        color=(0, 0, 0),
        render_mode=0,
    )


def combine_number_and_add_toc(
    pdf_items: list[PDFItem],
    output_path: Path,
    position: str = DEFAULT_NUMBER_POSITION,
    font_size: int = DEFAULT_NUMBER_FONT_SIZE,
    margin: int = DEFAULT_NUMBER_MARGIN,
    *,
    render_options: PdfBundleRenderOptions | None = None,
    index_entries: Sequence[BundleIndexEntry] | None = None,
) -> None:
    if not pdf_items:
        raise ValueError("No PDFs selected.")

    output_doc = fitz.open()
    toc: list[list[int | str]] = []
    try:
        entries = list(index_entries) if index_entries is not None else _build_entries(pdf_items, render_options)
        for entry in entries:
            item = entry.item
            source = fitz.open(item.path)
            try:
                if source.page_count == 0:
                    continue
                toc_title = _display_toc_title(item)
                toc.append([1, toc_title, entry.page_range.start])
                output_doc.insert_pdf(source)
            finally:
                source.close()

        for index in range(output_doc.page_count):
            page = output_doc[index]
            entry = _entry_for_bundle_page(entries, index + 1)
            _draw_number_for_entry(page, index + 1, position, font_size, margin, entry, render_options)
            if _physical_markers_enabled(render_options) and entry and index + 1 == entry.page_range.start:
                draw_physical_flag_marker(page, entry.item_number, len(entries), entry.flag_colour)

        _set_toc(output_doc, toc)
        output_doc.save(output_path, garbage=4, deflate=True)
    finally:
        output_doc.close()
    _ensure_saved_toc(output_path, toc)


def combine_with_front_index(
    pdf_items: list[PDFItem],
    index_pdf_path: Path,
    index_links: list[dict[str, int | float]],
    output_path: Path,
    position: str = DEFAULT_NUMBER_POSITION,
    font_size: int = DEFAULT_NUMBER_FONT_SIZE,
    margin: int = DEFAULT_NUMBER_MARGIN,
    *,
    toc_root_title: str = "Index",
    render_options: PdfBundleRenderOptions | None = None,
    index_entries: Sequence[BundleIndexEntry] | None = None,
) -> None:
    if not pdf_items:
        raise ValueError("No PDFs selected.")

    output_doc = fitz.open()
    index_doc = fitz.open(index_pdf_path)
    try:
        output_doc.insert_pdf(index_doc)
        index_page_count = index_doc.page_count
    finally:
        index_doc.close()

    toc: list[list[int | str]] = [[1, toc_root_title.strip() or "Index", 1]]
    current_start_page = index_page_count + 1
    try:
        entries = list(index_entries) if index_entries is not None else _build_entries(pdf_items, render_options)
        for entry in entries:
            item = entry.item
            source = fitz.open(item.path)
            try:
                if source.page_count == 0:
                    continue
                toc_title = _display_toc_title(item)
                toc.append([1, toc_title, current_start_page])
                output_doc.insert_pdf(source)
                current_start_page += source.page_count
            finally:
                source.close()

        for index in range(index_page_count, output_doc.page_count):
            page = output_doc[index]
            bundle_page_number = index - index_page_count + 1
            entry = _entry_for_bundle_page(entries, bundle_page_number)
            _draw_number_for_entry(page, bundle_page_number, position, font_size, margin, entry, render_options)
            if _physical_markers_enabled(render_options) and entry and bundle_page_number == entry.page_range.start:
                draw_physical_flag_marker(page, entry.item_number, len(entries), entry.flag_colour)

        for link in index_links:
            page_number = int(link["index_page"])
            target_page = int(link["target_page"]) + index_page_count
            if 0 <= page_number < output_doc.page_count and 0 <= target_page < output_doc.page_count:
                page = output_doc[page_number]
                rect = fitz.Rect(float(link["x0"]), float(link["y0"]), float(link["x1"]), float(link["y1"]))
                page.insert_link({"kind": fitz.LINK_GOTO, "from": rect, "page": target_page})

        _set_toc(output_doc, toc)
        output_doc.save(output_path, garbage=4, deflate=True)
    finally:
        output_doc.close()
    _ensure_saved_toc(output_path, toc)


def _set_toc(doc: fitz.Document, toc: list[list[int | str]]) -> None:
    if toc:
        doc.set_toc(toc)


def _display_toc_title(item: PDFItem) -> str:
    raw_title = item.title.strip() or clean_filename_title(item.path)
    return normalize_legal_display_title(raw_title)


def draw_physical_flag_marker(
    page: fitz.Page,
    item_number: int,
    item_count: int,
    colour_hex: str | None,
) -> None:
    if item_count <= 0 or colour_hex is None:
        return
    page_rect = page.rect
    marker_width = 14.0
    marker_height = 36.0
    top_margin = 54.0
    bottom_margin = 54.0
    usable_height = max(marker_height, page_rect.height - top_margin - bottom_margin - marker_height)
    if item_count == 1:
        y0 = page_rect.y0 + top_margin
    else:
        y0 = page_rect.y0 + top_margin + usable_height * ((item_number - 1) / (item_count - 1))
    y0 = min(max(page_rect.y0 + top_margin, y0), page_rect.y1 - bottom_margin - marker_height)
    rect = fitz.Rect(page_rect.x1 - marker_width, y0, page_rect.x1, y0 + marker_height)
    page.draw_rect(rect, color=None, fill=_hex_to_rgb(colour_hex), fill_opacity=0.85, width=0)


def _build_entries(
    pdf_items: Sequence[PDFItem],
    render_options: PdfBundleRenderOptions | None,
) -> list[BundleIndexEntry]:
    return build_bundle_index_entries(
        pdf_items,
        get_page_count=lambda item: get_pdf_page_count(item.path),
        flag_colours=None if render_options is None else render_options.flag_colours,
    )


def _entry_for_bundle_page(entries: Sequence[BundleIndexEntry], page_number: int) -> BundleIndexEntry | None:
    for entry in entries:
        if entry.page_range.start <= page_number <= entry.page_range.end:
            return entry
    return None


def _draw_number_for_entry(
    page: fitz.Page,
    page_number: int,
    position: str,
    font_size: int,
    margin: int,
    entry: BundleIndexEntry | None,
    render_options: PdfBundleRenderOptions | None,
) -> None:
    if entry and entry.flag_colour:
        draw_page_number(
            page,
            page_number,
            position,
            font_size,
            margin,
            fill_colour=entry.flag_colour,
            fill_opacity=_number_fill_opacity(render_options),
        )
        return
    draw_page_number(page, page_number, position, font_size, margin)


def _hex_to_rgb(colour_hex: str) -> tuple[float, float, float]:
    colour = normalize_flag_colour(colour_hex).lstrip("#")
    return (
        int(colour[0:2], 16) / 255,
        int(colour[2:4], 16) / 255,
        int(colour[4:6], 16) / 255,
    )


def _number_fill_opacity(render_options: PdfBundleRenderOptions | None) -> float:
    return 1.0 if render_options is None else render_options.number_fill_opacity


def _physical_markers_enabled(render_options: PdfBundleRenderOptions | None) -> bool:
    return bool(render_options and render_options.physical_flag_markers)


def _ensure_saved_toc(output_path: Path, toc: list[list[int | str]]) -> None:
    """Persist PDF outlines and repair them if a backend produced a file without one."""
    if not toc:
        return

    repaired_path: Path | None = None
    doc = fitz.open(output_path)
    try:
        if doc.get_toc():
            return
        doc.set_toc(toc)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=output_path.parent) as handle:
            repaired_path = Path(handle.name)
        doc.save(repaired_path, garbage=4, deflate=True)
    finally:
        doc.close()
    if repaired_path is not None:
        repaired_path.replace(output_path)
