from pathlib import Path

import fitz
from docx import Document

from huguenot.documents import create_authorities_index_docx, create_matter_authorities_index_docx
from huguenot.domain import Court, DocumentHeaderInput, Matter, Party, PartySide, PDFItem, ProceedingType


def make_pdf(path: Path, text: str, pages: int = 1) -> None:
    doc = fitz.open()
    try:
        for _ in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), text)
        doc.save(path)
    finally:
        doc.close()


def test_plain_authorities_index_uses_page_ranges(tmp_path: Path) -> None:
    pdf = tmp_path / "authority.pdf"
    make_pdf(pdf, "Authority", pages=2)
    output = tmp_path / "index.docx"

    create_authorities_index_docx([PDFItem(pdf, "Authority title")], output)

    doc = Document(str(output))
    assert doc.tables[0].cell(1, 1).text == "Authority title"
    assert doc.tables[0].cell(1, 2).text == "1-2"


def test_matter_authorities_index_contains_header_parties_and_document_title(tmp_path: Path) -> None:
    pdf = tmp_path / "authority.pdf"
    make_pdf(pdf, "Authority", pages=1)
    output = tmp_path / "matter_index.docx"
    matter = Matter(
        court=Court("IN THE HIGH COURT OF SOUTH AFRICA", "(GAUTENG DIVISION, JOHANNESBURG)"),
        proceeding_type=ProceedingType.APPLICATION,
        case_number="2026-086328",
        parties=(
            Party("Axim (Pty) Ltd", PartySide.BRINGING, 1),
            Party("Moodie", PartySide.OPPOSING, 1),
        ),
    )

    create_matter_authorities_index_docx(
        matter,
        DocumentHeaderInput("Respondents' Authorities Bundle"),
        [PDFItem(pdf, "Authority title")],
        output,
    )

    text = "\n".join(p.text for p in Document(str(output)).paragraphs)
    assert "IN THE HIGH COURT OF SOUTH AFRICA" in text
    assert "2026-086328" in text
    assert "RESPONDENTS' AUTHORITIES BUNDLE" in text
