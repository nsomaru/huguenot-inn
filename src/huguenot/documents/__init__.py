from .authorities_index import (
    create_authorities_index_docx,
    create_authorities_index_docx_from_rows,
    create_matter_authorities_index_docx,
    create_matter_authorities_index_docx_from_rows,
    get_index_entries,
    get_index_rows,
)
from .converter import Docx2PdfConverter, DocxToPdfConverter, LibreOfficeConverter
from .docling_adapter import DoclingAnalyser, DoclingAnalysisError
from .docling_models import DoclingModelManager, DoclingModelStatus, default_docling_model_root
from .ir_cache import FilesystemIRCache, default_ir_cache_root, document_checksum
from .legal_title_candidates import detect_authority_index_item_from_ir
from .matter_index_pdf import render_matter_index_pdf, render_matter_index_pdf_from_rows
from .reportlab_index import ReportLabIndexRenderer
from .settings import (
    FontResolver,
    PDFRenderer,
    RendererPreference,
    ResolvedIndexFont,
    choose_pdf_renderer,
    list_system_fonts,
)

__all__ = [
    "PDFRenderer",
    "FontResolver",
    "Docx2PdfConverter",
    "DoclingAnalyser",
    "DoclingAnalysisError",
    "DoclingModelManager",
    "DoclingModelStatus",
    "FilesystemIRCache",
    "default_ir_cache_root",
    "default_docling_model_root",
    "document_checksum",
    "detect_authority_index_item_from_ir",
    "DocxToPdfConverter",
    "LibreOfficeConverter",
    "ReportLabIndexRenderer",
    "RendererPreference",
    "ResolvedIndexFont",
    "choose_pdf_renderer",
    "create_authorities_index_docx",
    "create_authorities_index_docx_from_rows",
    "create_matter_authorities_index_docx",
    "create_matter_authorities_index_docx_from_rows",
    "get_index_entries",
    "get_index_rows",
    "list_system_fonts",
    "render_matter_index_pdf",
    "render_matter_index_pdf_from_rows",
]
