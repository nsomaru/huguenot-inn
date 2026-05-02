from __future__ import annotations

from pathlib import Path

import fitz
from docx import Document
from docx.document import Document as WordDocument
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from huguenot.domain import DocumentHeaderInput, Matter, PageRange, PartySide, PDFItem, party_label


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = tr_pr.find(qn("w:tblHeader"))
    if tbl_header is None:
        tbl_header = OxmlElement("w:tblHeader")
        tr_pr.append(tbl_header)
    tbl_header.set(qn("w:val"), "true")


def set_cell_text(cell, text: str, bold: bool = False, align=None) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    if align is not None:
        paragraph.alignment = align
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.size = Pt(10)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP


def get_pdf_page_count(path: Path) -> int:
    source = fitz.open(path)
    try:
        return source.page_count
    finally:
        source.close()


def get_index_entries(pdf_items: list[PDFItem], *, start_page: int = 1) -> list[tuple[int, PDFItem, PageRange]]:
    entries: list[tuple[int, PDFItem, PageRange]] = []
    current_page = start_page
    for number, item in enumerate(pdf_items, start=1):
        try:
            page_count = max(1, get_pdf_page_count(item.path))
        except Exception:
            page_count = 1
        page_range = PageRange(current_page, current_page + page_count - 1)
        entries.append((number, item, page_range))
        current_page += page_count
    return entries


def configure_document(doc: WordDocument) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)


def add_authorities_table(doc: WordDocument, entries: list[tuple[int, PDFItem, PageRange]]) -> None:
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.columns[0].width = Inches(0.55)
    table.columns[1].width = Inches(5.7)
    table.columns[2].width = Inches(1.25)

    header_cells = table.rows[0].cells
    set_cell_text(header_cells[0], "No", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    set_cell_text(header_cells[1], "Item", bold=True)
    set_cell_text(header_cells[2], "Page no", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    set_repeat_table_header(table.rows[0])

    for number, item, page_range in entries:
        row_cells = table.add_row().cells
        set_cell_text(row_cells[0], str(number), align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_text(row_cells[1], item.title)
        set_cell_text(row_cells[2], page_range.display(), align=WD_ALIGN_PARAGRAPH.CENTER)


def create_authorities_index_docx(pdf_items: list[PDFItem], output_path: Path) -> None:
    doc = Document()
    configure_document(doc)

    heading = doc.add_heading("Index of Authorities", level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note = doc.add_paragraph(
        "Generated automatically from the selected PDFs. "
        "Page numbers refer to the page numbering of the combined bundle."
    )
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()
    add_authorities_table(doc, get_index_entries(pdf_items))
    doc.save(str(output_path))


def add_centered_paragraph(doc: WordDocument, text: str, *, bold: bool = False, underline: bool = False) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    run.bold = bold
    run.underline = underline
    run.font.name = "Times New Roman"
    run.font.size = Pt(12 if not bold else 13)


def add_party_line(doc: WordDocument, name: str, label: str) -> None:
    paragraph = doc.add_paragraph()
    left = paragraph.add_run(name.upper())
    left.bold = True
    left.font.name = "Times New Roman"
    left.font.size = Pt(12)
    paragraph.add_run("\t\t\t")
    right = paragraph.add_run(label)
    right.font.name = "Times New Roman"
    right.font.size = Pt(12)


def create_matter_authorities_index_docx(
    matter: Matter,
    document_header: DocumentHeaderInput,
    pdf_items: list[PDFItem],
    output_path: Path,
    *,
    start_page: int = 1,
) -> None:
    doc = Document()
    configure_document(doc)

    add_centered_paragraph(doc, matter.court.name.upper(), bold=True)
    if matter.court.header_line_2:
        add_centered_paragraph(doc, matter.court.header_line_2.upper())

    doc.add_paragraph()
    case_line = f"CASE NO: {matter.case_number}" if matter.case_number else "CASE NO:"
    case_paragraph = doc.add_paragraph(case_line)
    case_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_paragraph("In the matter between:")
    doc.add_paragraph()

    bringing = matter.bringing_parties
    opposing = matter.opposing_parties
    for party in bringing:
        add_party_line(
            doc,
            party.name,
            party_label(matter.proceeding_type, PartySide.BRINGING, party.position, len(bringing)),
        )

    doc.add_paragraph()
    doc.add_paragraph("and")
    doc.add_paragraph()

    for party in opposing:
        add_party_line(
            doc,
            party.name,
            party_label(matter.proceeding_type, PartySide.OPPOSING, party.position, len(opposing)),
        )

    doc.add_paragraph()
    add_centered_paragraph(doc, document_header.title.upper(), bold=True, underline=True)
    doc.add_paragraph()
    add_authorities_table(doc, get_index_entries(pdf_items, start_page=start_page))
    doc.save(str(output_path))
