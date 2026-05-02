from pathlib import Path

from huguenot.domain import Court, Matter, Party, PartySide, PDFItem, ProceedingType
from huguenot.ui import app as ui_app


def make_matter() -> Matter:
    return Matter(
        court=Court("Court"),
        proceeding_type=ProceedingType.APPLICATION,
        parties=(
            Party("First Applicant", PartySide.BRINGING, 1),
            Party("First Respondent", PartySide.OPPOSING, 1),
        ),
    )


def make_app_shell() -> ui_app.PDFCombinerNumbererTOCIndexApp:
    app = ui_app.PDFCombinerNumbererTOCIndexApp.__new__(ui_app.PDFCombinerNumbererTOCIndexApp)
    app.active_matter = make_matter()
    app.pdf_items = [PDFItem(Path("authority.pdf"), "Authority")]
    return app


def test_matter_bundle_save_dialog_uses_matter_filename(monkeypatch) -> None:
    app = make_app_shell()
    captured = {}

    def fake_saveas(**kwargs):
        captured.update(kwargs)
        return ""

    monkeypatch.setattr(ui_app.filedialog, "asksaveasfilename", fake_saveas)

    app.create_combined_pdf()

    assert captured["initialfile"] == "first-applicant_v_first-respondent_AUTHORITIES_BUNDLE.pdf"


def test_matter_docx_save_dialog_uses_matter_filename(monkeypatch) -> None:
    app = make_app_shell()
    captured = {}

    def fake_saveas(**kwargs):
        captured.update(kwargs)
        return ""

    monkeypatch.setattr(ui_app.filedialog, "asksaveasfilename", fake_saveas)

    app.create_authorities_index()

    assert captured["initialfile"] == "first-applicant_v_first-respondent_AUTHORITIES_INDEX.docx"
