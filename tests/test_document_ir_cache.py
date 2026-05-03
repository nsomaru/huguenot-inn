from pathlib import Path

from huguenot.documents.ir_cache import FilesystemIRCache, document_checksum
from huguenot.domain.document_ir import (
    DocumentIR,
    DocumentIRIdentity,
    DocumentTextItem,
    IndexIR,
    OutputGenerationSettings,
    PageIR,
    SourceType,
)


def make_ir(path: Path, *, source_type: SourceType = SourceType.PDF, title: str = "Authority") -> DocumentIR:
    identity = DocumentIRIdentity.from_path(path, source_type=source_type)
    return DocumentIR(
        identity=identity,
        pages=(PageIR(number=1, width=600, height=800),),
        text_items=(DocumentTextItem(text=title, page_number=1, label="TITLE", bbox=(40, 40, 560, 80)),),
        title=title,
    )


def test_source_ir_cache_reuses_unchanged_checksum_and_rejects_changed_file(tmp_path: Path) -> None:
    source = tmp_path / "authority.pdf"
    source.write_bytes(b"first")
    cache = FilesystemIRCache(tmp_path / "cache")
    ir = make_ir(source)

    cache.save_source_ir(ir)

    assert cache.load_source_ir(DocumentIRIdentity.from_path(source, source_type=SourceType.PDF)) == ir
    source.write_bytes(b"changed")
    assert cache.load_source_ir(DocumentIRIdentity.from_path(source, source_type=SourceType.PDF)) is None


def test_source_ir_cache_corrupt_artifact_falls_back_to_miss(tmp_path: Path) -> None:
    source = tmp_path / "authority.pdf"
    source.write_bytes(b"pdf")
    cache = FilesystemIRCache(tmp_path / "cache")
    identity = DocumentIRIdentity.from_path(source, source_type=SourceType.PDF)
    cache.source_ir_path(identity).parent.mkdir(parents=True)
    cache.source_ir_path(identity).write_bytes(b"not parquet")

    assert cache.load_source_ir(identity) is None


def test_index_ir_cache_identity_includes_order_matter_and_output_settings(tmp_path: Path) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    cache = FilesystemIRCache(tmp_path / "cache")
    first_identity = DocumentIRIdentity.from_path(first, source_type=SourceType.PDF)
    second_identity = DocumentIRIdentity.from_path(second, source_type=SourceType.PDF)
    settings = OutputGenerationSettings(header_title="AUTHORITIES BUNDLE", index_font="Times New Roman")
    key = cache.index_key(
        (first_identity, second_identity),
        separator_titles=("Cases",),
        matter_context="A v B",
        settings=settings,
    )
    index_ir = IndexIR(cache_key=key, rows_json="[]")

    cache.save_index_ir(index_ir)

    assert cache.load_index_ir(key) == index_ir
    assert (
        cache.load_index_ir(
            cache.index_key(
                (second_identity, first_identity),
                separator_titles=("Cases",),
                matter_context="A v B",
                settings=settings,
            )
        )
        is None
    )
    assert (
        cache.load_index_ir(
            cache.index_key(
                (first_identity, second_identity),
                separator_titles=("Other",),
                matter_context="A v B",
                settings=settings,
            )
        )
        is None
    )
    assert (
        cache.load_index_ir(
            cache.index_key(
                (first_identity, second_identity),
                separator_titles=("Cases",),
                matter_context="Different",
                settings=settings,
            )
        )
        is None
    )
    assert (
        cache.load_index_ir(
            cache.index_key(
                (first_identity, second_identity),
                separator_titles=("Cases",),
                matter_context="A v B",
                settings=OutputGenerationSettings(header_title="AUTHORITIES BUNDLE", index_font="Arial"),
            )
        )
        is None
    )


def test_clear_cache_deletes_only_parquet_cache_artifacts(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache = FilesystemIRCache(cache_root)
    db = tmp_path / "huguenot.sqlite3"
    db.write_bytes(b"db")
    source = tmp_path / "authority.pdf"
    source.write_bytes(b"pdf")
    cache.save_source_ir(make_ir(source))
    notes = cache_root / "notes.txt"
    notes.write_text("keep")

    before = cache.cache_size_bytes()
    removed = cache.clear_cache()

    assert before > 0
    assert removed > 0
    assert db.read_bytes() == b"db"
    assert notes.read_text() == "keep"
    assert not list(cache_root.rglob("*.parquet"))


def test_document_checksum_is_content_based(tmp_path: Path) -> None:
    one = tmp_path / "one.pdf"
    two = tmp_path / "two.pdf"
    one.write_bytes(b"same")
    two.write_bytes(b"same")

    assert document_checksum(one) == document_checksum(two)
