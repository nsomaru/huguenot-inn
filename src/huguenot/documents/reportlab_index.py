from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from huguenot.domain import (
    BundleIndexEntry,
    BundleIndexRow,
    DocumentHeaderInput,
    IndexSeparatorEntry,
    Matter,
    PartySide,
    PDFItem,
    normalize_flag_colour,
    party_label,
)
from huguenot.domain.legal_titles import normalize_legal_display_title

from .authorities_index import get_index_entries
from .settings import FontResolver, ResolvedIndexFont

PARTY_TABLE_LEFT = 24 * mm
PARTY_TABLE_RIGHT_MARGIN = 24 * mm
HEADING_RULE_GAP = 7.25 * mm


class ReportLabIndexRenderer:
    """Lower-fidelity pure-Python fallback renderer for the matter index PDF."""

    def __init__(self, font: ResolvedIndexFont | None = None) -> None:
        self.font = font or FontResolver().resolve()

    def render_pdf(
        self,
        matter: Matter,
        document_header: DocumentHeaderInput,
        pdf_items: list[PDFItem],
        output_path: Path,
        *,
        start_page: int = 1,
        index_entries: Sequence[BundleIndexEntry] | None = None,
        index_rows: Sequence[BundleIndexRow] | None = None,
        colour_page_ranges: bool = False,
    ) -> list[dict[str, int | float]]:
        entries = index_rows if index_rows is not None else index_entries
        entries = entries if entries is not None else get_index_entries(pdf_items, start_page=start_page)
        return self._render_pdf_rows(
            matter,
            document_header,
            entries,
            output_path,
            start_page=start_page,
            colour_page_ranges=colour_page_ranges,
        )

    def render_pdf_from_rows(
        self,
        matter: Matter,
        document_header: DocumentHeaderInput,
        index_rows: Sequence[BundleIndexRow],
        output_path: Path,
        *,
        start_page: int = 1,
        colour_page_ranges: bool = False,
    ) -> list[dict[str, int | float]]:
        return self._render_pdf_rows(
            matter,
            document_header,
            index_rows,
            output_path,
            start_page=start_page,
            colour_page_ranges=colour_page_ranges,
        )

    def _render_pdf_rows(
        self,
        matter: Matter,
        document_header: DocumentHeaderInput,
        entries: Sequence[BundleIndexRow],
        output_path: Path,
        *,
        start_page: int,
        colour_page_ranges: bool,
    ) -> list[dict[str, int | float]]:
        width, height = A4
        c = canvas.Canvas(str(output_path), pagesize=A4)
        links: list[dict[str, int | float]] = []

        y = height - 24 * mm
        c.setFont(self.font.reportlab_bold, 12)
        c.drawCentredString(width / 2, y, matter.court.name.upper())
        y -= 7 * mm
        if matter.court.header_line_2:
            c.setFont(self.font.reportlab_regular, 12)
            c.drawCentredString(width / 2, y, matter.court.header_line_2.upper())
            y -= 9 * mm

        c.setFont(self.font.reportlab_bold, 11)
        case_line = f"CASE NO: {matter.case_number}" if matter.case_number else "CASE NO:"
        c.drawRightString(width - 24 * mm, y, case_line)
        y -= 8 * mm
        c.setFont(self.font.reportlab_regular, 11)
        c.drawString(24 * mm, y, "In the matter between:")
        y -= 10 * mm

        y = self._draw_parties(c, matter, y, width)
        y -= 8 * mm
        c.setFont(self.font.reportlab_bold, 12)
        c.line(PARTY_TABLE_LEFT, y + HEADING_RULE_GAP, width - PARTY_TABLE_RIGHT_MARGIN, y + HEADING_RULE_GAP)
        c.drawCentredString(width / 2, y, document_header.title.upper())
        c.line(PARTY_TABLE_LEFT, y - HEADING_RULE_GAP, width - PARTY_TABLE_RIGHT_MARGIN, y - HEADING_RULE_GAP)
        y -= 18 * mm

        page_index = 0
        y = self._draw_table_header(c, y, width)
        for entry in entries:
            if isinstance(entry, IndexSeparatorEntry):
                row_height = 11 * mm
                if y - row_height < 28 * mm:
                    c.showPage()
                    page_index += 1
                    y = height - 24 * mm
                    y = self._draw_table_header(c, y, width)
                row_top = y
                row_bottom = y - row_height
                c.setFont(self.font.reportlab_bold, 10)
                c.drawCentredString(width / 2, y - 7 * mm, entry.title)
                self._draw_row_box(c, row_top, row_bottom, width)
                y = row_bottom
                continue
            number = entry.item_number
            item = entry.item
            page_range = entry.page_range
            item_title = normalize_legal_display_title(item.title)
            lines = self._wrap_text(item_title, width - 100 * mm, self.font.reportlab_regular, 10)
            row_height = max(11 * mm, (len(lines) * 4.4 + 5) * mm)
            if y - row_height < 28 * mm:
                c.showPage()
                page_index += 1
                y = height - 24 * mm
                y = self._draw_table_header(c, y, width)

            row_top = y
            row_bottom = y - row_height
            c.setFont(self.font.reportlab_regular, 10)
            c.drawString(27 * mm, y - 7 * mm, str(number))
            text_y = y - 7 * mm
            for line_index, line in enumerate(lines):
                x = 43 * mm + (4 * mm if line_index else 0)
                c.drawString(x, text_y, line)
                text_y -= 4.4 * mm
            range_text = page_range.display()
            c.drawCentredString(width - 32 * mm, y - 7 * mm, range_text)
            self._draw_row_box(c, row_top, row_bottom, width)
            if colour_page_ranges and entry.flag_colour:
                self._draw_page_range_right_border(c, row_top, row_bottom, width, entry.flag_colour)

            links.append(
                {
                    "index_page": page_index,
                    "target_page": page_range.start - start_page,
                    "x0": 24 * mm,
                    "y0": height - row_top,
                    "x1": width - 24 * mm,
                    "y1": height - row_bottom,
                }
            )
            y = row_bottom

        c.save()
        return links

    def _draw_parties(self, c: canvas.Canvas, matter: Matter, y: float, width: float) -> float:
        c.setFont(self.font.reportlab_bold, 11)
        bringing = matter.bringing_parties
        opposing = matter.opposing_parties
        for party in bringing:
            c.drawString(PARTY_TABLE_LEFT, y, party.name.upper())
            c.setFont(self.font.reportlab_regular, 11)
            self._draw_party_label(
                c,
                width - PARTY_TABLE_RIGHT_MARGIN,
                y,
                party_label(matter.proceeding_type, PartySide.BRINGING, party.position, len(bringing)),
            )
            c.setFont(self.font.reportlab_bold, 11)
            y -= 7 * mm

        c.setFont(self.font.reportlab_regular, 11)
        y -= 3 * mm
        c.drawString(PARTY_TABLE_LEFT, y, "and")
        y -= 10 * mm
        c.setFont(self.font.reportlab_bold, 11)

        for party in opposing:
            c.drawString(PARTY_TABLE_LEFT, y, party.name.upper())
            c.setFont(self.font.reportlab_regular, 11)
            self._draw_party_label(
                c,
                width - PARTY_TABLE_RIGHT_MARGIN,
                y,
                party_label(matter.proceeding_type, PartySide.OPPOSING, party.position, len(opposing)),
            )
            c.setFont(self.font.reportlab_bold, 11)
            y -= 7 * mm
        return y

    def _draw_party_label(self, c: canvas.Canvas, x_right: float, y: float, label: str) -> None:
        segments = self._ordinal_segments(label)
        if segments is None:
            c.drawRightString(x_right, y, label)
            return

        number, suffix, role = segments
        number_font_size = 11
        suffix_font_size = 7
        role_font_size = 11
        total_width = (
            stringWidth(number, self.font.reportlab_regular, number_font_size)
            + stringWidth(suffix, self.font.reportlab_regular, suffix_font_size)
            + stringWidth(role, self.font.reportlab_regular, role_font_size)
        )
        x = x_right - total_width
        c.setFont(self.font.reportlab_regular, number_font_size)
        c.drawString(x, y, number)
        x += stringWidth(number, self.font.reportlab_regular, number_font_size)
        c.setFont(self.font.reportlab_regular, suffix_font_size)
        c.drawString(x, y + 3, suffix)
        x += stringWidth(suffix, self.font.reportlab_regular, suffix_font_size)
        c.setFont(self.font.reportlab_regular, role_font_size)
        c.drawString(x, y, role)

    def _ordinal_segments(self, label: str) -> tuple[str, str, str] | None:
        if not label or not label[0].isdigit():
            return None
        number = "".join(ch for ch in label if ch.isdigit())
        suffix_and_role = label[len(number) :]
        suffix = suffix_and_role.split(" ", 1)[0]
        role = suffix_and_role[len(suffix) :]
        if not suffix:
            return None
        return number, suffix, role

    def _draw_table_header(self, c: canvas.Canvas, y: float, width: float) -> float:
        c.setStrokeColor(colors.black)
        c.setFillColor(colors.whitesmoke)
        c.rect(24 * mm, y - 10 * mm, width - 48 * mm, 10 * mm, fill=1)
        c.setFillColor(colors.black)
        c.setFont(self.font.reportlab_bold, 10)
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

    def _draw_page_range_right_border(
        self, c: canvas.Canvas, row_top: float, row_bottom: float, width: float, colour_hex: str
    ) -> None:
        c.saveState()
        c.setStrokeColor(colors.HexColor(normalize_flag_colour(colour_hex)))
        c.setLineWidth(4)
        c.line(width - 24 * mm, row_top, width - 24 * mm, row_bottom)
        c.restoreState()

    def _wrap_text(self, text: str, max_width: float, font_name: str, font_size: int) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines
