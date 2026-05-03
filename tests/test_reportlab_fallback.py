from pathlib import Path

import fitz
from reportlab.lib.units import mm

from huguenot.documents import PDFRenderer, RendererPreference, ReportLabIndexRenderer, render_matter_index_pdf
from huguenot.domain import Court, DocumentHeaderInput, Matter, Party, PartySide, PDFItem, ProceedingType


def make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    try:
        page = doc.new_page()
        page.insert_text((72, 72), text)
        doc.save(path)
    finally:
        doc.close()


def _rgb_close(actual: object, expected: tuple[float, float, float]) -> bool:
    return (
        isinstance(actual, tuple)
        and len(actual) == 3
        and all(abs(float(actual[index]) - expected[index]) < 0.01 for index in range(3))
    )


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


def test_reportlab_fallback_can_colour_page_range_cell_right_border(tmp_path: Path) -> None:
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

    from huguenot.documents import get_index_entries

    entries = get_index_entries([PDFItem(source, "Authority title")], flag_colours=["#3467A5"])
    ReportLabIndexRenderer().render_pdf(
        matter,
        DocumentHeaderInput("Respondents' Authorities Bundle"),
        [PDFItem(source, "Authority title")],
        output,
        index_entries=entries,
        colour_page_ranges=True,
    )

    doc = fitz.open(output)
    try:
        drawings = doc[0].get_drawings()
        flag_rgb = (0x34 / 255, 0x67 / 255, 0xA5 / 255)
        assert not any(_rgb_close(drawing.get("fill"), flag_rgb) for drawing in drawings)
        coloured_strokes = [
            drawing
            for drawing in drawings
            if _rgb_close(drawing.get("color"), flag_rgb) and abs(float(drawing.get("width", 0)) - 4) < 0.01
        ]
        assert coloured_strokes
    finally:
        doc.close()


def test_reportlab_fallback_normalizes_afrikaans_authority_titles(tmp_path: Path) -> None:
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

    ReportLabIndexRenderer().render_pdf(
        matter,
        DocumentHeaderInput("Respondents' Authorities Bundle"),
        [PDFItem(source, "S V BOTHA EN 'N ANDER")],
        output,
    )

    doc = fitz.open(output)
    try:
        assert "S v Botha en 'n Ander" in doc[0].get_text()
    finally:
        doc.close()


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
        assert "1" in doc[0].get_text()
    finally:
        doc.close()


def test_matter_index_pdf_reportlab_choice_uses_visible_page_one(tmp_path: Path) -> None:
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

    used_libreoffice, links = render_matter_index_pdf(
        matter,
        DocumentHeaderInput("Respondents' Authorities Bundle"),
        [PDFItem(source, "Authority title")],
        output,
        renderer_preference=RendererPreference(PDFRenderer.REPORTLAB),
    )

    assert used_libreoffice is False
    assert links and links[0]["target_page"] == 0
    doc = fitz.open(output)
    try:
        text = doc[0].get_text()
        assert "Authority title\n1\n" in text
    finally:
        doc.close()


def test_reportlab_party_label_splits_ordinal_for_superscript_drawing() -> None:
    renderer = ReportLabIndexRenderer()

    assert renderer._ordinal_segments("1st Applicant") == ("1", "st", " Applicant")  # noqa: SLF001
    assert renderer._ordinal_segments("22nd Defendant") == ("22", "nd", " Defendant")  # noqa: SLF001


def test_reportlab_heading_tramlines_are_spaced_from_heading(tmp_path: Path) -> None:
    source = tmp_path / "authority.pdf"
    make_pdf(source, "Authority")
    output = tmp_path / "index.pdf"
    matter = Matter(
        court=Court("IN THE HIGH COURT OF SOUTH AFRICA", "(GAUTENG DIVISION, JOHANNESBURG)"),
        proceeding_type=ProceedingType.APPLICATION,
        case_number="2026-086328",
        parties=(
            Party("First Applicant", PartySide.BRINGING, 1),
            Party("Second Applicant", PartySide.BRINGING, 2),
            Party("First Respondent", PartySide.OPPOSING, 1),
            Party("Second Respondent", PartySide.OPPOSING, 2),
        ),
    )

    ReportLabIndexRenderer().render_pdf(
        matter,
        DocumentHeaderInput("Respondents' Authorities Bundle"),
        [PDFItem(source, "Authority title")],
        output,
    )

    doc = fitz.open(output)
    try:
        drawings = doc[0].get_drawings()
        horizontal_lines = [
            item
            for drawing in drawings
            for item in drawing["items"]
            if item[0] == "l" and abs(item[1].y - item[2].y) < 0.1
        ]
        assert len(horizontal_lines) >= 2
        heading_lines = [item for item in horizontal_lines if abs(item[1].x - 24 * mm) < 1]
        assert len(heading_lines) >= 2
        assert all(abs(item[2].x - (doc[0].rect.width - 24 * mm)) < 1 for item in heading_lines[:2])
        assert abs(heading_lines[0][1].y - heading_lines[1][1].y) >= 14 * mm
        text = doc[0].get_text()
        assert "1st Applicant" in text
        assert "2nd Respondent" in text
    finally:
        doc.close()
