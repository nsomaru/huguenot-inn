from __future__ import annotations

from .models import PartySide, ProceedingType

ORDINAL_WORDS = {
    1: "1st",
    2: "2nd",
    3: "3rd",
}


def ordinal(number: int) -> str:
    return ORDINAL_WORDS.get(number, f"{number}th")


def party_role(proceeding_type: ProceedingType, side: PartySide) -> str:
    if proceeding_type == ProceedingType.ACTION:
        return "Plaintiff" if side == PartySide.BRINGING else "Defendant"
    return "Applicant" if side == PartySide.BRINGING else "Respondent"


def party_label(proceeding_type: ProceedingType, side: PartySide, position: int, side_count: int) -> str:
    role = party_role(proceeding_type, side)
    if side_count == 1:
        return role
    return f"{ordinal(position)} {role}"
