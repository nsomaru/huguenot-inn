from pathlib import Path

import fitz

from huguenot.documents import ReportLabIndexRenderer, render_matter_index_pdf
from huguenot.domain import Court, DocumentHeaderInput, Matter, Party, PartySide, PDFItem, ProceedingType


def make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    try:
        page = doc.new_page()
        page.insert_text((72, 72), text)
        doc.save(path)
    finally:
        doc.close()


def test_reportlab_fallback_renders_pdf_and_link_rects(tmp_path: Path) -> None:
    source = tmp_path / "authority.pdf"
    make_pdf(source, "Authority")
    output = tmp_path / "index.pdf"
    matter = Matter(
        court=Court("IN THE HIGH COURT OF SOUTH AFRICA", "(GAUTENG DIVISION, JOHANNESBURG)"),
        proceeding_type=ProceedingType.APPLICATION,
        case_number="2026-086328",
        parties=(
            Party("Axim (Pty) Ltd", PartySide.BRINGING, 1),
            Party("Moodie", PartySide.OPPOSING, 1),
        ),
    )

    links = ReportLabIndexRenderer().render_pdf(
        matter,
        DocumentHeaderInput("Respondents' Authorities Bundle"),
        [PDFItem(source, "Authority title")],
        output,
        start_page=2,
    )

    doc = fitz.open(output)
    try:
        text = doc[0].get_text()
        assert "IN THE HIGH COURT OF SOUTH AFRICA" in text
        assert "Authority title" in text
        assert "2" in text
    finally:
        doc.close()
    assert links and links[0]["target_page"] == 0


def test_matter_index_pdf_falls_back_when_libreoffice_missing(tmp_path: Path) -> None:
    source = tmp_path / "authority.pdf"
    make_pdf(source, "Authority")
    output = tmp_path / "index.pdf"
    matter = Matter(
        court=Court("IN THE HIGH COURT OF SOUTH AFRICA", "(GAUTENG DIVISION, JOHANNESBURG)"),
        proceeding_type=ProceedingType.APPLICATION,
        case_number="2026-086328",
        parties=(
            Party("Axim (Pty) Ltd", PartySide.BRINGING, 1),
            Party("Moodie", PartySide.OPPOSING, 1),
        ),
    )

    class MissingConverter:
        def libreoffice_available(self) -> bool:
            return False

    used_libreoffice, links = render_matter_index_pdf(
        matter,
        DocumentHeaderInput("Respondents' Authorities Bundle"),
        [PDFItem(source, "Authority title")],
        output,
        converter=MissingConverter(),  # type: ignore[arg-type]
    )

    assert used_libreoffice is False
    assert output.exists()
    assert links
    doc = fitz.open(output)
    try:
        assert "2" in doc[0].get_text()
    finally:
        doc.close()
