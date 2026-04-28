#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

import fitz  # PyMuPDF
from tkinterdnd2 import DND_FILES, TkinterDnD


POSITIONS = [
    "Bottom centre",
    "Bottom right",
    "Bottom left",
    "Top centre",
    "Top right",
    "Top left",
]


@dataclass
class PDFItem:
    path: Path
    title: str


def get_number_box(
    page_rect: fitz.Rect,
    position: str,
    box_width: float,
    box_height: float,
    margin: float,
) -> fitz.Rect:
    position_lower = position.lower()

    if "left" in position_lower:
        x0 = page_rect.x0 + margin
    elif "right" in position_lower:
        x0 = page_rect.x1 - margin - box_width
    else:
        x0 = page_rect.x0 + (page_rect.width - box_width) / 2

    if "top" in position_lower:
        y0 = page_rect.y0 + margin
    else:
        y0 = page_rect.y1 - margin - box_height

    return fitz.Rect(x0, y0, x0 + box_width, y0 + box_height)


def draw_page_number(
    page: fitz.Page,
    number: int,
    position: str,
    font_size: int = 15,
    margin: int = 28,
) -> None:
    """
    Draws a clean, readable page number:
    - Helvetica Bold
    - centred in a small white backing box
    - subtle border
    """

    text = str(number)
    page_rect = page.rect

    text_width = fitz.get_text_length(
        text,
        fontname="hebo",
        fontsize=font_size,
    )

    box_width = max(34, text_width + 18)
    box_height = font_size + 12

    box = get_number_box(
        page_rect=page_rect,
        position=position,
        box_width=box_width,
        box_height=box_height,
        margin=margin,
    )

    page.draw_rect(
        box,
        color=(0, 0, 0),
        fill=(1, 1, 1),
        width=0.6,
        fill_opacity=0.85,
        stroke_opacity=0.65,
    )

    page.insert_textbox(
        box,
        text,
        fontsize=font_size,
        fontname="hebo",
        color=(0, 0, 0),
        align=fitz.TEXT_ALIGN_CENTER,
    )


def combine_number_and_add_toc(
    pdf_items: list[PDFItem],
    output_path: Path,
    position: str,
    font_size: int,
    margin: int,
) -> None:
    if not pdf_items:
        raise ValueError("No PDFs selected.")

    output_doc = fitz.open()

    # PyMuPDF TOC entries are:
    # [level, title, page_number]
    #
    # page_number is 1-based.
    toc: list[list[int | str]] = []

    try:
        current_start_page = 1

        for item in pdf_items:
            source = fitz.open(item.path)
            try:
                if source.page_count == 0:
                    continue

                toc_title = item.title.strip() or item.path.stem

                toc.append([1, toc_title, current_start_page])

                output_doc.insert_pdf(source)
                current_start_page += source.page_count
            finally:
                source.close()

        for index, page in enumerate(output_doc, start=1):
            draw_page_number(
                page=page,
                number=index,
                position=position,
                font_size=font_size,
                margin=margin,
            )

        if toc:
            output_doc.set_toc(toc)

        output_doc.save(output_path, garbage=4, deflate=True)
    finally:
        output_doc.close()


class PDFCombinerNumbererTOCApp(TkinterDnD.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("PDF Combiner + Page Numberer + TOC")
        self.geometry("850x520")
        self.minsize(760, 460)

        self.pdf_items: list[PDFItem] = []

        self.position_var = tk.StringVar(value="Bottom centre")
        self.font_size_var = tk.IntVar(value=15)
        self.margin_var = tk.IntVar(value=28)

        self._build_ui()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(
            outer,
            text="Drag PDFs here, edit TOC names, then create one numbered PDF",
            font=("TkDefaultFont", 15, "bold"),
        )
        title.pack(anchor="w", pady=(0, 12))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 12))

        ttk.Label(controls, text="Number position:").grid(row=0, column=0, sticky="w")

        position_box = ttk.Combobox(
            controls,
            textvariable=self.position_var,
            values=POSITIONS,
            state="readonly",
            width=20,
        )
        position_box.grid(row=0, column=1, sticky="w", padx=(8, 24))

        ttk.Label(controls, text="Font size:").grid(row=0, column=2, sticky="w")

        font_spin = ttk.Spinbox(
            controls,
            from_=10,
            to=28,
            textvariable=self.font_size_var,
            width=5,
        )
        font_spin.grid(row=0, column=3, sticky="w", padx=(8, 24))

        ttk.Label(controls, text="Margin:").grid(row=0, column=4, sticky="w")

        margin_spin = ttk.Spinbox(
            controls,
            from_=10,
            to=100,
            textvariable=self.margin_var,
            width=5,
        )
        margin_spin.grid(row=0, column=5, sticky="w", padx=(8, 0))

        main = ttk.Frame(outer)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        self.tree = ttk.Treeview(
            left,
            columns=("order", "title", "file"),
            show="headings",
            selectmode="browse",
        )

        self.tree.heading("order", text="#")
        self.tree.heading("title", text="TOC entry")
        self.tree.heading("file", text="PDF file")

        self.tree.column("order", width=45, anchor="center", stretch=False)
        self.tree.column("title", width=300, anchor="w", stretch=True)
        self.tree.column("file", width=360, anchor="w", stretch=True)

        self.tree.pack(fill="both", expand=True)

        self.tree.drop_target_register(DND_FILES)
        self.tree.dnd_bind("<<Drop>>", self.on_drop)

        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Return>", lambda event: self.edit_selected_title())

        hint = ttk.Label(
            left,
            text="Double-click a TOC entry to rename it. The PDF bookmarks will use these names.",
        )
        hint.pack(anchor="w", pady=(6, 0))

        buttons = ttk.Frame(main)
        buttons.pack(side="right", fill="y", padx=(12, 0))

        ttk.Button(buttons, text="Add PDFs", command=self.add_pdfs_dialog).pack(
            fill="x", pady=(0, 6)
        )

        ttk.Button(buttons, text="Edit TOC name", command=self.edit_selected_title).pack(
            fill="x", pady=(0, 6)
        )

        ttk.Button(buttons, text="Move up", command=self.move_up).pack(
            fill="x", pady=(0, 6)
        )

        ttk.Button(buttons, text="Move down", command=self.move_down).pack(
            fill="x", pady=(0, 6)
        )

        ttk.Button(buttons, text="Remove", command=self.remove_selected).pack(
            fill="x", pady=(0, 6)
        )

        ttk.Button(buttons, text="Clear", command=self.clear_list).pack(
            fill="x", pady=(0, 18)
        )

        ttk.Button(
            buttons,
            text="Create combined numbered PDF",
            command=self.create_combined_pdf,
        ).pack(fill="x")

        self.status = ttk.Label(
            outer,
            text="No PDFs added yet.",
            anchor="w",
        )
        self.status.pack(fill="x", pady=(12, 0))

    def parse_drop_files(self, data: str) -> list[Path]:
        raw_paths = self.tk.splitlist(data)

        return [
            Path(p)
            for p in raw_paths
            if Path(p).is_file() and Path(p).suffix.lower() == ".pdf"
        ]

    def add_paths(self, paths: list[Path]) -> None:
        existing = {item.path.resolve() for item in self.pdf_items}

        added = 0

        for path in paths:
            resolved = path.resolve()

            if resolved in existing:
                continue

            self.pdf_items.append(
                PDFItem(
                    path=path,
                    title=path.stem,
                )
            )

            existing.add(resolved)
            added += 1

        self.refresh_tree()

        if added:
            self.status.config(
                text=f"Added {added} PDF(s). Total: {len(self.pdf_items)}."
            )
        else:
            self.status.config(text="No new PDFs added.")

    def refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())

        for index, item in enumerate(self.pdf_items, start=1):
            self.tree.insert(
                "",
                tk.END,
                iid=str(index - 1),
                values=(
                    index,
                    item.title,
                    item.path.name,
                ),
            )

    def selected_index(self) -> int | None:
        selection = self.tree.selection()

        if not selection:
            return None

        return int(selection[0])

    def on_drop(self, event) -> None:
        pdfs = self.parse_drop_files(event.data)

        if not pdfs:
            messagebox.showwarning("No PDFs", "Please drop one or more PDF files.")
            return

        self.add_paths(pdfs)

    def add_pdfs_dialog(self) -> None:
        selected = filedialog.askopenfilenames(
            title="Choose PDFs",
            filetypes=[("PDF files", "*.pdf")],
        )

        if selected:
            self.add_paths([Path(p) for p in selected])

    def on_tree_double_click(self, event) -> None:
        region = self.tree.identify("region", event.x, event.y)
        column = self.tree.identify_column(event.x)

        # Only edit the TOC title column.
        if region == "cell" and column == "#2":
            self.edit_selected_title()

    def edit_selected_title(self) -> None:
        index = self.selected_index()

        if index is None:
            messagebox.showwarning("Nothing selected", "Please select a PDF first.")
            return

        item = self.pdf_items[index]

        new_title = simpledialog.askstring(
            title="Edit TOC entry",
            prompt="TOC entry name:",
            initialvalue=item.title,
            parent=self,
        )

        if new_title is None:
            return

        new_title = new_title.strip()

        if not new_title:
            messagebox.showwarning(
                "Blank title",
                "The TOC entry cannot be blank.",
            )
            return

        item.title = new_title
        self.refresh_tree()
        self.tree.selection_set(str(index))
        self.status.config(text=f"Renamed TOC entry to: {new_title}")

    def move_up(self) -> None:
        index = self.selected_index()

        if index is None or index == 0:
            return

        self.pdf_items[index - 1], self.pdf_items[index] = (
            self.pdf_items[index],
            self.pdf_items[index - 1],
        )

        self.refresh_tree()
        self.tree.selection_set(str(index - 1))

    def move_down(self) -> None:
        index = self.selected_index()

        if index is None or index >= len(self.pdf_items) - 1:
            return

        self.pdf_items[index + 1], self.pdf_items[index] = (
            self.pdf_items[index],
            self.pdf_items[index + 1],
        )

        self.refresh_tree()
        self.tree.selection_set(str(index + 1))

    def remove_selected(self) -> None:
        index = self.selected_index()

        if index is None:
            return

        removed = self.pdf_items.pop(index)

        self.refresh_tree()
        self.status.config(text=f"Removed {removed.path.name}.")

    def clear_list(self) -> None:
        self.pdf_items.clear()
        self.refresh_tree()
        self.status.config(text="List cleared.")

    def create_combined_pdf(self) -> None:
        if not self.pdf_items:
            messagebox.showwarning("No PDFs", "Please add one or more PDFs first.")
            return

        output_path_str = filedialog.asksaveasfilename(
            title="Save combined numbered PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="combined_numbered.pdf",
        )

        if not output_path_str:
            return

        output_path = Path(output_path_str)

        try:
            combine_number_and_add_toc(
                pdf_items=self.pdf_items,
                output_path=output_path,
                position=self.position_var.get(),
                font_size=int(self.font_size_var.get()),
                margin=int(self.margin_var.get()),
            )
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Failed", f"Could not create PDF:\n\n{exc}")
            self.status.config(text="Failed to create combined PDF.")
            return

        self.status.config(text=f"Created: {output_path}")
        messagebox.showinfo("Complete", f"Created:\n\n{output_path}")


def main() -> None:
    app = PDFCombinerNumbererTOCApp()
    app.mainloop()


if __name__ == "__main__":
    main()
