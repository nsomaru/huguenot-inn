from pathlib import Path

import fitz

from huguenot.pdf import detect_authority_index_item
from huguenot.pdf.authority_detection import clean_filename_title


def make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    try:
        page = doc.new_page()
        page.insert_text((72, 72), text)
        doc.save(path)
    finally:
        doc.close()


def test_detect_authority_index_item_preserves_citation_detection(tmp_path: Path) -> None:
    pdf = tmp_path / "judgment.pdf"
    make_pdf(pdf, "Neutral citation: S v Makwanyane [1995] ZACC 3")

    assert detect_authority_index_item(pdf) == "S v Makwanyane [1995] ZACC 3"


def test_clean_filename_title_is_used_as_safe_fallback() -> None:
    assert clean_filename_title(Path("001_authority_bundle-copy.pdf")) == "001 authority bundle-copy"
