from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from huguenot.domain import DocumentHeaderInput, Matter, PartySide, PDFItem, party_label

from .authorities_index import get_index_entries


class ReportLabIndexRenderer:
    """Lower-fidelity pure-Python fallback renderer for the matter index PDF."""

    def render_pdf(
        self,
        matter: Matter,
        document_header: DocumentHeaderInput,
        pdf_items: list[PDFItem],
        output_path: Path,
        *,
        start_page: int = 1,
    ) -> list[dict[str, int | float]]:
        width, height = A4
        c = canvas.Canvas(str(output_path), pagesize=A4)
        links: list[dict[str, int | float]] = []

        y = height - 24 * mm
        c.setFont("Times-Bold", 12)
        c.drawCentredString(width / 2, y, matter.court.name.upper())
        y -= 7 * mm
        if matter.court.header_line_2:
            c.setFont("Times-Roman", 12)
            c.drawCentredString(width / 2, y, matter.court.header_line_2.upper())
            y -= 9 * mm

        c.setFont("Times-Roman", 11)
        case_line = f"CASE NO: {matter.case_number}" if matter.case_number else "CASE NO:"
        c.drawRightString(width - 24 * mm, y, case_line)
        y -= 8 * mm
        c.drawString(24 * mm, y, "In the matter between:")
        y -= 10 * mm

        y = self._draw_parties(c, matter, y, width)
        y -= 4 * mm
        c.setFont("Times-Bold", 12)
        c.drawCentredString(width / 2, y, document_header.title.upper())
        c.line(45 * mm, y - 2, width - 45 * mm, y - 2)
        y -= 12 * mm

        page_index = 0
        y = self._draw_table_header(c, y, width)
        for number, item, page_range in get_index_entries(pdf_items, start_page=start_page):
            if y < 28 * mm:
                c.showPage()
                page_index += 1
                y = height - 24 * mm
                y = self._draw_table_header(c, y, width)

            row_top = y
            row_bottom = y - 11 * mm
            c.setFont("Times-Roman", 10)
            c.drawString(27 * mm, y - 7 * mm, str(number))
            c.drawString(43 * mm, y - 7 * mm, item.title[:95])
            range_text = page_range.display()
            c.drawCentredString(width - 32 * mm, y - 7 * mm, range_text)
            self._draw_row_box(c, row_top, row_bottom, width)

            links.append(
                {
                    "index_page": page_index,
                    "target_page": page_range.start - start_page,
                    "x0": width - 45 * mm,
                    "y0": height - row_top,
                    "x1": width - 19 * mm,
                    "y1": height - row_bottom,
                }
            )
            y = row_bottom

        c.save()
        return links

    def _draw_parties(self, c: canvas.Canvas, matter: Matter, y: float, width: float) -> float:
        c.setFont("Times-Bold", 11)
        bringing = matter.bringing_parties
        opposing = matter.opposing_parties
        for party in bringing:
            c.drawString(24 * mm, y, party.name.upper())
            c.setFont("Times-Roman", 11)
            c.drawRightString(
                width - 24 * mm,
                y,
                party_label(matter.proceeding_type, PartySide.BRINGING, party.position, len(bringing)),
            )
            c.setFont("Times-Bold", 11)
            y -= 7 * mm

        c.setFont("Times-Roman", 11)
        y -= 3 * mm
        c.drawString(24 * mm, y, "and")
        y -= 10 * mm
        c.setFont("Times-Bold", 11)

        for party in opposing:
            c.drawString(24 * mm, y, party.name.upper())
            c.setFont("Times-Roman", 11)
            c.drawRightString(
                width - 24 * mm,
                y,
                party_label(matter.proceeding_type, PartySide.OPPOSING, party.position, len(opposing)),
            )
            c.setFont("Times-Bold", 11)
            y -= 7 * mm
        return y

    def _draw_table_header(self, c: canvas.Canvas, y: float, width: float) -> float:
        c.setStrokeColor(colors.black)
        c.setFillColor(colors.whitesmoke)
        c.rect(24 * mm, y - 10 * mm, width - 48 * mm, 10 * mm, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Times-Bold", 10)
        c.drawString(27 * mm, y - 7 * mm, "No")
        c.drawString(43 * mm, y - 7 * mm, "Item")
        c.drawCentredString(width - 32 * mm, y - 7 * mm, "Page no")
        return y - 10 * mm

    def _draw_row_box(self, c: canvas.Canvas, row_top: float, row_bottom: float, width: float) -> None:
        c.setStrokeColor(colors.black)
        c.line(24 * mm, row_bottom, width - 24 * mm, row_bottom)
        c.line(38 * mm, row_top, 38 * mm, row_bottom)
        c.line(width - 50 * mm, row_top, width - 50 * mm, row_bottom)
        c.line(24 * mm, row_top, 24 * mm, row_bottom)
        c.line(width - 24 * mm, row_top, width - 24 * mm, row_bottom)
