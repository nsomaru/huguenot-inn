from __future__ import annotations

from pathlib import Path

import fitz

from huguenot.domain import PDFItem

from .authority_detection import clean_filename_title

POSITIONS = [
    "Bottom centre",
    "Bottom right",
    "Bottom left",
    "Top centre",
    "Top right",
    "Top left",
]


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


def draw_page_number(page: fitz.Page, number: int, position: str, font_size: int = 15, margin: int = 28) -> None:
    text = str(number)
    page_rect = page.rect
    fontname = "hebo"
    text_width = fitz.get_text_length(text, fontname=fontname, fontsize=font_size)
    box_width = max(34, text_width + 18)
    box_height = font_size + 12
    box = get_number_box(page_rect, position, box_width, box_height, margin)
    page.draw_rect(
        box,
        color=(0, 0, 0),
        fill=(1, 1, 1),
        width=0.6,
        fill_opacity=1.0,
        stroke_opacity=0.65,
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
    pdf_items: list[PDFItem], output_path: Path, position: str, font_size: int, margin: int
) -> None:
    if not pdf_items:
        raise ValueError("No PDFs selected.")

    output_doc = fitz.open()
    toc: list[list[int | str]] = []
    try:
        current_start_page = 1
        for item in pdf_items:
            source = fitz.open(item.path)
            try:
                if source.page_count == 0:
                    continue
                toc_title = item.title.strip() or clean_filename_title(item.path)
                toc.append([1, toc_title, current_start_page])
                output_doc.insert_pdf(source)
                current_start_page += source.page_count
            finally:
                source.close()

        for index in range(output_doc.page_count):
            page = output_doc[index]
            draw_page_number(page, index + 1, position, font_size, margin)

        if toc:
            output_doc.set_toc(toc)
        output_doc.save(output_path, garbage=4, deflate=True)
    finally:
        output_doc.close()


def combine_with_front_index(
    pdf_items: list[PDFItem],
    index_pdf_path: Path,
    index_links: list[dict[str, int | float]],
    output_path: Path,
    position: str,
    font_size: int,
    margin: int,
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

    toc: list[list[int | str]] = [[1, "Index", 1]]
    current_start_page = index_page_count + 1
    try:
        for item in pdf_items:
            source = fitz.open(item.path)
            try:
                if source.page_count == 0:
                    continue
                toc_title = item.title.strip() or clean_filename_title(item.path)
                toc.append([1, toc_title, current_start_page])
                output_doc.insert_pdf(source)
                current_start_page += source.page_count
            finally:
                source.close()

        for index in range(output_doc.page_count):
            page = output_doc[index]
            draw_page_number(page, index + 1, position, font_size, margin)

        for link in index_links:
            page_number = int(link["index_page"])
            target_page = int(link["target_page"]) + index_page_count
            if 0 <= page_number < output_doc.page_count and 0 <= target_page < output_doc.page_count:
                page = output_doc[page_number]
                rect = fitz.Rect(float(link["x0"]), float(link["y0"]), float(link["x1"]), float(link["y1"]))
                page.insert_link({"kind": fitz.LINK_GOTO, "from": rect, "page": target_page})

        output_doc.set_toc(toc)
        output_doc.save(output_path, garbage=4, deflate=True)
    finally:
        output_doc.close()
