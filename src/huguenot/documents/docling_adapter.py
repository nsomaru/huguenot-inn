from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, cast

from huguenot.domain.document_ir import DocumentIR, DocumentIRIdentity, DocumentTextItem, PageIR, SourceType
from huguenot.domain.source_documents import SourceDocument


class DoclingAnalysisError(RuntimeError):
    """Raised when Docling cannot analyse a source with a user-safe explanation."""


class DoclingAnalyser:
    parser_version = "docling-2.92"

    def __init__(self, converter: Any | None = None, *, model_artifacts_path: Path | None = None) -> None:
        self._converter = converter
        self._model_artifacts_path = model_artifacts_path

    def analyse(self, source: SourceDocument) -> DocumentIR:
        converter = self._converter or _default_converter(source.source_type, artifacts_path=self._model_artifacts_path)
        result = _convert_with_pdf_repair_retry(converter, source)
        document = result.document
        pages = _extract_pages(result, document)
        text_items = _extract_text_items(document)
        title = text_items[0].text if text_items else source.display_title
        return DocumentIR(
            identity=DocumentIRIdentity.from_path(
                source.path,
                source_type=source.source_type,
                parser_version=self.parser_version,
            ),
            pages=pages,
            text_items=text_items,
            title=title,
        )


def _default_converter(source_type: SourceType, *, artifacts_path: Path | None = None) -> Any:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    formats = [InputFormat.PDF, InputFormat.DOCX]
    if source_type is SourceType.RTF:
        formats = [InputFormat.PDF, InputFormat.DOCX]
    format_options: dict[Any, Any] | None = None
    if artifacts_path is not None:
        pipeline_options = PdfPipelineOptions(artifacts_path=artifacts_path)
        format_options = {InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    return DocumentConverter(allowed_formats=formats, format_options=format_options)


def _convert_with_pdf_repair_retry(converter: Any, source: SourceDocument) -> Any:
    try:
        return converter.convert(source.path)
    except Exception as exc:
        if source.source_type is not SourceType.PDF or not _is_invalid_docling_input_error(exc):
            raise
        if openability_error := _pdf_openability_error(source.path):
            raise DoclingAnalysisError(
                f"{source.path} could not be opened as a valid PDF. "
                "Please replace or re-save the source document and try AI Analyse again. "
                f"Details: {openability_error}"
            ) from exc
        with tempfile.TemporaryDirectory(prefix="huguenot-docling-") as temp_dir:
            normalised_path = Path(temp_dir) / source.path.name
            try:
                _normalise_pdf(source.path, normalised_path)
            except Exception as normalise_exc:
                raise DoclingAnalysisError(
                    f"Docling could not process {source.path}. Huguenot could open the PDF, "
                    f"but repairing it for analysis failed: {normalise_exc}"
                ) from normalise_exc
            try:
                return converter.convert(normalised_path)
            except Exception as retry_exc:
                raise DoclingAnalysisError(
                    f"Docling could not process {source.path}. Huguenot could open the PDF and tried a repaired copy, "
                    "but Docling still rejected it. Please try re-saving or re-exporting the PDF. "
                    "If this happens for every valid PDF, it can indicate a Docling runtime or packaged-app problem."
                ) from retry_exc


def _is_invalid_docling_input_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "input document" in message and "not valid" in message


def _pdf_openability_error(source_path: Path) -> str | None:
    import fitz

    try:
        document = fitz.open(source_path)
    except Exception as exc:
        return str(exc) or exc.__class__.__name__
    try:
        if getattr(document, "is_encrypted", False):
            return "the PDF is encrypted"
        page_count = int(getattr(document, "page_count", 0) or 0)
        if page_count < 1:
            return "the PDF contains no pages"
    finally:
        document.close()
    return None


def _normalise_pdf(source_path: Path, output_path: Path) -> None:
    import fitz

    document = fitz.open(source_path)
    try:
        document.save(output_path, garbage=4, deflate=True, clean=True)
    finally:
        document.close()


def _extract_pages(result: Any, document: Any) -> tuple[PageIR, ...]:
    pages: list[PageIR] = []
    for index, page in enumerate(getattr(result, "pages", []) or [], start=1):
        size = getattr(page, "size", None)
        width = getattr(size, "width", None)
        height = getattr(size, "height", None)
        page_no = getattr(page, "page_no", index) or index
        pages.append(PageIR(number=int(page_no), width=_float_or_none(width), height=_float_or_none(height)))
    if pages:
        return tuple(pages)
    doc_pages = getattr(document, "pages", None)
    if isinstance(doc_pages, dict) and doc_pages:
        return tuple(PageIR(number=int(number)) for number in sorted(doc_pages))
    return (PageIR(number=1),)


def _extract_text_items(document: Any) -> tuple[DocumentTextItem, ...]:
    items: list[DocumentTextItem] = []
    iterator = getattr(document, "iterate_items", None)
    if not callable(iterator):
        text = _export_text(document)
        return (DocumentTextItem(text=text, page_number=1, label="TEXT"),) if text else ()
    for raw in cast(Any, iterator)():
        item = raw[0] if isinstance(raw, tuple) else raw
        text = getattr(item, "text", None)
        if not isinstance(text, str) or not text.strip():
            continue
        label = getattr(getattr(item, "label", None), "name", getattr(item, "label", None))
        page_number, bbox = _provenance(item)
        items.append(
            DocumentTextItem(
                text=" ".join(text.split()), page_number=page_number, label=str(label) if label else None, bbox=bbox
            )
        )
    return tuple(items)


def _provenance(item: Any) -> tuple[int, tuple[float, float, float, float] | None]:
    prov = getattr(item, "prov", None) or []
    first = prov[0] if prov else None
    if first is None:
        return 1, None
    page_no = int(getattr(first, "page_no", 1) or 1)
    bbox = getattr(first, "bbox", None)
    if bbox is None:
        return page_no, None
    left = _float_or_none(getattr(bbox, "l", None))
    top = _float_or_none(getattr(bbox, "t", None))
    right = _float_or_none(getattr(bbox, "r", None))
    bottom = _float_or_none(getattr(bbox, "b", None))
    if None in {left, top, right, bottom}:
        return page_no, None
    return page_no, (left, top, right, bottom)  # type: ignore[return-value]


def _export_text(document: Any) -> str:
    export = getattr(document, "export_to_text", None)
    if callable(export):
        text = export()
        return text if isinstance(text, str) else ""
    return ""


def _float_or_none(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
