from __future__ import annotations

import tempfile
import tkinter as tk
import traceback
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, cast

from tkinterdnd2 import DND_FILES, TkinterDnD

from huguenot.application import MatterService
from huguenot.documents import (
    LibreOfficeConverter,
    create_authorities_index_docx,
    create_matter_authorities_index_docx,
    render_matter_index_pdf,
)
from huguenot.domain import DocumentHeaderInput, Matter, PDFItem, ProceedingType
from huguenot.pdf import POSITIONS, combine_number_and_add_toc, combine_with_front_index, detect_authority_index_item
from huguenot.persistence import SQLiteCourtRepository, SQLiteMatterRepository, create_app_database


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


class PDFCombinerNumbererTOCIndexApp(TkinterDnD.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PDF Combiner + Page Numberer + Authorities Index")
        self.geometry("900x570")
        self.minsize(800, 500)

        database = create_app_database()
        court_repository = SQLiteCourtRepository(database)
        matter_repository = SQLiteMatterRepository(database)
        self.matter_service = MatterService(matter_repository, court_repository)
        self.active_matter = self.matter_service.get_last_active_matter()

        self.pdf_items: list[PDFItem] = []
        self.position_var = tk.StringVar(value="Bottom centre")
        self.font_size_var = tk.IntVar(value=15)
        self.margin_var = tk.IntVar(value=28)
        self._build_ui()
        self._update_status()

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

        main = ttk.Frame(outer)
        main.pack(fill="both", expand=True)
        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)
        self.tree = ttk.Treeview(left, columns=("order", "title"), show="headings", selectmode="browse")
        self.tree.heading("order", text="#")
        self.tree.heading("title", text="PDF ToC entry / index item")
        self.tree.column("order", width=45, anchor="center", stretch=False)
        self.tree.column("title", width=650, anchor="w", stretch=True)
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
        ttk.Button(buttons, text="Edit title", command=self.edit_selected_title).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Auto-detect title", command=self.auto_detect_selected_title).pack(
            fill="x", pady=(0, 6)
        )
        ttk.Button(buttons, text="Move up", command=self.move_up).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Move down", command=self.move_down).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Remove", command=self.remove_selected).pack(fill="x", pady=(0, 6))
        ttk.Button(buttons, text="Clear", command=self.clear_list).pack(fill="x", pady=(0, 18))
        ttk.Button(buttons, text="Create combined numbered PDF", command=self.create_combined_pdf).pack(
            fill="x", pady=(0, 6)
        )
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
        file_menu.add_command(label="Exit", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu)

    def _update_status(self, message: str | None = None) -> None:
        matter_text = f"Active matter: {self.active_matter.display_name}" if self.active_matter else "No active matter"
        pdf_text = f"{len(self.pdf_items)} PDF(s)"
        base = f"{matter_text} | {pdf_text}"
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
        return [Path(p) for p in raw_paths if Path(p).is_file() and Path(p).suffix.lower() == ".pdf"]

    def add_paths(self, paths: list[Path]) -> None:
        existing = {item.path.resolve() for item in self.pdf_items}
        added = 0
        for path in paths:
            resolved = path.resolve()
            if resolved in existing:
                continue
            self.pdf_items.append(PDFItem(path=path, title=detect_authority_index_item(path)))
            existing.add(resolved)
            added += 1
        self.refresh_tree()
        self._update_status(f"Added {added} PDF(s)." if added else "No new PDFs added.")

    def refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for index, item in enumerate(self.pdf_items, start=1):
            self.tree.insert("", tk.END, iid=str(index - 1), values=(index, item.title))

    def selected_index(self) -> int | None:
        selection = self.tree.selection()
        return None if not selection else int(selection[0])

    def on_drop(self, event) -> None:
        pdfs = self.parse_drop_files(event.data)
        if not pdfs:
            messagebox.showwarning("No PDFs", "Please drop one or more PDF files.")
            return
        self.add_paths(pdfs)

    def add_pdfs_dialog(self) -> None:
        selected = filedialog.askopenfilenames(title="Choose PDFs", filetypes=[("PDF files", "*.pdf")])
        if selected:
            self.add_paths([Path(p) for p in selected])

    def on_tree_double_click(self, event) -> None:
        if self.tree.identify("region", event.x, event.y) == "cell" and self.tree.identify_column(event.x) == "#2":
            self.edit_selected_title()

    def edit_selected_title(self) -> None:
        index = self.selected_index()
        if index is None:
            messagebox.showwarning("Nothing selected", "Please select a PDF first.")
            return
        item = self.pdf_items[index]
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
        self.pdf_items[index] = replace(item, title=new_title)
        self.refresh_tree()
        self.tree.selection_set(str(index))
        self._update_status(f"Renamed title to: {new_title}")

    def auto_detect_selected_title(self) -> None:
        index = self.selected_index()
        if index is None:
            messagebox.showwarning("Nothing selected", "Please select a PDF first.")
            return
        item = self.pdf_items[index]
        self.pdf_items[index] = replace(item, title=detect_authority_index_item(item.path))
        self.refresh_tree()
        self.tree.selection_set(str(index))
        self._update_status(f"Auto-detected title: {self.pdf_items[index].title}")

    def move_up(self) -> None:
        index = self.selected_index()
        if index is None or index == 0:
            return
        self.pdf_items[index - 1], self.pdf_items[index] = self.pdf_items[index], self.pdf_items[index - 1]
        self.refresh_tree()
        self.tree.selection_set(str(index - 1))

    def move_down(self) -> None:
        index = self.selected_index()
        if index is None or index >= len(self.pdf_items) - 1:
            return
        self.pdf_items[index + 1], self.pdf_items[index] = self.pdf_items[index], self.pdf_items[index + 1]
        self.refresh_tree()
        self.tree.selection_set(str(index + 1))

    def remove_selected(self) -> None:
        index = self.selected_index()
        if index is None:
            return
        removed = self.pdf_items.pop(index)
        self.refresh_tree()
        self._update_status(f"Removed {removed.path.name}.")

    def clear_list(self) -> None:
        self.pdf_items.clear()
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
            initialfile="matter_authorities_bundle.pdf",
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
                converter = LibreOfficeConverter()
                used_libreoffice, links = render_matter_index_pdf(
                    self.active_matter,
                    DocumentHeaderInput(header.strip() or "AUTHORITIES BUNDLE"),
                    self.pdf_items,
                    index_pdf,
                    converter=converter,
                )
                if not used_libreoffice:
                    messagebox.showinfo(
                        "LibreOffice not available",
                        "LibreOffice was not available for high-fidelity conversion. "
                        "Using the lower-fidelity pure-Python PDF renderer.",
                    )
                combine_with_front_index(
                    self.pdf_items,
                    index_pdf,
                    links,
                    output_path,
                    self.position_var.get(),
                    int(self.font_size_var.get()),
                    int(self.margin_var.get()),
                )
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Failed", f"Could not create matter bundle PDF: {exc}")
            self._update_status("Failed to create matter bundle PDF.")
            return
        self._update_status(f"Created: {output_path}")
        messagebox.showinfo("Complete", f"Created: {output_path}")

    def _create_plain_pdf_bundle(self, *, initialfile: str) -> None:
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
            combine_number_and_add_toc(
                self.pdf_items,
                output_path,
                self.position_var.get(),
                int(self.font_size_var.get()),
                int(self.margin_var.get()),
            )
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Failed", f"Could not create PDF: {exc}")
            self._update_status("Failed to create combined PDF.")
            return
        self._update_status(f"Created: {output_path}")
        messagebox.showinfo("Complete", f"Created: {output_path}")

    def create_authorities_index(self) -> None:
        if not self.pdf_items:
            messagebox.showwarning("No PDFs", "Please add one or more PDFs first.")
            return
        output_path_str = filedialog.asksaveasfilename(
            title="Save authorities index as",
            defaultextension=".docx",
            filetypes=[("Word documents", "*.docx")],
            initialfile="authorities_index.docx",
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
                create_matter_authorities_index_docx(
                    self.active_matter,
                    DocumentHeaderInput(header.strip() or "AUTHORITIES BUNDLE"),
                    self.pdf_items,
                    output_path,
                )
            else:
                create_authorities_index_docx(self.pdf_items, output_path)
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
