import inspect
from pathlib import Path

from huguenot.domain import Court, IndexSeparator, Matter, Party, PartySide, PDFItem, ProceedingType
from huguenot.domain.page_numbering import DEFAULT_NUMBER_FONT_SIZE, DEFAULT_NUMBER_MARGIN, DEFAULT_NUMBER_POSITION
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


class FakeTree:
    def __init__(self) -> None:
        self.rows = {}
        self._selection: tuple[str, ...] = ()

    def delete(self, *items) -> None:
        self.rows.clear()

    def get_children(self):
        return tuple(self.rows)

    def insert(self, _parent, _where, *, iid, values) -> None:
        self.rows[iid] = values

    def selection(self):
        return self._selection

    def selection_set(self, iid) -> None:
        self._selection = (str(iid),)


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


def test_page_number_ui_defaults_use_shared_values(monkeypatch) -> None:
    captured: list[object] = []

    class FakeVar:
        def __init__(self, *, value):
            captured.append(value)

    class FakeStringVar(FakeVar):
        pass

    class FakeIntVar(FakeVar):
        pass

    app = ui_app.PDFCombinerNumbererTOCIndexApp.__new__(ui_app.PDFCombinerNumbererTOCIndexApp)

    monkeypatch.setattr(ui_app.tk, "StringVar", FakeStringVar)
    monkeypatch.setattr(ui_app.tk, "IntVar", FakeIntVar)
    app.position_var = ui_app.tk.StringVar(value=ui_app.DEFAULT_NUMBER_POSITION)
    app.font_size_var = ui_app.tk.IntVar(value=ui_app.DEFAULT_NUMBER_FONT_SIZE)
    app.margin_var = ui_app.tk.IntVar(value=ui_app.DEFAULT_NUMBER_MARGIN)

    assert app.position_var is not None
    assert captured == [DEFAULT_NUMBER_POSITION, DEFAULT_NUMBER_FONT_SIZE, DEFAULT_NUMBER_MARGIN]
    assert ui_app.DEFAULT_NUMBER_FONT_SIZE == DEFAULT_NUMBER_FONT_SIZE
    assert ui_app.DEFAULT_NUMBER_MARGIN == DEFAULT_NUMBER_MARGIN


def test_output_labels_and_flags_menu_are_wired() -> None:
    ui_source = inspect.getsource(ui_app.PDFCombinerNumbererTOCIndexApp._build_ui)
    menu_source = inspect.getsource(ui_app.PDFCombinerNumbererTOCIndexApp._build_menu)

    assert "Final Court Bundle" in ui_source
    assert "Counsel's Bundle" in ui_source
    assert "Create PDF bundle only" in ui_source
    assert "Flags" in menu_source
    assert "Tools" in menu_source
    assert "Disable physical flag markers" in ui_source
    assert "Add Separator" in ui_source


def test_ui_mixed_rows_show_blank_order_for_separators_and_pdf_numbers() -> None:
    app = ui_app.PDFCombinerNumbererTOCIndexApp.__new__(ui_app.PDFCombinerNumbererTOCIndexApp)
    app.bundle_items = [
        IndexSeparator("Cases"),
        PDFItem(Path("authority.pdf"), "Authority"),
        IndexSeparator("Statutes"),
    ]
    fake_tree = FakeTree()
    app.tree = fake_tree  # type: ignore[assignment]

    app.refresh_tree()

    assert fake_tree.rows == {
        "0": ("", "Cases"),
        "1": (1, "Authority"),
        "2": ("", "Statutes"),
    }


def test_auto_detect_title_warns_for_separator(monkeypatch) -> None:
    app = ui_app.PDFCombinerNumbererTOCIndexApp.__new__(ui_app.PDFCombinerNumbererTOCIndexApp)
    app.bundle_items = [IndexSeparator("Cases")]
    app.tree = FakeTree()  # type: ignore[assignment]
    app.tree.selection_set("0")
    warnings = []
    monkeypatch.setattr(ui_app.messagebox, "showwarning", lambda *args, **kwargs: warnings.append(args))

    app.auto_detect_selected_title()

    assert warnings and warnings[0][0] == "Not a PDF"
    assert app.bundle_items == [IndexSeparator("Cases")]


def test_counsels_bundle_no_matter_uses_plain_bundle_with_counsel_options(monkeypatch) -> None:
    app = ui_app.PDFCombinerNumbererTOCIndexApp.__new__(ui_app.PDFCombinerNumbererTOCIndexApp)
    app.active_matter = None
    captured = {}

    def fake_plain_bundle(**kwargs):
        captured.update(kwargs)

    app._create_plain_pdf_bundle = fake_plain_bundle  # type: ignore[method-assign]

    app.create_counsels_bundle()

    assert captured == {"initialfile": "counsels_bundle.pdf", "counsel_bundle": True}


def test_counsel_render_options_disable_only_physical_markers() -> None:
    app = ui_app.PDFCombinerNumbererTOCIndexApp.__new__(ui_app.PDFCombinerNumbererTOCIndexApp)

    class FakeBooleanVar:
        def get(self) -> bool:
            return True

    app.disable_physical_flag_markers_var = FakeBooleanVar()  # type: ignore[assignment]

    options = app._counsel_pdf_render_options(["#3467A5"])

    assert options.flag_colours == ["#3467A5"]
    assert options.physical_flag_markers is False
    assert options.number_fill_opacity == 1.0
