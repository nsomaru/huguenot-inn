from pathlib import Path

import fitz

from huguenot.domain import PDFItem
from huguenot.pdf import combine_number_and_add_toc, combine_with_front_index


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
