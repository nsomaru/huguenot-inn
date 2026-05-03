from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .document_ir import SourceType, compute_file_checksum


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    source_type: SourceType
    checksum: str
    display_title: str
    resolved_pdf_path: Path | None = None

    @classmethod
    def from_path(cls, path: Path, *, display_title: str | None = None) -> SourceDocument:
        return cls(
            path=path,
            source_type=SourceType.from_path(path),
            checksum=compute_file_checksum(path),
            display_title=display_title if display_title is not None else _clean_source_title(path),
        )


def _clean_source_title(path: Path) -> str:
    title = path.stem.replace("_", " ")
    return " ".join(title.split()).strip() or path.name


SUPPORTED_SOURCE_SUFFIXES = frozenset({".pdf", ".docx", ".rtf"})


def is_supported_source(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_SOURCE_SUFFIXES
