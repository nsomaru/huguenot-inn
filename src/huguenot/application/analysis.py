from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from huguenot.documents.ir_cache import FilesystemIRCache
from huguenot.domain.document_ir import DocumentIR, IndexIR, OutputGenerationSettings
from huguenot.domain.source_documents import SourceDocument


@dataclass(frozen=True)
class AnalysisStatus:
    stage: str
    message: str
    current: int = 0
    total: int = 0


@dataclass(frozen=True)
class AnalysisResult:
    source_count: int
    index_cache_key: str


class DocumentAnalyser(Protocol):
    parser_version: str

    def analyse(self, source: SourceDocument) -> DocumentIR: ...


ProgressReporter = Callable[[AnalysisStatus], None]


class ModelManager(Protocol):
    def models_ready(self) -> bool: ...

    def ensure_models(self, progress: Callable[[Any], None]) -> None: ...


class NoOpModelManager:
    def models_ready(self) -> bool:
        return True

    def ensure_models(self, progress: Callable[[Any], None]) -> None:
        return None


class AnalysisService:
    def __init__(
        self, *, cache: FilesystemIRCache, analyser: DocumentAnalyser, model_manager: ModelManager | None = None
    ) -> None:
        self._cache = cache
        self._analyser = analyser
        self._model_manager = model_manager or NoOpModelManager()

    def analyse_sources(
        self,
        sources: Sequence[SourceDocument],
        *,
        separator_titles: Sequence[str] = (),
        matter_context: str = "",
        settings: OutputGenerationSettings | None = None,
        progress: ProgressReporter | None = None,
    ) -> AnalysisResult:
        reporter = progress or (lambda _status: None)
        self._model_manager.ensure_models(lambda status: reporter(_analysis_status_from_model_status(status)))
        total = len(sources)
        reporter(AnalysisStatus("queued", "Queued Docling analysis", 0, total))
        analysed: list[DocumentIR] = []
        for index, source in enumerate(sources, start=1):
            reporter(AnalysisStatus("analysing", f"Analysing {source.path.name}", index, total))
            analysed.append(self._analyser.analyse(source))

        reporter(AnalysisStatus("caching", "Saving IR cache", total, total))
        for ir in analysed:
            self._cache.save_source_ir(ir)
        key = self._cache.index_key(
            tuple(ir.identity for ir in analysed),
            separator_titles=tuple(separator_titles),
            matter_context=matter_context,
            settings=settings or OutputGenerationSettings(),
            parser_version=self._analyser.parser_version,
        )
        rows_json = json.dumps(
            [{"path": ir.identity.path, "title": ir.title, "page_count": ir.page_count} for ir in analysed],
            sort_keys=True,
        )
        self._cache.save_index_ir(IndexIR(cache_key=key, rows_json=rows_json))
        reporter(AnalysisStatus("complete", "Analysis complete", total, total))
        return AnalysisResult(source_count=total, index_cache_key=key)


def _analysis_status_from_model_status(status: Any) -> AnalysisStatus:
    return AnalysisStatus(
        stage=str(getattr(status, "stage", "models-downloading")),
        message=str(getattr(status, "message", "Preparing Docling models")),
        current=int(getattr(status, "current", 0) or 0),
        total=int(getattr(status, "total", 0) or 0),
    )
