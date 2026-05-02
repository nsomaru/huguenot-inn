from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from huguenot.domain import PDFItem


class DuplicateDecision(StrEnum):
    ADD_ANYWAY = "add_anyway"
    SKIP = "skip"
    SKIP_ALL = "skip_all"


@dataclass(frozen=True)
class DuplicatePDF:
    path: Path
    title: str
    duplicate_title: str
    duplicate_path: Path


@dataclass(frozen=True)
class PDFAdditionResult:
    added: list[PDFItem]
    duplicates: list[DuplicatePDF]
    skipped_duplicates: list[DuplicatePDF]
    skipped_existing_paths: list[Path]


def normalize_citation_key(title: str) -> str:
    return " ".join(title.casefold().split())


def plan_pdf_additions(
    existing_items: list[PDFItem],
    paths: list[Path],
    *,
    detect_title: Callable[[Path], str],
    decide_duplicate: Callable[[DuplicatePDF, int], DuplicateDecision],
) -> PDFAdditionResult:
    existing_paths = {item.path.resolve() for item in existing_items}
    known_titles: dict[str, PDFItem] = {
        normalize_citation_key(item.title): item for item in existing_items if normalize_citation_key(item.title)
    }
    added: list[PDFItem] = []
    duplicates: list[DuplicatePDF] = []
    skipped_duplicates: list[DuplicatePDF] = []
    skipped_existing_paths: list[Path] = []
    skip_all = False

    pending: list[PDFItem | DuplicatePDF] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in existing_paths:
            skipped_existing_paths.append(resolved)
            continue
        title = detect_title(path)
        item = PDFItem(path=path, title=title)
        key = normalize_citation_key(title)
        duplicate_of = known_titles.get(key) if key else None
        if duplicate_of is None:
            pending.append(item)
            known_titles[key] = item
            existing_paths.add(resolved)
            continue
        duplicate = DuplicatePDF(
            path=path, title=title, duplicate_title=duplicate_of.title, duplicate_path=duplicate_of.path
        )
        duplicates.append(duplicate)
        pending.append(duplicate)
        existing_paths.add(resolved)

    remaining_duplicates = len(duplicates)
    for entry in pending:
        if isinstance(entry, PDFItem):
            added.append(entry)
            continue
        remaining_duplicates -= 1
        if skip_all:
            skipped_duplicates.append(entry)
            continue
        decision = decide_duplicate(entry, remaining_duplicates + 1)
        if decision is DuplicateDecision.ADD_ANYWAY:
            added.append(PDFItem(path=entry.path, title=entry.title))
        elif decision is DuplicateDecision.SKIP_ALL:
            skipped_duplicates.append(entry)
            skip_all = True
        else:
            skipped_duplicates.append(entry)

    return PDFAdditionResult(
        added=added,
        duplicates=duplicates,
        skipped_duplicates=skipped_duplicates,
        skipped_existing_paths=skipped_existing_paths,
    )
