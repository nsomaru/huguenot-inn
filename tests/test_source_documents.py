from pathlib import Path

from huguenot.application.duplicates import DuplicateDecision
from huguenot.application.source_import import SourceImportService, plan_source_additions
from huguenot.domain import PDFItem
from huguenot.domain.source_documents import SourceDocument, SourceType


class FakeConverter:
    def __init__(self) -> None:
        self.converted: list[tuple[Path, Path]] = []

    def converter_available(self) -> bool:
        return True

    def convert_to_pdf(self, source_path: Path, output_dir: Path) -> Path:
        self.converted.append((source_path, output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"{source_path.stem}.pdf"
        output.write_bytes(b"pdf")
        return output


def test_source_document_keeps_original_metadata_for_docx_and_rtf(tmp_path: Path) -> None:
    docx = tmp_path / "S v Makwanyane.docx"
    rtf = tmp_path / "Ex parte Minister.rtf"
    docx.write_bytes(b"docx")
    rtf.write_bytes(b"rtf")

    assert SourceDocument.from_path(docx).source_type is SourceType.DOCX
    assert SourceDocument.from_path(rtf).source_type is SourceType.RTF
    assert SourceDocument.from_path(docx).display_title == "S v Makwanyane"


def test_plan_source_additions_supports_docx_rtf_and_preserves_pdf_duplicate_behaviour(tmp_path: Path) -> None:
    pdf = tmp_path / "case.pdf"
    docx = tmp_path / "case.docx"
    rtf = tmp_path / "other.rtf"
    for path in (pdf, docx, rtf):
        path.write_bytes(path.suffix.encode())

    result = plan_source_additions(
        [PDFItem(pdf, "Existing")],
        [pdf, docx, rtf],
        detect_title=lambda path: "Case" if path.suffix == ".docx" else path.stem,
        decide_duplicate=lambda _duplicate, _remaining: DuplicateDecision.ADD_ANYWAY,
    )

    assert result.skipped_existing_paths == [pdf.resolve()]
    assert [item.source_type for item in result.added_sources] == [SourceType.DOCX, SourceType.RTF]
    assert [item.title for item in result.added_pdf_items] == ["Case", "other"]


def test_source_import_service_converts_non_pdf_only_behind_application_boundary(tmp_path: Path) -> None:
    docx = tmp_path / "authority.docx"
    docx.write_bytes(b"docx")
    converter = FakeConverter()
    service = SourceImportService(converter=converter, converted_pdf_dir=tmp_path / "converted")

    source = SourceDocument.from_path(docx, display_title="Authority")
    pdf_item = service.as_pdf_item(source)

    assert pdf_item.title == "Authority"
    assert pdf_item.path == tmp_path / "converted" / "authority.pdf"
    assert converter.converted == [(docx, tmp_path / "converted")]
    assert source.path == docx
    assert source.source_type is SourceType.DOCX
