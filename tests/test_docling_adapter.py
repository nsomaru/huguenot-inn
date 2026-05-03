from pathlib import Path

import fitz
import pytest

from huguenot.documents.docling_adapter import DoclingAnalyser, DoclingAnalysisError
from huguenot.domain.source_documents import SourceDocument


class FakeConversionResult:
    document = object()
    pages = []


class RejectOriginalPdfConverter:
    def __init__(self, original: Path) -> None:
        self.original = original
        self.paths: list[Path] = []

    def convert(self, path: Path) -> FakeConversionResult:
        self.paths.append(path)
        if path == self.original:
            raise ValueError(f"Input document {path} is not valid.")
        return FakeConversionResult()


class RejectEveryPdfConverter:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def convert(self, path: Path) -> FakeConversionResult:
        self.paths.append(path)
        raise ValueError(f"Input document {path} is not valid.")


def test_docling_analyser_retries_invalid_pdf_with_normalised_copy(tmp_path: Path) -> None:
    source_pdf = tmp_path / "case_1.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Automotive Tooling Systems (Pty) Ltd v Wilkens and Others")
    document.save(source_pdf)
    document.close()
    converter = RejectOriginalPdfConverter(source_pdf)

    ir = DoclingAnalyser(converter=converter).analyse(SourceDocument.from_path(source_pdf))

    assert len(converter.paths) == 2
    assert converter.paths[0] == source_pdf
    retry_path = converter.paths[1]
    assert retry_path != source_pdf
    assert retry_path.name == source_pdf.name
    assert retry_path.exists() is False
    assert ir.identity.path == str(source_pdf)
    assert ir.identity.checksum


def test_docling_analyser_does_not_retry_unrelated_conversion_failures(tmp_path: Path) -> None:
    source_pdf = tmp_path / "case.pdf"
    source_pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")

    class BrokenConverter:
        def convert(self, path: Path) -> FakeConversionResult:
            raise RuntimeError(f"Cannot read {path}")

    with pytest.raises(RuntimeError, match="Cannot read"):
        DoclingAnalyser(converter=BrokenConverter()).analyse(SourceDocument.from_path(source_pdf))


def test_docling_analyser_reports_original_pdf_when_repaired_copy_is_rejected(tmp_path: Path) -> None:
    source_pdf = tmp_path / "case_1.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Automotive Tooling Systems (Pty) Ltd v Wilkens and Others")
    document.save(source_pdf)
    document.close()
    converter = RejectEveryPdfConverter()

    with pytest.raises(DoclingAnalysisError) as exc_info:
        DoclingAnalyser(converter=converter).analyse(SourceDocument.from_path(source_pdf))

    message = str(exc_info.value)
    assert len(converter.paths) == 2
    assert converter.paths[0] == source_pdf
    assert str(source_pdf) in message
    assert "repaired copy" in message
    assert "runtime or packaged-app problem" in message
    assert "huguenot-docling-" not in message
    assert str(converter.paths[1]) not in message


def test_docling_analyser_reports_corrupt_pdf_as_invalid_without_temp_path(tmp_path: Path) -> None:
    source_pdf = tmp_path / "corrupt.pdf"
    source_pdf.write_bytes(b"not a pdf")
    converter = RejectEveryPdfConverter()

    with pytest.raises(DoclingAnalysisError) as exc_info:
        DoclingAnalyser(converter=converter).analyse(SourceDocument.from_path(source_pdf))

    message = str(exc_info.value)
    assert converter.paths == [source_pdf]
    assert str(source_pdf) in message
    assert "could not be opened" in message
    assert "huguenot-docling-" not in message


def test_docling_analyser_converts_example_case_fixture() -> None:
    source_pdf = Path("examples/cases/case_1.pdf")

    ir = DoclingAnalyser().analyse(SourceDocument.from_path(source_pdf))

    assert ir.page_count == 10
    assert ir.title is not None
    assert "Automotive Tooling Systems" in ir.title
