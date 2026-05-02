import pytest

from huguenot.domain import (
    BundleOutputMode,
    Court,
    IndexLinkTarget,
    Matter,
    MatterValidationError,
    PageRange,
    Party,
    PartySide,
    ProceedingType,
    validate_matter,
)


def test_matter_requires_court_and_parties() -> None:
    matter = Matter(
        court=Court(name=""),
        proceeding_type=ProceedingType.APPLICATION,
        parties=(
            Party("Applicant", PartySide.BRINGING, 1),
            Party("Respondent", PartySide.OPPOSING, 1),
        ),
    )
    with pytest.raises(MatterValidationError, match="Court name"):
        validate_matter(matter)


def test_matter_requires_parties_on_both_sides() -> None:
    matter = Matter(
        court=Court(name="IN THE HIGH COURT OF SOUTH AFRICA"),
        proceeding_type=ProceedingType.ACTION,
        parties=(Party("Plaintiff", PartySide.BRINGING, 1),),
    )
    with pytest.raises(MatterValidationError, match="opposing party"):
        validate_matter(matter)


def test_matter_display_name_uses_first_parties_and_case_number() -> None:
    matter = Matter(
        court=Court(name="IN THE HIGH COURT OF SOUTH AFRICA"),
        proceeding_type=ProceedingType.ACTION,
        case_number="123/2026",
        parties=(
            Party("Alpha Ltd", PartySide.BRINGING, 1),
            Party("Beta Ltd", PartySide.OPPOSING, 1),
        ),
    )
    assert matter.display_name == "Alpha Ltd v Beta Ltd (123/2026)"


def test_output_mode_and_index_link_value_objects() -> None:
    target = IndexLinkTarget(item_number=1, page_range=PageRange(2, 3), target_page=1)

    assert BundleOutputMode.COMBINED_WITH_INDEX.value == "combined_with_index"
    assert target.page_range.display() == "2-3"
