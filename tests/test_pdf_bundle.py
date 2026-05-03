import inspect
from pathlib import Path
from typing import Any

import fitz

from huguenot.application import protocols
from huguenot.domain import PDFItem
from huguenot.domain.page_numbering import DEFAULT_NUMBER_FONT_SIZE, DEFAULT_NUMBER_MARGIN, DEFAULT_NUMBER_POSITION
from huguenot.pdf import PdfBundleRenderOptions, combine_number_and_add_toc, combine_with_front_index
from huguenot.pdf.bundle import draw_page_number, get_number_box, number_box_size


def make_pdf(path: Path, text: str, pages: int = 1) -> None:
    doc = fitz.open()
    try:
        for _ in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), text)
        doc.save(path)
    finally:
        doc.close()


def test_combine_number_and_add_toc_preserves_no_matter_behavior(tmp_path: Path) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    make_pdf(first, "First", pages=1)
    make_pdf(second, "Second", pages=2)
    output = tmp_path / "combined.pdf"

    combine_number_and_add_toc(
        [PDFItem(first, "First authority"), PDFItem(second, "Second authority")],
        output,
        "Bottom centre",
        12,
        28,
    )

    doc = fitz.open(output)
    try:
        assert doc.page_count == 3
        assert doc.get_toc() == [[1, "First authority", 1], [1, "Second authority", 2]]
    finally:
        doc.close()


def test_numbering_defaults_are_shared_without_pdf_import_in_protocols() -> None:
    assert DEFAULT_NUMBER_POSITION == "Top right"
    assert DEFAULT_NUMBER_FONT_SIZE == 12
    assert DEFAULT_NUMBER_MARGIN == 28
    signature = inspect.signature(protocols.PdfBundler.combine_number_and_add_toc)
    assert signature.parameters["position"].default == DEFAULT_NUMBER_POSITION
    assert signature.parameters["font_size"].default == DEFAULT_NUMBER_FONT_SIZE
    assert signature.parameters["margin"].default == DEFAULT_NUMBER_MARGIN
    assert "huguenot.pdf" not in inspect.getsource(protocols)


def test_combine_with_front_index_adds_link_to_target_page(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    index = tmp_path / "index.pdf"
    output = tmp_path / "combined.pdf"
    make_pdf(source, "Authority", pages=1)
    make_pdf(index, "Index", pages=1)

    combine_with_front_index(
        [PDFItem(source, "Authority")],
        index,
        [{"index_page": 0, "target_page": 0, "x0": 50, "y0": 50, "x1": 150, "y1": 80}],
        output,
        "Bottom centre",
        12,
        28,
    )

    doc = fitz.open(output)
    try:
        assert doc.page_count == 2
        links = doc[0].get_links()
        assert links
        assert links[0]["page"] == 1
    finally:
        doc.close()


def test_combine_with_front_index_numbers_attached_documents_from_one(tmp_path: Path) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    index = tmp_path / "index.pdf"
    output = tmp_path / "combined.pdf"
    make_pdf(first, "First authority", pages=1)
    make_pdf(second, "Second authority", pages=1)
    make_pdf(index, "Front index", pages=1)

    combine_with_front_index(
        [PDFItem(first, "First authority"), PDFItem(second, "Second authority")],
        index,
        [{"index_page": 0, "target_page": 1, "x0": 50, "y0": 50, "x1": 150, "y1": 80}],
        output,
        "Bottom centre",
        12,
        28,
    )

    doc = fitz.open(output)
    try:
        assert doc.page_count == 3
        assert "Front index" in doc[0].get_text()
        assert " 1\n" not in f" {doc[0].get_text()}\n"
        assert "1" in doc[1].get_text()
        assert "2" in doc[2].get_text()
        assert doc[0].get_links()[0]["page"] == 2
        assert doc.get_toc() == [[1, "Index", 1], [1, "First authority", 2], [1, "Second authority", 3]]
    finally:
        doc.close()


def test_bundle_functions_use_default_position_font_and_margin(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    index = tmp_path / "index.pdf"
    output = tmp_path / "combined.pdf"
    front_output = tmp_path / "front.pdf"
    make_pdf(source, "Authority", pages=1)
    make_pdf(index, "Index", pages=1)
    calls: list[tuple[int, str, int, int]] = []

    def fake_draw_page_number(
        page: fitz.Page, number: int, position: str, font_size: int = 12, margin: int = 28
    ) -> None:
        calls.append((number, position, font_size, margin))

    monkeypatch.setattr("huguenot.pdf.bundle.draw_page_number", fake_draw_page_number)

    combine_number_and_add_toc([PDFItem(source, "Authority")], output)
    combine_with_front_index([PDFItem(source, "Authority")], index, [], front_output)

    assert calls == [
        (1, DEFAULT_NUMBER_POSITION, DEFAULT_NUMBER_FONT_SIZE, DEFAULT_NUMBER_MARGIN),
        (1, DEFAULT_NUMBER_POSITION, DEFAULT_NUMBER_FONT_SIZE, DEFAULT_NUMBER_MARGIN),
    ]


def test_number_box_size_scales_with_font_and_text_width() -> None:
    small = number_box_size("9", font_size=12)
    large_font = number_box_size("9", font_size=24)
    multi_digit = number_box_size("100", font_size=12)

    assert large_font.width > small.width
    assert large_font.height > small.height
    assert multi_digit.width > small.width


def test_get_number_box_default_top_right_geometry() -> None:
    size = number_box_size("1", font_size=DEFAULT_NUMBER_FONT_SIZE)
    box = get_number_box(
        fitz.Rect(0, 0, 200, 300),
        DEFAULT_NUMBER_POSITION,
        size.width,
        size.height,
        DEFAULT_NUMBER_MARGIN,
    )

    assert box.x1 == 200 - DEFAULT_NUMBER_MARGIN
    assert box.y0 == DEFAULT_NUMBER_MARGIN


def test_draw_page_number_uses_transparent_rectangle_background(tmp_path: Path) -> None:
    output = tmp_path / "numbered.pdf"
    doc = fitz.open()
    try:
        page = doc.new_page()
        draw_page_number(page, 1, DEFAULT_NUMBER_POSITION, DEFAULT_NUMBER_FONT_SIZE, DEFAULT_NUMBER_MARGIN)
        drawings: list[dict[str, Any]] = page.get_drawings()
        number_rects = [drawing for drawing in drawings if drawing.get("type") in {"s", "fs"}]
        assert number_rects
        assert all(drawing.get("fill") is None or drawing.get("fill_opacity") == 0 for drawing in number_rects)
        doc.save(output)
    finally:
        doc.close()


def test_draw_page_number_can_use_translucent_flag_colour(tmp_path: Path) -> None:
    output = tmp_path / "numbered.pdf"
    doc = fitz.open()
    try:
        page = doc.new_page()
        draw_page_number(
            page,
            1,
            DEFAULT_NUMBER_POSITION,
            DEFAULT_NUMBER_FONT_SIZE,
            DEFAULT_NUMBER_MARGIN,
            fill_colour="#3467A5",
            fill_opacity=0.25,
        )
        drawings: list[dict[str, Any]] = page.get_drawings()
        filled = [drawing for drawing in drawings if drawing.get("fill") is not None]
        assert filled
        assert any(abs(float(drawing.get("fill_opacity", 0)) - 0.25) < 0.01 for drawing in filled)
        doc.save(output)
    finally:
        doc.close()


def test_counsel_no_matter_bundle_colours_number_boxes_and_markers(tmp_path: Path) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    make_pdf(first, "First", pages=2)
    make_pdf(second, "Second", pages=1)
    output = tmp_path / "counsel.pdf"

    combine_number_and_add_toc(
        [PDFItem(first, "First authority"), PDFItem(second, "Second authority")],
        output,
        render_options=PdfBundleRenderOptions(flag_colours=["#3467A5", "#71B735"], physical_flag_markers=True),
    )

    doc = fitz.open(output)
    try:
        assert doc.page_count == 3
        page0_fills = [drawing for drawing in doc[0].get_drawings() if drawing.get("fill") is not None]
        page1_fills = [drawing for drawing in doc[1].get_drawings() if drawing.get("fill") is not None]
        page2_fills = [drawing for drawing in doc[2].get_drawings() if drawing.get("fill") is not None]
        assert len(page0_fills) > len(page1_fills)
        assert len(page2_fills) > len(page1_fills)
        assert page1_fills
        assert all(abs(float(drawing.get("fill_opacity", 0)) - 1) < 0.01 for drawing in page1_fills)
    finally:
        doc.close()


def test_counsel_front_index_markers_skip_index_pages_and_can_be_disabled(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    index = tmp_path / "index.pdf"
    output = tmp_path / "combined.pdf"
    disabled_output = tmp_path / "disabled.pdf"
    make_pdf(source, "Authority", pages=1)
    make_pdf(index, "Index", pages=2)

    combine_with_front_index(
        [PDFItem(source, "Authority")],
        index,
        [],
        output,
        render_options=PdfBundleRenderOptions(flag_colours=["#3467A5"], physical_flag_markers=True),
    )
    combine_with_front_index(
        [PDFItem(source, "Authority")],
        index,
        [],
        disabled_output,
        render_options=PdfBundleRenderOptions(flag_colours=["#3467A5"], physical_flag_markers=False),
    )

    doc = fitz.open(output)
    disabled_doc = fitz.open(disabled_output)
    try:
        assert all(
            not [drawing for drawing in doc[index_page].get_drawings() if drawing.get("fill") is not None]
            for index_page in (0, 1)
        )
        enabled_item_fills = [drawing for drawing in doc[2].get_drawings() if drawing.get("fill") is not None]
        disabled_item_fills = [drawing for drawing in disabled_doc[2].get_drawings() if drawing.get("fill") is not None]
        assert len(enabled_item_fills) == len(disabled_item_fills) + 1
        assert disabled_item_fills
    finally:
        doc.close()
        disabled_doc.close()
