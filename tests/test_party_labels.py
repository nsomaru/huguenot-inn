from huguenot.domain import PartySide, ProceedingType, party_label


def test_action_party_labels_singular_and_plural() -> None:
    assert party_label(ProceedingType.ACTION, PartySide.BRINGING, 1, 1) == "Plaintiff"
    assert party_label(ProceedingType.ACTION, PartySide.OPPOSING, 1, 1) == "Defendant"
    assert party_label(ProceedingType.ACTION, PartySide.BRINGING, 1, 2) == "1st Plaintiff"
    assert party_label(ProceedingType.ACTION, PartySide.BRINGING, 2, 2) == "2nd Plaintiff"
    assert party_label(ProceedingType.ACTION, PartySide.OPPOSING, 3, 3) == "3rd Defendant"


def test_application_party_labels_singular_and_plural() -> None:
    assert party_label(ProceedingType.APPLICATION, PartySide.BRINGING, 1, 1) == "Applicant"
    assert party_label(ProceedingType.APPLICATION, PartySide.OPPOSING, 1, 1) == "Respondent"
    assert party_label(ProceedingType.APPLICATION, PartySide.BRINGING, 1, 2) == "1st Applicant"
    assert party_label(ProceedingType.APPLICATION, PartySide.OPPOSING, 4, 4) == "4th Respondent"
