from pathlib import Path

from huguenot.application.disk_usage import DiskUsageService
from huguenot.documents.ir_cache import FilesystemIRCache
from huguenot.domain.document_ir import DocumentIR, DocumentIRIdentity, PageIR, SourceType


def test_disk_usage_reports_sqlite_and_cache_sizes_and_clears_cache_only(tmp_path: Path) -> None:
    db = tmp_path / "huguenot.sqlite3"
    db.write_bytes(b"db")
    pdf = tmp_path / "authority.pdf"
    pdf.write_bytes(b"pdf")
    cache = FilesystemIRCache(tmp_path / "cache")
    cache.save_source_ir(
        DocumentIR(
            identity=DocumentIRIdentity.from_path(pdf, source_type=SourceType.PDF),
            pages=(PageIR(number=1, width=600, height=800),),
            text_items=(),
        )
    )
    service = DiskUsageService(database_path=db, cache=cache)

    usage = service.calculate()
    cleared = service.clear_cache()

    assert usage.sqlite_bytes == 2
    assert usage.cache_bytes > 0
    assert cleared > 0
    assert db.read_bytes() == b"db"
    assert cache.cache_size_bytes() == 0
