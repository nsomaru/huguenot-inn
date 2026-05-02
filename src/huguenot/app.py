from __future__ import annotations

from huguenot.documents import create_authorities_index_docx
from huguenot.domain import PDFItem
from huguenot.pdf import POSITIONS, combine_number_and_add_toc, detect_authority_index_item
from huguenot.ui.app import PDFCombinerNumbererTOCIndexApp, main

__all__ = [
    "PDFCombinerNumbererTOCIndexApp",
    "PDFItem",
    "POSITIONS",
    "combine_number_and_add_toc",
    "create_authorities_index_docx",
    "detect_authority_index_item",
    "main",
]


if __name__ == "__main__":
    main()
