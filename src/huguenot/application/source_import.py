from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from huguenot.application.duplicates import DuplicateDecision, DuplicatePDF, normalize_citation_key
from huguenot.domain import PDFItem
from huguenot.domain.source_documents import SourceDocument, SourceType, is_supported_source


class SourcePdfConverter(Protocol):
    def converter_available(self) -> bool: ...
    def convert_to_pdf(self, source_path: Path, output_dir: Path) -> Path: ...


@dataclass(frozen=True)
class SourceAdditionResult:
    added_sources: list[SourceDocument]
    added_pdf_items: list[PDFItem]
    duplicates: list[DuplicatePDF]
    skipped_duplicates: list[DuplicatePDF]
    skipped_existing_paths: list[Path]
    unsupported_paths: list[Path]


class SourceImportService:
    def __init__(self, *, converter: SourcePdfConverter, converted_pdf_dir: Path) -> None:
        self._converter = converter
        self._converted_pdf_dir = converted_pdf_dir

    def as_pdf_item(self, source: SourceDocument) -> PDFItem:
        if source.source_type is SourceType.PDF:
            return PDFItem(source.path, source.display_title)
        pdf_path = self._converter.convert_to_pdf(source.path, self._converted_pdf_dir)
        return PDFItem(pdf_path, source.display_title)


def plan_source_additions(
    existing_items: list[PDFItem],
    paths: list[Path],
    *,
    detect_title: Callable[[Path], str],
    decide_duplicate: Callable[[DuplicatePDF, int], DuplicateDecision],
) -> SourceAdditionResult:
    existing_paths = {item.path.resolve() for item in existing_items}
    known_titles: dict[str, PDFItem] = {
        normalize_citation_key(item.title): item for item in existing_items if normalize_citation_key(item.title)
    }
    added_sources: list[SourceDocument] = []
    duplicates: list[DuplicatePDF] = []
    skipped_duplicates: list[DuplicatePDF] = []
    skipped_existing_paths: list[Path] = []
    unsupported_paths: list[Path] = []
    skip_all = False

    pending: list[SourceDocument | DuplicatePDF] = []
    for path in paths:
        if not is_supported_source(path):
            unsupported_paths.append(path)
            continue
        resolved = path.resolve()
        if resolved in existing_paths:
            skipped_existing_paths.append(resolved)
            continue
        title = detect_title(path)
        source = SourceDocument.from_path(path, display_title=title)
        item = PDFItem(path=path, title=title)
        key = normalize_citation_key(title)
        duplicate_of = known_titles.get(key) if key else None
        if duplicate_of is None:
            pending.append(source)
            known_titles[key] = item
            existing_paths.add(resolved)
            continue
        duplicate = DuplicatePDF(
            path=path,
            title=title,
            duplicate_title=duplicate_of.title,
            duplicate_path=duplicate_of.path,
        )
        duplicates.append(duplicate)
        pending.append(duplicate)
        existing_paths.add(resolved)

    remaining_duplicates = len(duplicates)
    for entry in pending:
        if isinstance(entry, SourceDocument):
            added_sources.append(entry)
            continue
        remaining_duplicates -= 1
        if skip_all:
            skipped_duplicates.append(entry)
            continue
        decision = decide_duplicate(entry, remaining_duplicates + 1)
        if decision is DuplicateDecision.ADD_ANYWAY:
            added_sources.append(SourceDocument.from_path(entry.path, display_title=entry.title))
        elif decision is DuplicateDecision.SKIP_ALL:
            skipped_duplicates.append(entry)
            skip_all = True
        else:
            skipped_duplicates.append(entry)

    return SourceAdditionResult(
        added_sources=added_sources,
        added_pdf_items=[PDFItem(source.path, source.display_title) for source in added_sources],
        duplicates=duplicates,
        skipped_duplicates=skipped_duplicates,
        skipped_existing_paths=skipped_existing_paths,
        unsupported_paths=unsupported_paths,
    )
