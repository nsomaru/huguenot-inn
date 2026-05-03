from pathlib import Path

from huguenot.application.analysis import AnalysisService, AnalysisStatus
from huguenot.documents.ir_cache import FilesystemIRCache
from huguenot.domain.document_ir import DocumentIR, DocumentIRIdentity, DocumentTextItem, PageIR, SourceType
from huguenot.domain.source_documents import SourceDocument


class FakeAnalyser:
    parser_version = "fake-docling"

    def analyse(self, source: SourceDocument) -> DocumentIR:
        return DocumentIR(
            identity=DocumentIRIdentity.from_path(source.path, source_type=source.source_type),
            pages=(PageIR(number=1, width=600, height=800),),
            text_items=(DocumentTextItem(text=source.display_title, page_number=1, label="TITLE", bbox=None),),
            title=source.display_title,
        )


class FakeModelManager:
    def __init__(self) -> None:
        self.called = False

    def models_ready(self) -> bool:
        return False

    def ensure_models(self, progress) -> None:
        self.called = True
        progress(AnalysisStatus("models-checking", "Checking Docling models"))
        progress(AnalysisStatus("models-downloading", "Downloading Docling models", 1, 2))
        progress(AnalysisStatus("models-ready", "Docling models ready", 2, 2))


def test_analysis_service_writes_source_and_index_ir_with_progress(tmp_path: Path) -> None:
    source_path = tmp_path / "case.pdf"
    source_path.write_bytes(b"pdf")
    source = SourceDocument.from_path(source_path, display_title="Case Title")
    cache = FilesystemIRCache(tmp_path / "cache")
    events: list[AnalysisStatus] = []

    result = AnalysisService(cache=cache, analyser=FakeAnalyser()).analyse_sources(
        [source],
        separator_titles=("Cases",),
        matter_context="A v B",
        progress=events.append,
    )

    assert [event.stage for event in events] == ["queued", "analysing", "caching", "complete"]
    assert result.source_count == 1
    assert cache.load_source_ir(DocumentIRIdentity.from_path(source_path, source_type=SourceType.PDF)) is not None
    assert cache.load_index_ir(result.index_cache_key) is not None


def test_analysis_service_prepares_docling_models_before_document_analysis(tmp_path: Path) -> None:
    source_path = tmp_path / "case.pdf"
    source_path.write_bytes(b"pdf")
    source = SourceDocument.from_path(source_path, display_title="Case Title")
    cache = FilesystemIRCache(tmp_path / "cache")
    events: list[AnalysisStatus] = []
    model_manager = FakeModelManager()

    AnalysisService(cache=cache, analyser=FakeAnalyser(), model_manager=model_manager).analyse_sources(
        [source],
        progress=events.append,
    )

    assert model_manager.called is True
    assert [event.stage for event in events] == [
        "models-checking",
        "models-downloading",
        "models-ready",
        "queued",
        "analysing",
        "caching",
        "complete",
    ]
