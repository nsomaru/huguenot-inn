from pathlib import Path

from huguenot.application.duplicates import DuplicateDecision, plan_pdf_additions
from huguenot.domain import PDFItem


def test_plan_pdf_additions_skips_existing_paths_before_duplicate_citation(tmp_path: Path) -> None:
    existing_path = tmp_path / "existing.pdf"
    existing_path.write_bytes(b"pdf")

    result = plan_pdf_additions(
        [PDFItem(existing_path, "S v Makwanyane [1995] ZACC 3")],
        [existing_path],
        detect_title=lambda path: "S v Makwanyane [1995] ZACC 3",
        decide_duplicate=lambda _duplicate, _remaining: DuplicateDecision.ADD_ANYWAY,
    )

    assert result.added == []
    assert result.skipped_existing_paths == [existing_path.resolve()]
    assert result.duplicates == []


def test_plan_pdf_additions_handles_add_skip_and_skip_all(tmp_path: Path) -> None:
    existing_path = tmp_path / "existing.pdf"
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    third = tmp_path / "third.pdf"
    for path in (existing_path, first, second, third):
        path.write_bytes(b"pdf")

    decisions = iter([DuplicateDecision.ADD_ANYWAY, DuplicateDecision.SKIP_ALL])
    result = plan_pdf_additions(
        [PDFItem(existing_path, "S v Makwanyane [1995] ZACC 3")],
        [first, second, third],
        detect_title=lambda _path: " S   v Makwanyane [1995] ZACC 3 ",
        decide_duplicate=lambda _duplicate, _remaining: next(decisions),
    )

    assert [item.path for item in result.added] == [first]
    assert len(result.duplicates) == 3
    assert [duplicate.path for duplicate in result.skipped_duplicates] == [second, third]


def test_duplicate_modal_labels_match_prd() -> None:
    from huguenot.ui.app import (
        DUPLICATE_ADD_ANYWAY_LABEL,
        DUPLICATE_SKIP_ALL_LABEL_TEMPLATE,
        DUPLICATE_SKIP_LABEL,
    )

    assert DUPLICATE_ADD_ANYWAY_LABEL == "Add Anyway"
    assert DUPLICATE_SKIP_LABEL == "Skip"
    assert DUPLICATE_SKIP_ALL_LABEL_TEMPLATE.format(count=3) == "Skip all 3 duplicates"
