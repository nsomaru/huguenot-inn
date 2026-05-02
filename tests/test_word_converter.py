import sys
import types
from pathlib import Path

import pytest

from huguenot.documents import Docx2PdfConverter


def test_docx2pdf_converter_uses_lazy_docx2pdf_import(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"docx")
    output_dir = tmp_path / "out"
    calls = []

    def fake_convert(input_path: str, output_path: str) -> None:
        calls.append((input_path, output_path))
        Path(output_path).write_bytes(b"pdf")

    monkeypatch.setitem(sys.modules, "docx2pdf", types.SimpleNamespace(convert=fake_convert))

    output = Docx2PdfConverter().convert_docx_to_pdf(input_docx, output_dir)

    assert output == output_dir / "input.pdf"
    assert output.read_bytes() == b"pdf"
    assert calls == [(str(input_docx), str(output_dir / "input.pdf"))]


def test_docx2pdf_converter_reports_missing_dependency(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delitem(sys.modules, "docx2pdf", raising=False)
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"docx")

    with pytest.raises(RuntimeError, match="docx2pdf"):
        Docx2PdfConverter(
            import_module=lambda _name: (_ for _ in ()).throw(ModuleNotFoundError("docx2pdf"))
        ).convert_docx_to_pdf(
            input_docx,
            tmp_path,
        )


def test_ui_document_converter_selects_docx2pdf_for_microsoft_word() -> None:
    from huguenot.documents import Docx2PdfConverter
    from huguenot.ui.app import WORD_RENDERER_LABEL, PDFCombinerNumbererTOCIndexApp

    app = PDFCombinerNumbererTOCIndexApp.__new__(PDFCombinerNumbererTOCIndexApp)

    class RendererVar:
        def get(self) -> str:
            return WORD_RENDERER_LABEL

    app.renderer_var = RendererVar()  # type: ignore[assignment]

    assert isinstance(app._document_converter(), Docx2PdfConverter)  # noqa: SLF001
