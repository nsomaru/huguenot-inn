from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class SourceType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    RTF = "rtf"

    @classmethod
    def from_path(cls, path: Path) -> SourceType:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return cls.PDF
        if suffix == ".docx":
            return cls.DOCX
        if suffix == ".rtf":
            return cls.RTF
        raise ValueError(f"Unsupported source document type: {path.suffix or path.name}")


@dataclass(frozen=True)
class DocumentIRIdentity:
    path: str
    checksum: str
    source_type: SourceType
    parser_version: str = "legacy"

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        source_type: SourceType | None = None,
        parser_version: str = "legacy",
    ) -> DocumentIRIdentity:
        return cls(
            path=str(path),
            checksum=compute_file_checksum(path),
            source_type=source_type or SourceType.from_path(path),
            parser_version=parser_version,
        )

    @property
    def path_as_path(self) -> Path:
        return Path(self.path)


@dataclass(frozen=True)
class PageIR:
    number: int
    width: float | None = None
    height: float | None = None


@dataclass(frozen=True)
class DocumentTextItem:
    text: str
    page_number: int
    label: str | None = None
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class DocumentIR:
    identity: DocumentIRIdentity
    pages: tuple[PageIR, ...]
    text_items: tuple[DocumentTextItem, ...]
    title: str | None = None

    @property
    def page_count(self) -> int:
        return max((page.number for page in self.pages), default=1)


@dataclass(frozen=True)
class OutputGenerationSettings:
    header_title: str = ""
    index_font: str = "Times New Roman"
    colour_page_ranges: bool = False
    flag_colours: tuple[str, ...] = ()
    physical_flag_markers: bool = True
    renderer_preference: str = "reportlab"


@dataclass(frozen=True)
class IndexIR:
    cache_key: str
    rows_json: str
    schema_version: str = "1"


JsonDict = dict[str, Any]


def compute_file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def document_ir_to_json(ir: DocumentIR) -> str:
    return json.dumps(_to_jsonable(asdict(ir)), sort_keys=True, separators=(",", ":"))


def document_ir_from_json(payload: str) -> DocumentIR:
    data = json.loads(payload)
    identity_data = data["identity"]
    pages = tuple(PageIR(**page) for page in data.get("pages", []))
    text_items = tuple(
        DocumentTextItem(
            text=item["text"],
            page_number=item["page_number"],
            label=item.get("label"),
            bbox=tuple(item["bbox"]) if item.get("bbox") is not None else None,
        )
        for item in data.get("text_items", [])
    )
    return DocumentIR(
        identity=DocumentIRIdentity(
            path=identity_data["path"],
            checksum=identity_data["checksum"],
            source_type=SourceType(identity_data["source_type"]),
            parser_version=identity_data.get("parser_version", "legacy"),
        ),
        pages=pages,
        text_items=text_items,
        title=data.get("title"),
    )


def index_ir_to_json(ir: IndexIR) -> str:
    return json.dumps(asdict(ir), sort_keys=True, separators=(",", ":"))


def index_ir_from_json(payload: str) -> IndexIR:
    data = json.loads(payload)
    return IndexIR(
        cache_key=data["cache_key"], rows_json=data["rows_json"], schema_version=data.get("schema_version", "1")
    )


def settings_identity(settings: OutputGenerationSettings) -> JsonDict:
    return _to_jsonable(asdict(settings))


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value
