from __future__ import annotations

import tempfile
import threading
import tkinter as tk
import traceback
from dataclasses import replace
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from typing import Any, cast

from tkinterdnd2 import DND_FILES, TkinterDnD

from huguenot.application import (
    AnalysisService,
    AnalysisStatus,
    DiskUsageService,
    DuplicateDecision,
    DuplicatePDF,
    FlagPaletteService,
    IndexRowService,
    MatterService,
    MissingIRDecision,
    SourceImportService,
    plan_source_additions,
)
from huguenot.documents import (
    DoclingAnalyser,
    DoclingModelManager,
    Docx2PdfConverter,
    FilesystemIRCache,
    LibreOfficeConverter,
    PDFRenderer,
    RendererPreference,
    create_authorities_index_docx_from_rows,
    create_matter_authorities_index_docx_from_rows,
    default_ir_cache_root,
    detect_authority_index_item_from_ir,
    list_system_fonts,
    render_matter_index_pdf_from_rows,
)
from huguenot.domain import (
    DEFAULT_NUMBER_FONT_SIZE,
    DEFAULT_NUMBER_MARGIN,
    DEFAULT_NUMBER_POSITION,
    BundleListItem,
    DocumentHeaderInput,
    DocumentIRIdentity,
    IndexSeparator,
    Matter,
    OutputGenerationSettings,
    PDFItem,
    ProceedingType,
    matter_output_filename,
    matter_output_root,
    pdf_items_from_bundle_items,
)
from huguenot.domain.source_documents import SourceDocument, is_supported_source
from huguenot.pdf import (
    POSITIONS,
    PdfBundleRenderOptions,
    combine_bundle_items_number_and_add_toc,
    combine_bundle_items_with_front_index,
    detect_authority_index_item,
)
from huguenot.pdf.authority_detection import clean_filename_title
from huguenot.persistence import (
    SQLiteCourtRepository,
    SQLiteFlagPaletteRepository,
    SQLiteMatterRepository,
    create_app_database,
)
from huguenot.ui import duplicate_dialog
from huguenot.ui.about import ABOUT_METADATA, about_icon_path, app_icon_path
from huguenot.ui.duplicate_dialog import ask_duplicate_decision
from huguenot.ui.platform import configure_app_identity, configure_macos_quit, root_identity_options

APP_WINDOW_TITLE = "Huguenot Inn"
REPORTLAB_RENDERER_LABEL = "ReportLab (default)"
LIBREOFFICE_RENDERER_LABEL = "LibreOffice"
WORD_RENDERER_LABEL = "Microsoft Word"
ANALYSIS_CACHE_MISSING_ICON = "❌"
ANALYSIS_CACHE_READY_ICON = "✅"
ANALYSIS_IN_PROGRESS_ICON = "⏳"
DUPLICATE_ADD_ANYWAY_LABEL = duplicate_dialog.DUPLICATE_ADD_ANYWAY_LABEL
DUPLICATE_SKIP_LABEL = duplicate_dialog.DUPLICATE_SKIP_LABEL
DUPLICATE_SKIP_ALL_LABEL_TEMPLATE = duplicate_dialog.DUPLICATE_SKIP_ALL_LABEL_TEMPLATE


class MatterDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, service: MatterService) -> None:
        super().__init__(parent)
        self.service = service
        self.result: Matter | None = None
        self.title("New Matter")
        self.resizable(True, True)
        self.transient(cast(Any, parent))
        self.grab_set()

        self.court_var = tk.StringVar()
        self.header_var = tk.StringVar()
        self.proceeding_var = tk.StringVar(value=ProceedingType.APPLICATION.value)
        self.case_var = tk.StringVar()
        self.bringing_vars: list[tk.StringVar] = [tk.StringVar()]
        self.opposing_vars: list[tk.StringVar] = [tk.StringVar()]
        self.bringing_frame: ttk.LabelFrame | None = None
        self.opposing_frame: ttk.LabelFrame | None = None

        self._build()
        self._refresh_party_fields()

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Court name").grid(row=0, column=0, sticky="w")
        court_values = [court.name for court in self.service.list_courts()]
        ttk.Combobox(outer, textvariable=self.court_var, values=court_values, width=58).grid(
            row=0, column=1, sticky="ew", padx=(8, 4)
        )
        ttk.Button(outer, text="Add", command=self._add_court).grid(row=0, column=2, sticky="ew")

        ttk.Label(outer, text="Court header line 2").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(outer, textvariable=self.header_var, values=self.service.list_header_lines(), width=58).grid(
            row=1, column=1, sticky="ew", padx=(8, 4), pady=(8, 0)
        )
        ttk.Button(outer, text="Add", command=self._add_header).grid(row=1, column=2, sticky="ew", pady=(8, 0))

        ttk.Label(outer, text="Proceeding type").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(
            outer,
            textvariable=self.proceeding_var,
            values=[ProceedingType.ACTION.value, ProceedingType.APPLICATION.value],
            state="readonly",
            width=24,
        ).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

        ttk.Label(outer, text="Case number").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(outer, textvariable=self.case_var, width=34).grid(
            row=3, column=1, sticky="w", padx=(8, 0), pady=(8, 0)
        )

        self.bringing_frame = ttk.LabelFrame(outer, text="Parties bringing the proceeding", padding=8)
        self.bringing_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(outer, text="Add bringing party", command=self._add_bringing_party).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )

        self.opposing_frame = ttk.LabelFrame(outer, text="Opposing parties", padding=8)
        self.opposing_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(outer, text="Add opposing party", command=self._add_opposing_party).grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )

        actions = ttk.Frame(outer)
        actions.grid(row=8, column=0, columnspan=3, sticky="e", pady=(14, 0))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Save Matter", command=self._save).pack(side="right")
        outer.columnconfigure(1, weight=1)

    def _refresh_party_fields(self) -> None:
        for frame, variables in [(self.bringing_frame, self.bringing_vars), (self.opposing_frame, self.opposing_vars)]:
            if frame is None:
                continue
            for child in frame.winfo_children():
                child.destroy()
            for index, variable in enumerate(variables, start=1):
                ttk.Label(frame, text=f"{index}.").grid(row=index - 1, column=0, sticky="w")
                ttk.Entry(frame, textvariable=variable, width=62).grid(
                    row=index - 1, column=1, sticky="ew", padx=(6, 0)
                )
            frame.columnconfigure(1, weight=1)

    def _add_court(self) -> None:
        value = simpledialog.askstring("Add court", "Court name:", parent=self)
        if value:
            court = self.service.add_court(value, self.header_var.get() or None)
            self.court_var.set(court.name)

    def _add_header(self) -> None:
        value = simpledialog.askstring("Add court header line 2", "Header line:", parent=self)
        if value:
            self.service.add_header_line(value)
            self.header_var.set(value)

    def _add_bringing_party(self) -> None:
        self.bringing_vars.append(tk.StringVar())
        self._refresh_party_fields()

    def _add_opposing_party(self) -> None:
        self.opposing_vars.append(tk.StringVar())
        self._refresh_party_fields()

    def _save(self) -> None:
        try:
            self.result = self.service.create_matter(
                court_name=self.court_var.get(),
                court_header_line_2=self.header_var.get() or None,
                proceeding_type=ProceedingType(self.proceeding_var.get()),
                case_number=self.case_var.get(),
                bringing_party_names=[value.get() for value in self.bringing_vars],
                opposing_party_names=[value.get() for value in self.opposing_vars],
            )
        except Exception as exc:
            messagebox.showerror("Invalid matter", str(exc), parent=self)
            return
        self.destroy()


class OpenMatterDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, matters: list[Matter]) -> None:
        super().__init__(parent)
        self.title("Open Matter")
        self.transient(cast(Any, parent))
        self.grab_set()
        self.result: Matter | None = None
        self._matters = matters

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(outer, width=72, height=10)
        self.listbox.pack(fill="both", expand=True)
        for matter in matters:
            self.listbox.insert(tk.END, matter.display_name)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Open", command=self._open).pack(side="right")

    def _open(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("No matter selected", "Please select a matter.", parent=self)
            return
        self.result = self._matters[int(selection[0])]
        self.destroy()


class FlagPaletteDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, service: FlagPaletteService) -> None:
        super().__init__(parent)
        self.service = service
        self.title("Flags")
        self.transient(cast(Any, parent))
        self.grab_set()
        self.colours = self.service.list_palette()

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Counsel's Bundle flag colours").pack(anchor="w")
        self.listbox = tk.Listbox(outer, width=24, height=10)
        self.listbox.pack(fill="both", expand=True, pady=(8, 8))
        self._refresh()

        actions = ttk.Frame(outer)
        actions.pack(fill="x")
        ttk.Button(actions, text="Add", command=self._add).pack(side="left")
        ttk.Button(actions, text="Edit", command=self._edit).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Delete", command=self._delete).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Up", command=self._move_up).pack(side="left", padx=(18, 0))
        ttk.Button(actions, text="Down", command=self._move_down).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Save", command=self._save).pack(side="right", padx=(6, 0))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side="right")

    def _refresh(self) -> None:
        self.listbox.delete(0, tk.END)
        for colour in self.colours:
            self.listbox.insert(tk.END, colour)

    def _selected_index(self) -> int | None:
        selection = self.listbox.curselection()
        return None if not selection else int(selection[0])

    def _choose_colour(self, initial: str | None = None) -> str | None:
        _rgb, colour = colorchooser.askcolor(color=initial, parent=self, title="Choose flag colour")
        return None if colour is None else colour

    def _add(self) -> None:
        colour = self._choose_colour()
        if colour:
            self.colours.append(colour)
            self._refresh()
            self.listbox.selection_set(tk.END)

    def _edit(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        colour = self._choose_colour(self.colours[index])
        if colour:
            self.colours[index] = colour
            self._refresh()
            self.listbox.selection_set(index)

    def _delete(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        if len(self.colours) == 1:
            messagebox.showwarning("Flags", "At least one flag colour is required.", parent=self)
            return
        del self.colours[index]
        self._refresh()

    def _move_up(self) -> None:
        index = self._selected_index()
        if index is None or index == 0:
            return
        self.colours[index - 1], self.colours[index] = self.colours[index], self.colours[index - 1]
        self._refresh()
        self.listbox.selection_set(index - 1)

    def _move_down(self) -> None:
        index = self._selected_index()
        if index is None or index >= len(self.colours) - 1:
            return
        self.colours[index + 1], self.colours[index] = self.colours[index], self.colours[index + 1]
        self._refresh()
        self.listbox.selection_set(index + 1)

    def _save(self) -> None:
        try:
            self.colours = self.service.replace_palette(self.colours)
        except ValueError as exc:
            messagebox.showerror("Invalid flags", str(exc), parent=self)
            return
        self.destroy()


class DiskUsageDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, service: DiskUsageService) -> None:
        super().__init__(parent)
        self.service = service
        self.title("Disk usage")
        self.transient(cast(Any, parent))
        self.resizable(False, False)
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)
        self.usage_label = ttk.Label(outer, text="calculating...")
        self.usage_label.pack(anchor="w", pady=(0, 10))
        ttk.Button(outer, text="Clear cache", command=self._clear_cache).pack(side="left")
        ttk.Button(outer, text="Close", command=self.destroy).pack(side="right")
        self._calculate_async()

    def _calculate_async(self) -> None:
        def worker() -> None:
            try:
                usage = self.service.calculate()
            except Exception as exc:
                self.after(0, self.usage_label.config, {"text": f"Failed to calculate disk usage: {exc}"})
                return
            text = (
                f"SQLite database: {_format_bytes(usage.sqlite_bytes)}\n"
                f"Parquet cache: {_format_bytes(usage.cache_bytes)}"
            )
            self.after(0, self.usage_label.config, {"text": text})

        threading.Thread(target=worker, daemon=True).start()

    def _clear_cache(self) -> None:
        removed = self.service.clear_cache()
        self.usage_label.config(text=f"Cleared {_format_bytes(removed)} from the parquet cache. Recalculating...")
        self._calculate_async()


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


class PDFCombinerNumbererTOCIndexApp(TkinterDnD.Tk):
    def __init__(self) -> None:
        super().__init__(**root_identity_options(APP_WINDOW_TITLE))
        configure_app_identity(self, APP_WINDOW_TITLE)
        self.title(APP_WINDOW_TITLE)
        self.geometry("900x570")
        self.minsize(800, 500)

        database = create_app_database()
        self.database = database
        self.ir_cache = FilesystemIRCache()
        self.docling_model_manager = DoclingModelManager()
        self._docling_model_status_text = "Docling models: checking"
        self.source_documents: dict[Path, SourceDocument] = {}
        self._analysis_warning_shown = False
        self._analysis_in_progress_source_path: Path | None = None
        self._analysis_progress_sources: tuple[Path, ...] = ()
        court_repository = SQLiteCourtRepository(database)
        matter_repository = SQLiteMatterRepository(database)
        flag_palette_repository = SQLiteFlagPaletteRepository(database)
        self.matter_service = MatterService(matter_repository, court_repository)
        self.flag_palette_service = FlagPaletteService(flag_palette_repository)
        self.active_matter = self.matter_service.get_last_active_matter()

        self.bundle_items: list[BundleListItem] = []
        self.position_var = tk.StringVar(value=DEFAULT_NUMBER_POSITION)
        self.font_size_var = tk.IntVar(value=DEFAULT_NUMBER_FONT_SIZE)
        self.margin_var = tk.IntVar(value=DEFAULT_NUMBER_MARGIN)
        self.renderer_var = tk.StringVar(value=REPORTLAB_RENDERER_LABEL)
        self.index_font_var = tk.StringVar(value="Times New Roman")
        self.disable_physical_flag_markers_var = tk.BooleanVar(value=False)
        self.analysis_progress_var = tk.IntVar(value=0)
        self._system_fonts = list_system_fonts()
        self._icon_image: tk.PhotoImage | None = None
        self._about_icon_image: tk.PhotoImage | None = None
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._close_application)
        configure_macos_quit(self, self._close_application)
        self._configure_app_icon()
        self._update_status()
        self._refresh_docling_model_status_async()

    @property
    def pdf_items(self) -> list[PDFItem]:
        return pdf_items_from_bundle_items(self.bundle_items)

    @pdf_items.setter
    def pdf_items(self, value: list[PDFItem]) -> None:
        self.bundle_items = list(value)

    def _build_ui(self) -> None:
        self._build_menu()
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(
            outer,
            text="Drag PDFs here, edit titles, then create a numbered bundle or authorities index",
            font=("TkDefaultFont", 15, "bold"),
        )
        title.pack(anchor="w", pady=(0, 12))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 12))
        ttk.Label(controls, text="Number position:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(controls, textvariable=self.position_var, values=POSITIONS, state="readonly", width=20).grid(
            row=0, column=1, sticky="w", padx=(8, 24)
        )
        ttk.Label(controls, text="Font size:").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(controls, from_=10, to=28, textvariable=self.font_size_var, width=5).grid(
            row=0, column=3, sticky="w", padx=(8, 24)
        )
        ttk.Label(controls, text="Margin:").grid(row=0, column=4, sticky="w")
        ttk.Spinbox(controls, from_=10, to=100, textvariable=self.margin_var, width=5).grid(
            row=0, column=5, sticky="w", padx=(8, 0)
        )
        advanced = ttk.LabelFrame(controls, text="Advanced", padding=(8, 6))
        advanced.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(10, 0))
        ttk.Label(advanced, text="PDF index renderer:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            advanced,
            textvariable=self.renderer_var,
            values=[REPORTLAB_RENDERER_LABEL, LIBREOFFICE_RENDERER_LABEL, WORD_RENDERER_LABEL],
            state="readonly",
            width=18,
        ).grid(row=0, column=1, sticky="w", padx=(8, 24))
        ttk.Label(advanced, text="Index font:").grid(row=0, column=2, sticky="w")
        font_box = ttk.Combobox(advanced, textvariable=self.index_font_var, values=self._system_fonts, width=30)
        font_box.grid(row=0, column=3, sticky="ew", padx=(8, 0))
        font_box.bind("<KeyRelease>", self._filter_font_choices)
        ttk.Checkbutton(
            advanced,
            text="Disable physical flag markers",
            variable=self.disable_physical_flag_markers_var,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))
        advanced.columnconfigure(3, weight=1)
        controls.columnconfigure(5, weight=1)

        main = ttk.Frame(outer)
        main.pack(fill="both", expand=True)
        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)
        self.tree = ttk.Treeview(left, columns=("order", "analysis", "title"), show="headings", selectmode="browse")
        self.tree.heading("order", text="#")
        self.tree.heading("analysis", text="Analysis")
        self.tree.heading("title", text="PDF ToC entry / index item")
        self.tree.column("order", width=45, anchor="center", stretch=False)
        self.tree.column("analysis", width=80, anchor="center", stretch=False)
        self.tree.column("title", width=570, anchor="w", stretch=True)
        self.tree.pack(fill="both", expand=True)
        dnd_tree = cast(Any, self.tree)
        dnd_tree.drop_target_register(DND_FILES)
        dnd_tree.dnd_bind("<<Drop>>", self.on_drop)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Return>", lambda event: self.edit_selected_title())
        ttk.Label(
            left,
            text="Double-click a title to edit it. This title is used for PDF bookmarks and index rows.",
        ).pack(anchor="w", pady=(6, 0))

        buttons = ttk.Frame(main)
        buttons.pack(side="right", fill="y", padx=(12, 0))
        ttk.Button(buttons, text="Add PDFs", command=self.add_pdfs_dialog).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Add Separator", command=self.add_separator).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Edit title", command=self.edit_selected_title).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Auto-detect title", command=self.auto_detect_selected_title).pack(
            fill="x", pady=(0, 6)
        )
        ttk.Button(buttons, text="AI Analyse", command=self.ai_analyse_selected_sources).pack(fill="x", pady=(0, 6))
        ttk.Progressbar(buttons, variable=self.analysis_progress_var, maximum=100, mode="determinate").pack(
            fill="x", pady=(0, 6)
        )
        ttk.Button(buttons, text="Move up", command=self.move_up).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Move down", command=self.move_down).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Remove", command=self.remove_selected).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Clear", command=self.clear_list).pack(fill="x", pady=(0, 18))
        ttk.Button(buttons, text="Final Court Bundle", command=self.create_combined_pdf).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Counsel's Bundle", command=self.create_counsels_bundle).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Create PDF bundle only", command=self.create_pdf_bundle_only).pack(
            fill="x", pady=(0, 6)
        )
        ttk.Button(buttons, text="Create authorities index (.docx)", command=self.create_authorities_index).pack(
            fill="x"
        )

        self.status = ttk.Label(outer, text="", anchor="w")
        self.status.pack(fill="x", pady=(12, 0))

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New Matter", command=self.new_matter)
        file_menu.add_command(label="Open/Select Matter", command=self.open_matter)
        file_menu.add_command(label="Clear Active Matter", command=self.clear_active_matter)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._close_application)
        menu.add_cascade(label="File", menu=file_menu)
        tools_menu = tk.Menu(menu, tearoff=False)
        tools_menu.add_command(label="Flags", command=self.open_flags_dialog)
        tools_menu.add_command(label="Disk usage", command=self.open_disk_usage_dialog)
        menu.add_cascade(label="Tools", menu=tools_menu)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="About Huguenot Inn", command=self.show_about)
        menu.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menu)

    def _configure_app_icon(self) -> None:
        icon_path = app_icon_path()
        if not icon_path.exists():
            return
        try:
            self._icon_image = tk.PhotoImage(file=str(icon_path))
            self.iconphoto(True, self._icon_image)
        except tk.TclError:
            self._icon_image = None

    def _close_application(self) -> None:
        self.destroy()

    def _filter_font_choices(self, _event=None) -> None:
        query = self.index_font_var.get().lower()
        matches = [font for font in self._system_fonts if query in font.lower()]
        widget = self.focus_get()
        if isinstance(widget, ttk.Combobox):
            widget.configure(values=matches or self._system_fonts)

    def _renderer_preference(self) -> RendererPreference:
        value = self.renderer_var.get().lower()
        renderer = {
            "libreoffice": PDFRenderer.LIBREOFFICE,
            "microsoft word": PDFRenderer.LIBREOFFICE,
        }.get(value, PDFRenderer.REPORTLAB)
        return RendererPreference(renderer)

    def _document_converter(self):
        if self.renderer_var.get() == WORD_RENDERER_LABEL:
            return Docx2PdfConverter()
        return LibreOfficeConverter()

    def _source_import_service(self) -> SourceImportService:
        return SourceImportService(
            converter=self._document_converter(), converted_pdf_dir=default_ir_cache_root() / "converted-pdfs"
        )

    def _analysis_service(self) -> AnalysisService:
        return AnalysisService(
            cache=self.ir_cache,
            analyser=DoclingAnalyser(model_artifacts_path=self.docling_model_manager.cache_root),
            model_manager=self.docling_model_manager,
        )

    def _disk_usage_service(self) -> DiskUsageService:
        return DiskUsageService(database_path=self.database.path, cache=self.ir_cache)

    def _index_row_service(self) -> IndexRowService:
        return IndexRowService(
            cache=self.ir_cache,
            generate_missing_ir=self._generate_missing_ir,
            source_identity_provider=self._source_identity_for_pdf_item,
        )

    def _source_identity_for_pdf_item(self, item: PDFItem) -> DocumentIRIdentity:
        source = self._source_for_path(item.path)
        return DocumentIRIdentity.from_path(source.path, source_type=source.source_type)

    def _output_settings(self, *, header_title: str = "", colour_page_ranges: bool = False) -> OutputGenerationSettings:
        palette = tuple(self.flag_palette_service.list_palette()) if colour_page_ranges else ()
        return OutputGenerationSettings(
            header_title=header_title,
            index_font=self.index_font_var.get(),
            colour_page_ranges=colour_page_ranges,
            flag_colours=palette,
            physical_flag_markers=not bool(self.disable_physical_flag_markers_var.get()),
            renderer_preference=self.renderer_var.get(),
        )

    def _generate_missing_ir(self, missing: tuple[DocumentIRIdentity, ...]) -> None:
        self._analyse_missing_sources(missing, settings=self._output_settings())

    def _analyse_missing_sources(
        self, missing: tuple[DocumentIRIdentity, ...], *, settings: OutputGenerationSettings
    ) -> None:
        sources = [self._source_for_path(identity.path_as_path) for identity in missing]
        self._analysis_service().analyse_sources(
            sources,
            separator_titles=tuple(item.title for item in self.bundle_items if isinstance(item, IndexSeparator)),
            matter_context=self.active_matter.display_name if self.active_matter else "",
            settings=settings,
        )

    def _source_for_path(self, path: Path) -> SourceDocument:
        source_documents = getattr(self, "source_documents", {})
        return source_documents.get(path, SourceDocument.from_path(path, display_title=clean_filename_title(path)))

    def _rows_for_output(
        self,
        *,
        header_title: str = "",
        colour_page_ranges: bool = False,
        flag_colours: list[str] | None = None,
    ):
        partial_cache = []
        decision = MissingIRDecision.CONTINUE_LEGACY
        settings = self._output_settings(header_title=header_title, colour_page_ranges=colour_page_ranges)
        separator_titles = tuple(item.title for item in self.bundle_items if isinstance(item, IndexSeparator))
        matter_context = self.active_matter.display_name if self.active_matter else ""

        def warn(partial) -> None:
            partial_cache.append(partial)

        result = self._index_row_service().build_rows(
            self.bundle_items,
            settings=settings,
            separator_titles=separator_titles,
            matter_context=matter_context,
            flag_colours=flag_colours,
            on_partial_cache=warn,
            missing_ir_decision=decision,
        )
        if partial_cache:
            generate = messagebox.askyesno(
                "Partial AI analysis cache",
                "Some sources do not have cached Docling IR. "
                "Generate missing IR now? Choose No to continue with legacy output.",
                parent=self,
            )
            if generate:
                self._analyse_missing_sources(partial_cache[0].missing, settings=settings)
                result = self._index_row_service().build_rows(
                    self.bundle_items,
                    settings=settings,
                    separator_titles=separator_titles,
                    matter_context=matter_context,
                    flag_colours=flag_colours,
                )
        return result.rows

    def show_about(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("About Huguenot Inn")
        dialog.transient(self)
        dialog.resizable(False, False)
        outer = ttk.Frame(dialog, padding=16)
        outer.pack(fill="both", expand=True)
        icon_path = about_icon_path()
        if icon_path.exists():
            try:
                self._about_icon_image = tk.PhotoImage(file=str(icon_path))
            except tk.TclError:
                self._about_icon_image = self._icon_image
        if self._about_icon_image is not None:
            ttk.Label(outer, image=self._about_icon_image).grid(row=0, column=0, rowspan=5, sticky="n", padx=(0, 12))
        text = (
            f"{ABOUT_METADATA.application_name}\n"
            f"Version {ABOUT_METADATA.version}\n\n"
            f"{ABOUT_METADATA.license_notice}\n\n"
            f"Author: {ABOUT_METADATA.author}\n"
            f"Contact: {ABOUT_METADATA.contact}"
        )
        ttk.Label(outer, text=text, justify="left").grid(row=0, column=1, sticky="w")
        ttk.Button(outer, text="OK", command=dialog.destroy).grid(row=1, column=1, sticky="e", pady=(12, 0))

    def open_flags_dialog(self) -> None:
        dialog = FlagPaletteDialog(self, self.flag_palette_service)
        self.wait_window(dialog)

    def open_disk_usage_dialog(self) -> None:
        DiskUsageDialog(self, self._disk_usage_service())

    def ai_analyse_selected_sources(self) -> None:
        if not self.pdf_items:
            messagebox.showwarning("No sources", "Please add one or more source documents first.")
            return
        if not self._analysis_warning_shown:
            proceed = messagebox.askokcancel(
                "AI Analyse",
                self._docling_analysis_warning(),
                parent=self,
            )
            if not proceed:
                return
            self._analysis_warning_shown = True
        sources = [self._source_for_path(item.path) for item in self.pdf_items]
        self._analysis_progress_sources = tuple(source.path for source in sources)
        self._analysis_in_progress_source_path = None
        self.refresh_tree()
        self.analysis_progress_var.set(0)
        self._update_status("AI Analyse queued...")

        def progress(status: AnalysisStatus) -> None:
            percentage = self._analysis_progress_percentage(status)
            self.after(0, self._update_analysis_status, percentage, status)

        def worker() -> None:
            try:
                self._analysis_service().analyse_sources(
                    sources,
                    separator_titles=tuple(
                        item.title for item in self.bundle_items if isinstance(item, IndexSeparator)
                    ),
                    matter_context=self.active_matter.display_name if self.active_matter else "",
                    settings=self._output_settings(),
                    progress=progress,
                )
            except Exception as exc:
                traceback.print_exc()
                self.after(0, messagebox.showerror, "AI Analyse failed", str(exc))
                if not self.docling_model_manager.models_ready():
                    self.after(0, self._set_docling_model_status, "Docling models: not downloaded")
                self.after(0, self._finish_analysis, "AI Analyse failed.")
                return
            self.after(0, self._finish_analysis, "AI Analyse complete.")

        threading.Thread(target=worker, daemon=True).start()

    def _update_analysis_progress(self, percentage: int, message: str) -> None:
        self.analysis_progress_var.set(percentage)
        self._update_status(message)

    def _update_analysis_status(self, percentage: int, status: AnalysisStatus) -> None:
        if status.stage == "models-checking":
            self._docling_model_status_text = "Docling models: checking"
        elif status.stage == "models-downloading":
            suffix = f" ({status.current}/{status.total})" if status.total else ""
            self._docling_model_status_text = f"Docling models: downloading{suffix}"
        elif status.stage == "models-ready":
            self._docling_model_status_text = "Docling models: ready"
        self._update_analysis_marker(status)
        self._update_analysis_progress(percentage, status.message)

    def _update_analysis_marker(self, status: AnalysisStatus) -> None:
        current_path = getattr(self, "_analysis_in_progress_source_path", None)
        next_path = current_path
        if status.stage == "analysing":
            source_paths = getattr(self, "_analysis_progress_sources", ())
            next_path = source_paths[status.current - 1] if 1 <= status.current <= len(source_paths) else None
        elif status.stage in {"queued", "caching", "complete"}:
            next_path = None
        if next_path == current_path:
            return
        self._analysis_in_progress_source_path = next_path
        self.refresh_tree()

    def _finish_analysis(self, message: str) -> None:
        self._analysis_in_progress_source_path = None
        self.refresh_tree()
        self._update_status(message)

    def _analysis_progress_percentage(self, status: AnalysisStatus) -> int:
        if status.stage == "complete":
            return 100
        if status.stage == "caching":
            return 95
        if status.stage == "queued":
            return 30
        if status.stage == "analysing":
            return 30 + int((status.current / max(status.total, 1)) * 60)
        if status.stage == "models-ready":
            return 25
        if status.stage == "models-downloading":
            return 5 + int((status.current / max(status.total, 1)) * 20)
        return 1

    def _docling_analysis_warning(self) -> str:
        if self.docling_model_manager.models_ready():
            return "Docling models are already downloaded. Continue with AI Analyse?"
        return (
            "Docling models are not downloaded yet. AI Analyse will download them the first time it runs; "
            "progress will be shown in the status bar. Continue?"
        )

    def _refresh_docling_model_status_async(self) -> None:
        def worker() -> None:
            ready = self.docling_model_manager.models_ready()
            status = "Docling models: ready" if ready else "Docling models: not downloaded"
            self.after(0, self._set_docling_model_status, status)

        threading.Thread(target=worker, daemon=True).start()

    def _set_docling_model_status(self, status: str) -> None:
        self._docling_model_status_text = status
        self._update_status()

    def _update_status(self, message: str | None = None) -> None:
        matter_text = f"Active matter: {self.active_matter.display_name}" if self.active_matter else "No active matter"
        separator_count = len(self.bundle_items) - len(self.pdf_items)
        pdf_text = f"{len(self.pdf_items)} PDF(s)"
        if separator_count:
            pdf_text = f"{pdf_text}, {separator_count} separator(s)"
        model_text = getattr(self, "_docling_model_status_text", "Docling models: checking")
        base = f"{matter_text} | {pdf_text} | {model_text}"
        self.status.config(text=f"{base} | {message}" if message else base)

    def new_matter(self) -> None:
        dialog = MatterDialog(self, self.matter_service)
        self.wait_window(dialog)
        if dialog.result:
            self.active_matter = dialog.result
            self._update_status("Matter saved.")

    def open_matter(self) -> None:
        matters = self.matter_service.list_matters()
        if not matters:
            messagebox.showinfo("No matters", "No saved matters are available.")
            return
        dialog = OpenMatterDialog(self, matters)
        self.wait_window(dialog)
        if dialog.result and dialog.result.id is not None:
            self.active_matter = self.matter_service.set_active_matter(dialog.result.id)
            self._update_status("Matter opened.")

    def clear_active_matter(self) -> None:
        self.active_matter = self.matter_service.set_active_matter(None)
        self._update_status("Active matter cleared.")

    def parse_drop_files(self, data: str) -> list[Path]:
        raw_paths = self.tk.splitlist(data)
        return [Path(p) for p in raw_paths if Path(p).is_file() and is_supported_source(Path(p))]

    def add_paths(self, paths: list[Path]) -> None:
        result = plan_source_additions(
            self.pdf_items,
            paths,
            detect_title=self._detect_source_title,
            decide_duplicate=self._decide_duplicate_pdf,
        )
        service = self._source_import_service()
        added_items = []
        for source in result.added_sources:
            item = service.as_pdf_item(source)
            added_items.append(item)
            self.source_documents[item.path] = source
        self.bundle_items.extend(added_items)
        self.refresh_tree()
        added = len(added_items)
        duplicate_count = len(result.duplicates)
        if duplicate_count:
            self._update_status(f"Added {added} source(s); reviewed {duplicate_count} duplicate(s).")
        else:
            self._update_status(f"Added {added} source(s)." if added else "No new source documents added.")

    def _detect_source_title(self, path: Path) -> str:
        source = SourceDocument.from_path(path, display_title=clean_filename_title(path))
        identity = source.path
        ir = self.ir_cache.load_source_ir(DocumentIRIdentity.from_path(identity, source_type=source.source_type))
        if ir is not None:
            return detect_authority_index_item_from_ir(ir, fallback=lambda: source.display_title)
        if source.source_type.value == "pdf":
            return detect_authority_index_item(path)
        return source.display_title

    def _decide_duplicate_pdf(self, duplicate: DuplicatePDF, remaining_duplicates: int) -> DuplicateDecision:
        return ask_duplicate_decision(self, duplicate, remaining_duplicates)

    def refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        pdf_number = 0
        for index, item in enumerate(self.bundle_items):
            if isinstance(item, PDFItem):
                pdf_number += 1
                values = (pdf_number, self._analysis_icon_for_item(item), item.title)
            else:
                values = ("", "", item.title)
            self.tree.insert("", tk.END, iid=str(index), values=values)

    def _analysis_icon_for_item(self, item: PDFItem) -> str:
        source = self._source_for_analysis_icon(item)
        if source is None:
            return ANALYSIS_CACHE_MISSING_ICON
        if getattr(self, "_analysis_in_progress_source_path", None) == source.path:
            return ANALYSIS_IN_PROGRESS_ICON
        cache = getattr(self, "ir_cache", None)
        if cache is None:
            return ANALYSIS_CACHE_MISSING_ICON
        try:
            identity = DocumentIRIdentity.from_path(source.path, source_type=source.source_type)
            has_cache = cache.load_source_ir(identity) is not None
        except Exception:
            return ANALYSIS_CACHE_MISSING_ICON
        return ANALYSIS_CACHE_READY_ICON if has_cache else ANALYSIS_CACHE_MISSING_ICON

    def _source_for_analysis_icon(self, item: PDFItem) -> SourceDocument | None:
        source = getattr(self, "source_documents", {}).get(item.path)
        if source is not None:
            return source
        try:
            return SourceDocument.from_path(item.path, display_title=clean_filename_title(item.path))
        except Exception:
            return None

    def selected_index(self) -> int | None:
        selection = self.tree.selection()
        return None if not selection else int(selection[0])

    def on_drop(self, event) -> None:
        pdfs = self.parse_drop_files(event.data)
        if not pdfs:
            messagebox.showwarning("No sources", "Please drop one or more PDF, DOCX, or RTF files.")
            return
        self.after_idle(self.add_paths, pdfs)

    def add_pdfs_dialog(self) -> None:
        selected = filedialog.askopenfilenames(
            title="Choose source documents",
            filetypes=[
                ("Source documents", "*.pdf *.docx *.rtf"),
                ("PDF files", "*.pdf"),
                ("Word/RTF files", "*.docx *.rtf"),
            ],
        )
        if selected:
            self.add_paths([Path(p) for p in selected])

    def add_separator(self) -> None:
        title = simpledialog.askstring(
            title="Add separator",
            prompt="Separator title:",
            parent=self,
        )
        if title is None:
            return
        title = title.strip()
        if not title:
            messagebox.showwarning("Blank title", "The title cannot be blank.")
            return
        self.bundle_items.append(IndexSeparator(title))
        self.refresh_tree()
        self.tree.selection_set(str(len(self.bundle_items) - 1))
        self._update_status(f"Added separator: {title}")

    def on_tree_double_click(self, event) -> None:
        if self.tree.identify("region", event.x, event.y) == "cell" and self.tree.identify_column(event.x) == "#3":
            self.edit_selected_title()

    def edit_selected_title(self) -> None:
        index = self.selected_index()
        if index is None:
            messagebox.showwarning("Nothing selected", "Please select a PDF first.")
            return
        item = self.bundle_items[index]
        new_title = simpledialog.askstring(
            title="Edit title",
            prompt="PDF ToC entry / index item:",
            initialvalue=item.title,
            parent=self,
        )
        if new_title is None:
            return
        new_title = new_title.strip()
        if not new_title:
            messagebox.showwarning("Blank title", "The title cannot be blank.")
            return
        self.bundle_items[index] = replace(item, title=new_title)
        self.refresh_tree()
        self.tree.selection_set(str(index))
        self._update_status(f"Renamed title to: {new_title}")

    def auto_detect_selected_title(self) -> None:
        index = self.selected_index()
        if index is None:
            messagebox.showwarning("Nothing selected", "Please select a PDF first.")
            return
        item = self.bundle_items[index]
        if not isinstance(item, PDFItem):
            messagebox.showwarning("Not a PDF", "Auto-detect title is only available for PDF rows.")
            return
        self.bundle_items[index] = replace(item, title=self._detect_source_title(item.path))
        self.refresh_tree()
        self.tree.selection_set(str(index))
        self._update_status(f"Auto-detected title: {self.bundle_items[index].title}")

    def move_up(self) -> None:
        index = self.selected_index()
        if index is None or index == 0:
            return
        self.bundle_items[index - 1], self.bundle_items[index] = self.bundle_items[index], self.bundle_items[index - 1]
        self.refresh_tree()
        self.tree.selection_set(str(index - 1))

    def move_down(self) -> None:
        index = self.selected_index()
        if index is None or index >= len(self.bundle_items) - 1:
            return
        self.bundle_items[index + 1], self.bundle_items[index] = self.bundle_items[index], self.bundle_items[index + 1]
        self.refresh_tree()
        self.tree.selection_set(str(index + 1))

    def remove_selected(self) -> None:
        index = self.selected_index()
        if index is None:
            return
        removed = self.bundle_items.pop(index)
        self.refresh_tree()
        removed_name = removed.path.name if isinstance(removed, PDFItem) else removed.title
        self._update_status(f"Removed {removed_name}.")

    def clear_list(self) -> None:
        self.bundle_items.clear()
        self.refresh_tree()
        self._update_status("List cleared.")

    def create_pdf_bundle_only(self) -> None:
        self._create_plain_pdf_bundle(initialfile="combined_numbered.pdf")

    def create_combined_pdf(self) -> None:
        if not self.active_matter:
            self._create_plain_pdf_bundle(initialfile="combined_numbered.pdf")
            return
        if not self.pdf_items:
            messagebox.showwarning("No PDFs", "Please add one or more PDFs first.")
            return
        output_path_str = filedialog.asksaveasfilename(
            title="Save matter bundle PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=matter_output_filename(self.active_matter, "AUTHORITIES_BUNDLE", ".pdf"),
        )
        if not output_path_str:
            return
        header = simpledialog.askstring(
            title="Document header",
            prompt="Document header:",
            initialvalue="AUTHORITIES BUNDLE",
            parent=self,
        )
        if header is None:
            return
        output_path = Path(output_path_str)
        self._update_status("Creating matter bundle PDF...")
        self.update_idletasks()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                index_pdf = Path(tmp) / "matter_index.pdf"
                converter = self._document_converter()
                rows = self._rows_for_output(header_title=header.strip() or "AUTHORITIES BUNDLE")
                _used_libreoffice, links = render_matter_index_pdf_from_rows(
                    self.active_matter,
                    DocumentHeaderInput(header.strip() or "AUTHORITIES BUNDLE"),
                    self.pdf_items,
                    rows,
                    index_pdf,
                    converter=converter,
                    renderer_preference=self._renderer_preference(),
                    font_name=self.index_font_var.get(),
                )
                combine_bundle_items_with_front_index(
                    self.bundle_items,
                    index_pdf,
                    links,
                    output_path,
                    self.position_var.get(),
                    int(self.font_size_var.get()),
                    int(self.margin_var.get()),
                    toc_root_title=matter_output_root(self.active_matter),
                    index_rows=rows,
                )
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Failed", f"Could not create matter bundle PDF: {exc}")
            self._update_status("Failed to create matter bundle PDF.")
            return
        self._update_status(f"Created: {output_path}")
        messagebox.showinfo("Complete", f"Created: {output_path}")

    def create_counsels_bundle(self) -> None:
        if not self.active_matter:
            self._create_plain_pdf_bundle(initialfile="counsels_bundle.pdf", counsel_bundle=True)
            return
        if not self.pdf_items:
            messagebox.showwarning("No PDFs", "Please add one or more PDFs first.")
            return
        output_path_str = filedialog.asksaveasfilename(
            title="Save counsel's bundle PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=matter_output_filename(self.active_matter, "COUNSELS_BUNDLE", ".pdf"),
        )
        if not output_path_str:
            return
        header = simpledialog.askstring(
            title="Document header",
            prompt="Document header:",
            initialvalue="AUTHORITIES BUNDLE",
            parent=self,
        )
        if header is None:
            return
        output_path = Path(output_path_str)
        palette = self.flag_palette_service.list_palette()
        rows = self._rows_for_output(header_title="AUTHORITIES BUNDLE", colour_page_ranges=True, flag_colours=palette)
        self._update_status("Creating counsel's bundle PDF...")
        self.update_idletasks()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                index_pdf = Path(tmp) / "matter_index.pdf"
                converter = self._document_converter()
                _used_libreoffice, links = render_matter_index_pdf_from_rows(
                    self.active_matter,
                    DocumentHeaderInput(header.strip() or "AUTHORITIES BUNDLE"),
                    self.pdf_items,
                    rows,
                    index_pdf,
                    converter=converter,
                    renderer_preference=self._renderer_preference(),
                    font_name=self.index_font_var.get(),
                    colour_page_ranges=True,
                )
                combine_bundle_items_with_front_index(
                    self.bundle_items,
                    index_pdf,
                    links,
                    output_path,
                    self.position_var.get(),
                    int(self.font_size_var.get()),
                    int(self.margin_var.get()),
                    toc_root_title=matter_output_root(self.active_matter),
                    render_options=self._counsel_pdf_render_options(palette),
                    index_rows=rows,
                )
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Failed", f"Could not create counsel's bundle PDF: {exc}")
            self._update_status("Failed to create counsel's bundle PDF.")
            return
        self._update_status(f"Created: {output_path}")
        messagebox.showinfo("Complete", f"Created: {output_path}")

    def _create_plain_pdf_bundle(self, *, initialfile: str, counsel_bundle: bool = False) -> None:
        if not self.pdf_items:
            messagebox.showwarning("No PDFs", "Please add one or more PDFs first.")
            return
        output_path_str = filedialog.asksaveasfilename(
            title="Save combined numbered PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=initialfile,
        )
        if not output_path_str:
            return
        output_path = Path(output_path_str)
        try:
            palette = self.flag_palette_service.list_palette() if counsel_bundle else None
            combine_bundle_items_number_and_add_toc(
                self.bundle_items,
                output_path,
                self.position_var.get(),
                int(self.font_size_var.get()),
                int(self.margin_var.get()),
                render_options=self._counsel_pdf_render_options(palette) if palette else None,
            )
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Failed", f"Could not create PDF: {exc}")
            self._update_status("Failed to create combined PDF.")
            return
        self._update_status(f"Created: {output_path}")
        messagebox.showinfo("Complete", f"Created: {output_path}")

    def _counsel_pdf_render_options(self, palette: list[str]) -> PdfBundleRenderOptions:
        return PdfBundleRenderOptions(
            flag_colours=palette,
            physical_flag_markers=not bool(self.disable_physical_flag_markers_var.get()),
            number_fill_opacity=1.0,
        )

    def create_authorities_index(self) -> None:
        if not self.pdf_items:
            messagebox.showwarning("No PDFs", "Please add one or more PDFs first.")
            return
        output_path_str = filedialog.asksaveasfilename(
            title="Save authorities index as",
            defaultextension=".docx",
            filetypes=[("Word documents", "*.docx")],
            initialfile=(
                matter_output_filename(self.active_matter, "AUTHORITIES_INDEX", ".docx")
                if self.active_matter
                else "authorities_index.docx"
            ),
        )
        if not output_path_str:
            return
        output_path = Path(output_path_str)
        self._update_status("Creating authorities index...")
        self.update_idletasks()
        try:
            if self.active_matter:
                header = simpledialog.askstring(
                    title="Document header",
                    prompt="Document header:",
                    initialvalue="AUTHORITIES BUNDLE",
                    parent=self,
                )
                if header is None:
                    return
                create_matter_authorities_index_docx_from_rows(
                    self.active_matter,
                    DocumentHeaderInput(header.strip() or "AUTHORITIES BUNDLE"),
                    self._rows_for_output(header_title=header.strip() or "AUTHORITIES BUNDLE"),
                    output_path,
                    font_name=self.index_font_var.get(),
                )
            else:
                create_authorities_index_docx_from_rows(
                    self._rows_for_output(),
                    output_path,
                    font_name=self.index_font_var.get(),
                )
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Failed", f"Could not create authorities index: {exc}")
            self._update_status("Failed to create authorities index.")
            return
        self._update_status(f"Created authorities index: {output_path}")
        messagebox.showinfo("Complete", f"Created authorities index: {output_path}")


def main() -> None:
    app = PDFCombinerNumbererTOCIndexApp()
    app.mainloop()
