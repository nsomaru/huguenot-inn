from pathlib import Path

import fitz

from huguenot.domain import (
    Court,
    Matter,
    Party,
    PartySide,
    PDFItem,
    ProceedingType,
    matter_output_filename,
    matter_output_root,
)
from huguenot.domain.output_names import safe_filename_token
from huguenot.pdf import combine_with_front_index


def make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    try:
        page = doc.new_page()
        page.insert_text((72, 72), text)
        doc.save(path)
    finally:
        doc.close()


def test_matter_output_root_uses_first_bringing_and_opposing_parties() -> None:
    matter = Matter(
        court=Court("Court"),
        proceeding_type=ProceedingType.APPLICATION,
        parties=(
            Party("Axim (Pty) Ltd", PartySide.BRINGING, 1),
            Party("Moodie N.O.", PartySide.OPPOSING, 1),
        ),
    )

    assert matter_output_root(matter) == "axim-pty-ltd_v_moodie-n-o"
    assert (
        matter_output_filename(matter, "AUTHORITIES_BUNDLE", ".pdf")
        == "axim-pty-ltd_v_moodie-n-o_AUTHORITIES_BUNDLE.pdf"
    )


def test_safe_filename_token_preserves_readable_text() -> None:
    assert safe_filename_token("  1st Applicant / Alpha: Beta?  ") == "1st-applicant-alpha-beta"


def test_combine_with_front_index_accepts_matter_toc_root_without_changing_default(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    index = tmp_path / "index.pdf"
    default_output = tmp_path / "default.pdf"
    matter_output = tmp_path / "matter.pdf"
    make_pdf(source, "Authority")
    make_pdf(index, "Index")

    combine_with_front_index([PDFItem(source, "Authority")], index, [], default_output, "Bottom centre", 12, 28)
    combine_with_front_index(
        [PDFItem(source, "Authority")],
        index,
        [],
        matter_output,
        "Bottom centre",
        12,
        28,
        toc_root_title="axim-pty-ltd_v_moodie-n-o",
    )

    default_doc = fitz.open(default_output)
    matter_doc = fitz.open(matter_output)
    try:
        assert default_doc.get_toc()[0] == [1, "Index", 1]
        assert matter_doc.get_toc()[0] == [1, "axim-pty-ltd_v_moodie-n-o", 1]
    finally:
        default_doc.close()
        matter_doc.close()
