from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from huguenot.documents.authorities_index import get_index_rows
from huguenot.documents.ir_cache import FilesystemIRCache
from huguenot.domain import (
    BundleIndexEntry,
    BundleIndexRow,
    BundleListItem,
    IndexSeparator,
    IndexSeparatorEntry,
    PDFItem,
)
from huguenot.domain.document_ir import DocumentIR, DocumentIRIdentity, OutputGenerationSettings, SourceType


class RowSource(StrEnum):
    LEGACY = "legacy"
    IR = "ir"


class MissingIRDecision(StrEnum):
    CONTINUE_LEGACY = "continue_legacy"
    GENERATE_MISSING = "generate_missing"


@dataclass(frozen=True)
class PartialIRCache:
    missing: tuple[DocumentIRIdentity, ...]
    available: tuple[DocumentIRIdentity, ...]


@dataclass(frozen=True)
class RowSelection:
    rows: list[BundleIndexRow]
    source: RowSource


LegacyRowBuilder = Callable[..., list[BundleIndexRow]]
GenerateMissingIR = Callable[[tuple[DocumentIRIdentity, ...]], None]
PartialCacheWarning = Callable[[PartialIRCache], None]
SourceIdentityProvider = Callable[[PDFItem], DocumentIRIdentity]


class IndexRowService:
    def __init__(
        self,
        *,
        cache: FilesystemIRCache,
        legacy_row_builder: LegacyRowBuilder = get_index_rows,
        generate_missing_ir: GenerateMissingIR | None = None,
        source_identity_provider: SourceIdentityProvider | None = None,
    ) -> None:
        self._cache = cache
        self._legacy_row_builder = legacy_row_builder
        self._generate_missing_ir = generate_missing_ir
        self._source_identity_provider = source_identity_provider or _default_source_identity

    def build_rows(
        self,
        bundle_items: Sequence[BundleListItem],
        *,
        settings: OutputGenerationSettings,
        start_page: int = 1,
        separator_titles: Sequence[str] = (),
        matter_context: str = "",
        flag_colours: Sequence[str] | None = None,
        on_partial_cache: PartialCacheWarning | None = None,
        missing_ir_decision: MissingIRDecision = MissingIRDecision.CONTINUE_LEGACY,
    ) -> RowSelection:
        pdf_items = [item for item in bundle_items if isinstance(item, PDFItem)]
        if not pdf_items:
            return RowSelection(
                self._legacy_rows(bundle_items, start_page=start_page, flag_colours=flag_colours), RowSource.LEGACY
            )

        identities = tuple(self._source_identity_provider(item) for item in pdf_items)
        loaded = [self._cache.load_source_ir(identity) for identity in identities]
        if all(ir is None for ir in loaded):
            return RowSelection(
                self._legacy_rows(bundle_items, start_page=start_page, flag_colours=flag_colours), RowSource.LEGACY
            )
        if any(ir is None for ir in loaded):
            missing = tuple(identity for identity, ir in zip(identities, loaded, strict=True) if ir is None)
            available = tuple(identity for identity, ir in zip(identities, loaded, strict=True) if ir is not None)
            if on_partial_cache is not None:
                on_partial_cache(PartialIRCache(missing=missing, available=available))
            if missing_ir_decision is MissingIRDecision.GENERATE_MISSING and self._generate_missing_ir is not None:
                self._generate_missing_ir(missing)
            return RowSelection(
                self._legacy_rows(bundle_items, start_page=start_page, flag_colours=flag_colours), RowSource.LEGACY
            )

        index_key = self._cache.index_key(
            identities,
            separator_titles=tuple(separator_titles),
            matter_context=matter_context,
            settings=settings,
        )
        if self._cache.load_index_ir(index_key) is None:
            return RowSelection(
                self._legacy_rows(bundle_items, start_page=start_page, flag_colours=flag_colours), RowSource.LEGACY
            )

        rows = _rows_from_ir(
            bundle_items,
            {identity.path: ir for identity, ir in zip(identities, loaded, strict=True) if ir is not None},
            identities_by_pdf_path={
                str(item.path): identity for item, identity in zip(pdf_items, identities, strict=True)
            },
            start_page=start_page,
            flag_colours=flag_colours,
        )
        return RowSelection(rows, RowSource.IR)

    def _legacy_rows(
        self,
        bundle_items: Sequence[BundleListItem],
        *,
        start_page: int,
        flag_colours: Sequence[str] | None,
    ) -> list[BundleIndexRow]:
        return self._legacy_row_builder(bundle_items, start_page=start_page, flag_colours=flag_colours)


def _rows_from_ir(
    bundle_items: Sequence[BundleListItem],
    ir_by_path: dict[str, DocumentIR],
    *,
    identities_by_pdf_path: dict[str, DocumentIRIdentity],
    start_page: int,
    flag_colours: Sequence[str] | None,
) -> list[BundleIndexRow]:
    rows: list[BundleIndexRow] = []
    current_page = start_page
    real_index = 0
    for item in bundle_items:
        if isinstance(item, IndexSeparator):
            rows.append(IndexSeparatorEntry(item.title))
            continue
        identity = identities_by_pdf_path[str(item.path)]
        ir = ir_by_path[identity.path]
        page_count = max(1, ir.page_count)
        flag_colour = None if flag_colours is None else flag_colours[real_index % len(flag_colours)]
        rows.append(
            BundleIndexEntry(
                real_index + 1,
                item,
                page_range=_page_range(current_page, page_count),
                flag_colour=flag_colour,
            )
        )
        current_page += page_count
        real_index += 1
    return rows


def _page_range(start: int, page_count: int):
    from huguenot.domain import PageRange

    return PageRange(start, start + page_count - 1)


def _default_source_identity(item: PDFItem) -> DocumentIRIdentity:
    return DocumentIRIdentity.from_path(item.path, source_type=SourceType.PDF)
