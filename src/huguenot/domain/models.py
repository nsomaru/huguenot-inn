from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class PDFItem:
    path: Path
    title: str


@dataclass(frozen=True)
class IndexSeparator:
    title: str


class ProceedingType(StrEnum):
    ACTION = "Action"
    APPLICATION = "Application"


class PartySide(StrEnum):
    BRINGING = "bringing"
    OPPOSING = "opposing"


class BundleOutputMode(StrEnum):
    COMBINED_WITH_INDEX = "combined_with_index"
    SEPARATE_DOCX_AND_PDF = "separate_docx_and_pdf"
    PDF_ONLY = "pdf_only"


@dataclass(frozen=True)
class Court:
    name: str
    header_line_2: str | None = None
    id: int | None = None
    source: str | None = None


@dataclass(frozen=True)
class Party:
    name: str
    side: PartySide
    position: int
    id: int | None = None


@dataclass(frozen=True)
class Matter:
    court: Court
    proceeding_type: ProceedingType
    parties: tuple[Party, ...]
    case_number: str = ""
    id: int | None = None

    @property
    def bringing_parties(self) -> tuple[Party, ...]:
        return tuple(p for p in self.parties if p.side == PartySide.BRINGING)

    @property
    def opposing_parties(self) -> tuple[Party, ...]:
        return tuple(p for p in self.parties if p.side == PartySide.OPPOSING)

    @property
    def display_name(self) -> str:
        first = self.bringing_parties[0].name if self.bringing_parties else "Matter"
        second = self.opposing_parties[0].name if self.opposing_parties else ""
        case = f" ({self.case_number})" if self.case_number else ""
        if second:
            return f"{first} v {second}{case}"
        return f"{first}{case}"


@dataclass(frozen=True)
class DocumentHeaderInput:
    title: str


@dataclass(frozen=True)
class PageRange:
    start: int
    end: int

    def display(self) -> str:
        return str(self.start) if self.start == self.end else f"{self.start}-{self.end}"


@dataclass(frozen=True)
class IndexLinkTarget:
    item_number: int
    page_range: PageRange
    target_page: int
