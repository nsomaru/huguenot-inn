from pathlib import Path

import fitz
import pytest

from huguenot.pdf import detect_authority_index_item
from huguenot.pdf.authority_detection import clean_filename_title, titlecase_parties_before_year


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


def test_detect_authority_index_item_uses_afrikaans_legal_title_casing(tmp_path: Path) -> None:
    pdf = tmp_path / "judgment.pdf"
    make_pdf(pdf, "Neutral citation: S V BOTHA EN 'N ANDER [2024] ZASCA 1")

    assert detect_authority_index_item(pdf) == "S v Botha en 'n Ander [2024] ZASCA 1"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "BASSON v CHILWAN AND OTHERS [1993] 2 All SA 373 (A)",
            "Basson v Chilwan and Others [1993] 2 All SA 373 (A)",
        ),
        (
            "TRANS - DRAKENSBERG BANK LTD (UNDER JUDICIAL MANAGEMENT) v "
            "COMBINED ENGINEERING (PTY) LTD AND ANOTHER 1967 (3) SA 632 (D)",
            "Trans - Drakensberg Bank Ltd (Under Judicial Management) v "
            "Combined Engineering (Pty) Ltd and Another 1967 (3) SA 632 (D)",
        ),
        (
            "CIBA-GEIGY (PTY) LTD v LUSHOF FARMS (PTY) LTD EN 'N ANDER 2002 (2) SA 447 (SCA)",
            "Ciba-Geigy (Pty) Ltd v Lushof Farms (Pty) Ltd en 'n Ander 2002 (2) SA 447 (SCA)",
        ),
    ],
)
def test_titlecase_parties_before_year_restores_mixed_case_citation_title_casing(source: str, expected: str) -> None:
    assert titlecase_parties_before_year(source) == expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("case_1.pdf", "Automotive Tooling Systems (Pty) Ltd v Wilkens and Others [2007] 4 All SA 1073 (SCA)"),
        (
            "case_10.pdf",
            "Trans - Drakensberg Bank Ltd (Under Judicial Management) v "
            "Combined Engineering (Pty) Ltd and Another 1967 (3) SA 632 (D)",
        ),
        ("case_11.pdf", "Labournet (Pty) Ltd v Jankielsohn and Another [2017] JOL 38369 (LAC)"),
        ("case_12.pdf", "Meter Systems Holdings Ltd v Venter and Another [1993] 3 All SA 574 (W)"),
        (
            "case_13.pdf",
            "Pexmart CC and Others v H Mocke Construction (Pty) Ltd and Another [2019] 1 All SA 335 (SCA)",
        ),
        ("case_14.pdf", "Reddy v Siemens Telecommunications (Pty) Ltd [2006] JOL 18829 (SCA)"),
        ("case_15.pdf", "Waste Products Utilisation (Pty) Ltd v Wilkes and Others [2001] JOL 8924 (W)"),
        ("case_16.pdf", "Ball v Bambalela Bolts (Pty) Ltd and Another [2017] JOL 37209 (LAC)"),
        ("case_17.pdf", "Caxton Ltd and Others v Reeva Forman (Pty) Ltd and Another 1990 (3) SA 547 (A)"),
        ("case_18.pdf", "Cgu Insurance Ltd v Rumdel Construction (Pty) Ltd 2004 (2) SA 622 (SCA)"),
        (
            "case_19.pdf",
            "Ciba-Geigy (Pty) Ltd v Lushof Farms (Pty) Ltd en 'n Ander 2002 (2) SA 447 (SCA)",
        ),
        ("case_2.pdf", "Ball v Bambalela Bolts (Pty) Ltd and Another [2017] JOL 37209 (LAC)"),
        ("case_3.pdf", "Basson v Chilwan and Others [1993] 2 All SA 373 (A)"),
        ("case_4.pdf", "Beedle v Slo-Jo Innovations Hub (Pty) Ltd [2023] JOL 60553 (LAC)"),
        ("case_5.pdf", "Automotive Tooling Systems (Pty) Ltd v Wilkens and Others [2007] 4 All SA 1073 (SCA)"),
        ("case_6.pdf", "Vox Telecommunications (Pty) Ltd v Steyn & Another (2016) 37 ILJ 1255 (LC)"),
        ("case_7.pdf", "Cross v Ferreira 1950 (3) SA 443 (C)"),
        ("case_8.pdf", "Park Finance Corporation (Pty) Ltd v Van Niekerk 1956 (1) SA 669 (T)"),
        ("case_9.pdf", "Stroud v Steel Engineering Co Ltd and Another 1996 (4) SA 1139 (W)"),
    ],
)
def test_examples_cases_keep_pre_regression_citation_title_casing(filename: str, expected: str) -> None:
    assert detect_authority_index_item(Path("examples/cases") / filename) == expected


def test_clean_filename_title_is_used_as_safe_fallback() -> None:
    assert clean_filename_title(Path("001_authority_bundle-copy.pdf")) == "001 authority bundle-copy"
