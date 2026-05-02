import pytest

from huguenot.domain.legal_titles import normalize_legal_display_title, should_normalize_legal_title


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("S V BOTHA EN 'N ANDER", "S v Botha en 'n Ander"),
        ("VAN DER MERWE V MINISTER VAN POLISIE", "Van der Merwe v Minister van Polisie"),
        (
            "LE ROUX EN 'N ANDER V JOHANNES G COETZEE & SEUNS EN 'N ANDER",
            "Le Roux en 'n Ander v Johannes G Coetzee & Seuns en 'n Ander",
        ),
        (
            "JANSE VAN RENSBURG V DIE MEESTER VAN DIE HOOGGEREGSHOF",
            "Janse van Rensburg v Die Meester van die Hooggeregshof",
        ),
        ("DIE HOOGSTE HOF VAN APPÈL VAN SUID-AFRIKA", "Die Hoogste Hof van Appèl van Suid-Afrika"),
        ("IN DIE SAAK TUSSEN:", "In die saak tussen:"),
        ("MINISTER VAN VEILIGHEID EN SEKURITEIT", "Minister van Veiligheid en Sekuriteit"),
        ("'N BORGAANSOEK IS STRAFVERRIGTINGE", "'n Borgaansoek is strafverrigtinge"),
        (
            "BK TOOLING (EDMS) BPK V SCOPE PRECISION ENGINEERING (EDMS) BPK",
            "BK Tooling (Edms) Bpk v Scope Precision Engineering (Edms) Bpk",
        ),
        ("PLAASLIKE BOEREDIENSTE (EDMS) BPK. V CHEMFOS BPK.", "Plaaslike Boeredienste (Edms) Bpk. v Chemfos Bpk."),
        (
            "BON ACCOR SAFARIS (EDMS) BPK AND OTHERS V MASILONYANA MUNICIPALITY",
            "Bon Accor Safaris (Edms) Bpk and Others v Masilonyana Municipality",
        ),
        ("ABSA BANK BPK V ERF 1252 MARINE DRIVE (EDMS) BPK", "ABSA Bank Bpk v Erf 1252 Marine Drive (Edms) Bpk"),
        ("ACL GROUP (EDMS) BPK V QICK TELEVENTURES FZE", "ACL Group (Edms) Bpk v Qick Televentures FZE"),
        ("SA KALK & GIPS (EDMS) BPK V KROG", "SA Kalk & Gips (Edms) Bpk v Krog"),
        ("ALPHA (PTY) LTD T/A BETA V GAMMA CC", "Alpha (Pty) Ltd t/a Beta v Gamma CC"),
        ("MOODIE N.O. EN ANDERE V DIE STAAT", "Moodie N.O. en Andere v Die Staat"),
    ],
)
def test_normalize_legal_display_title_handles_afrikaans_legal_fixtures(source: str, expected: str) -> None:
    assert normalize_legal_display_title(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "President of the Republic of South Africa v Hugo",
        "Free State Cheetahs (Pty) Limited v Mapoe",
        "F v Minister of Safety and Security and Another",
        "Custom MIXED Case User Title",
        "HOE HOF",
    ],
)
def test_normalize_legal_display_title_preserves_guardrails(source: str) -> None:
    assert normalize_legal_display_title(source) == source


def test_normalize_legal_display_title_preserves_citation_tail() -> None:
    assert (
        normalize_legal_display_title("S V BOTHA EN 'N ANDER [2024] ZASCA 1") == "S v Botha en 'n Ander [2024] ZASCA 1"
    )


def test_should_normalize_legal_title_exposes_conservative_safety_decision() -> None:
    assert should_normalize_legal_title("S V BOTHA EN 'N ANDER")
    assert not should_normalize_legal_title("Custom MIXED Case User Title")
