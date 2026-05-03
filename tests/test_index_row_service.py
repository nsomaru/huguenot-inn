from pathlib import Path

from huguenot.application.index_rows import IndexRowService, MissingIRDecision, RowSource
from huguenot.documents.ir_cache import FilesystemIRCache
from huguenot.domain import BundleIndexEntry, IndexSeparator, IndexSeparatorEntry, PDFItem
from huguenot.domain.document_ir import (
    DocumentIR,
    DocumentIRIdentity,
    IndexIR,
    OutputGenerationSettings,
    PageIR,
    SourceType,
)


def make_ir(path: Path, *, title: str, pages: int) -> DocumentIR:
    return DocumentIR(
        identity=DocumentIRIdentity.from_path(path, source_type=SourceType.PDF),
        pages=tuple(PageIR(number=index, width=600, height=800) for index in range(1, pages + 1)),
        text_items=(),
        title=title,
    )


def test_complete_ir_cache_selects_ir_derived_rows(tmp_path: Path) -> None:
    pdf = tmp_path / "authority.pdf"
    pdf.write_bytes(b"pdf")
    item = PDFItem(pdf, "Legacy Title")
    cache = FilesystemIRCache(tmp_path / "cache")
    cache.save_source_ir(make_ir(pdf, title="Legacy Title", pages=3))
    settings = OutputGenerationSettings()
    key = cache.index_key((DocumentIRIdentity.from_path(pdf, source_type=SourceType.PDF),), settings=settings)
    cache.save_index_ir(IndexIR(key, "[]"))
    service = IndexRowService(cache=cache, legacy_row_builder=lambda *_args, **_kwargs: [])

    result = service.build_rows([IndexSeparator("Cases"), item], settings=settings)

    assert result.source is RowSource.IR
    assert result.rows[0] == IndexSeparatorEntry("Cases")
    assert isinstance(result.rows[1], BundleIndexEntry)
    assert result.rows[1].page_range.display() == "1-3"


def test_index_ir_cache_match_includes_separator_and_matter_context(tmp_path: Path) -> None:
    pdf = tmp_path / "authority.pdf"
    pdf.write_bytes(b"pdf")
    item = PDFItem(pdf, "Authority")
    cache = FilesystemIRCache(tmp_path / "cache")
    identity = DocumentIRIdentity.from_path(pdf, source_type=SourceType.PDF)
    cache.save_source_ir(make_ir(pdf, title="Authority", pages=1))
    settings = OutputGenerationSettings(header_title="AUTHORITIES BUNDLE")
    key = cache.index_key(
        (identity,),
        separator_titles=("Cases",),
        matter_context="A v B",
        settings=settings,
    )
    cache.save_index_ir(IndexIR(key, "[]"))
    service = IndexRowService(cache=cache, legacy_row_builder=lambda *_args, **_kwargs: [])

    matching = service.build_rows(
        [IndexSeparator("Cases"), item],
        settings=settings,
        separator_titles=("Cases",),
        matter_context="A v B",
    )
    stale_context = service.build_rows(
        [IndexSeparator("Cases"), item],
        settings=settings,
        separator_titles=("Other",),
        matter_context="A v B",
    )

    assert matching.source is RowSource.IR
    assert stale_context.source is RowSource.LEGACY


def test_no_ir_cache_uses_legacy_rows_without_warning(tmp_path: Path) -> None:
    pdf = tmp_path / "authority.pdf"
    pdf.write_bytes(b"pdf")
    item = PDFItem(pdf, "Title")
    sentinel_rows = [object()]
    warnings: list[object] = []
    service = IndexRowService(
        cache=FilesystemIRCache(tmp_path / "cache"),
        legacy_row_builder=lambda *_args, **_kwargs: sentinel_rows,  # type: ignore[return-value]
    )

    result = service.build_rows([item], settings=OutputGenerationSettings(), on_partial_cache=warnings.append)

    assert result.source is RowSource.LEGACY
    assert result.rows == sentinel_rows
    assert warnings == []


def test_partial_ir_cache_warns_and_can_continue_legacy_or_generate_missing(tmp_path: Path) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    cache = FilesystemIRCache(tmp_path / "cache")
    cache.save_source_ir(make_ir(first, title="First", pages=1))
    generated: list[Path] = []
    service = IndexRowService(
        cache=cache,
        legacy_row_builder=lambda *_args, **_kwargs: [],
        generate_missing_ir=lambda missing: generated.extend(identity.path_as_path for identity in missing),
    )
    warnings = []

    legacy = service.build_rows(
        [PDFItem(first, "First"), PDFItem(second, "Second")],
        settings=OutputGenerationSettings(),
        on_partial_cache=warnings.append,
        missing_ir_decision=MissingIRDecision.CONTINUE_LEGACY,
    )
    generate = service.build_rows(
        [PDFItem(first, "First"), PDFItem(second, "Second")],
        settings=OutputGenerationSettings(),
        missing_ir_decision=MissingIRDecision.GENERATE_MISSING,
    )

    assert legacy.source is RowSource.LEGACY
    assert warnings and len(warnings[0].missing) == 1
    assert generated == [second]
    assert generate.source is RowSource.LEGACY


def test_ir_rows_preserve_current_edited_titles_and_flag_colours(tmp_path: Path) -> None:
    pdf = tmp_path / "authority.pdf"
    pdf.write_bytes(b"pdf")
    cache = FilesystemIRCache(tmp_path / "cache")
    cache.save_source_ir(make_ir(pdf, title="Stale Cached Title", pages=2))
    item = PDFItem(pdf, "Edited Visible Title")
    settings = OutputGenerationSettings(colour_page_ranges=True, flag_colours=("#3467A5",))
    key = cache.index_key((DocumentIRIdentity.from_path(pdf, source_type=SourceType.PDF),), settings=settings)
    cache.save_index_ir(IndexIR(key, "[]"))
    service = IndexRowService(cache=cache, legacy_row_builder=lambda *_args, **_kwargs: [])

    result = service.build_rows([item], settings=settings, flag_colours=["#3467A5"])

    assert result.source is RowSource.IR
    assert isinstance(result.rows[0], BundleIndexEntry)
    assert result.rows[0].item.title == "Edited Visible Title"
    assert result.rows[0].flag_colour == "#3467A5"


def test_complete_source_ir_without_matching_index_ir_falls_back_to_legacy(tmp_path: Path) -> None:
    pdf = tmp_path / "authority.pdf"
    pdf.write_bytes(b"pdf")
    cache = FilesystemIRCache(tmp_path / "cache")
    cache.save_source_ir(make_ir(pdf, title="Title", pages=2))
    sentinel_rows = [object()]
    service = IndexRowService(
        cache=cache,
        legacy_row_builder=lambda *_args, **_kwargs: sentinel_rows,  # type: ignore[return-value]
    )

    result = service.build_rows([PDFItem(pdf, "Title")], settings=OutputGenerationSettings())

    assert result.source is RowSource.LEGACY
    assert result.rows == sentinel_rows


def test_source_identity_provider_allows_docx_ir_after_pdf_conversion(tmp_path: Path) -> None:
    docx = tmp_path / "authority.docx"
    converted_pdf = tmp_path / "converted" / "authority.pdf"
    docx.write_bytes(b"docx")
    converted_pdf.parent.mkdir()
    converted_pdf.write_bytes(b"pdf")
    cache = FilesystemIRCache(tmp_path / "cache")
    docx_identity = DocumentIRIdentity.from_path(docx, source_type=SourceType.DOCX)
    cache.save_source_ir(
        DocumentIR(identity=docx_identity, pages=(PageIR(number=1), PageIR(number=2)), text_items=(), title="Docx IR")
    )
    settings = OutputGenerationSettings()
    key = cache.index_key((docx_identity,), settings=settings)
    cache.save_index_ir(IndexIR(key, "[]"))
    service = IndexRowService(
        cache=cache,
        legacy_row_builder=lambda *_args, **_kwargs: [],
        source_identity_provider=lambda item: docx_identity,
    )

    result = service.build_rows([PDFItem(converted_pdf, "Visible Docx Title")], settings=settings)

    assert result.source is RowSource.IR
    assert isinstance(result.rows[0], BundleIndexEntry)
    assert result.rows[0].item.title == "Visible Docx Title"
    assert result.rows[0].page_range.display() == "1-2"
