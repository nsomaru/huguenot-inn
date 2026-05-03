from huguenot.documents.legal_title_candidates import detect_authority_index_item_from_ir
from huguenot.domain.document_ir import DocumentIR, DocumentIRIdentity, DocumentTextItem, PageIR, SourceType


def make_ir(*items: DocumentTextItem) -> DocumentIR:
    return DocumentIR(
        identity=DocumentIRIdentity(path="case.pdf", checksum="abc", source_type=SourceType.PDF),
        pages=(PageIR(number=1, width=600, height=1000), PageIR(number=2, width=600, height=1000)),
        text_items=items,
    )


def test_ir_title_scoring_prefers_page_one_title_with_sa_citation() -> None:
    ir = make_ir(
        DocumentTextItem(text="JUDGMENT", page_number=1, label="SECTION_HEADER", bbox=(40, 20, 560, 60)),
        DocumentTextItem(
            text="S v MAKWANYANE [1995] ZACC 3; 1995 (3) SA 391 (CC)",
            page_number=1,
            label="TITLE",
            bbox=(40, 100, 560, 140),
        ),
        DocumentTextItem(text="S v MAKWANYANE", page_number=2, label="PAGE_HEADER", bbox=(40, 10, 560, 35)),
    )

    assert detect_authority_index_item_from_ir(ir, fallback=lambda: "legacy") == (
        "S v Makwanyane [1995] ZACC 3; 1995 (3) SA 391 (CC)"
    )


def test_ir_title_scoring_penalises_repeated_headers_and_judgment_metadata() -> None:
    ir = make_ir(
        DocumentTextItem(text="S v HEADER", page_number=1, label="PAGE_HEADER", bbox=(20, 10, 580, 30)),
        DocumentTextItem(text="S v HEADER", page_number=2, label="PAGE_HEADER", bbox=(20, 10, 580, 30)),
        DocumentTextItem(text="Coram: JUDGMENT Heard Delivered", page_number=1, label="TEXT", bbox=(40, 150, 560, 180)),
        DocumentTextItem(
            text="EX PARTE MINISTER OF SAFETY [1993] 2 All SA 373 (A)",
            page_number=1,
            label="TITLE",
            bbox=(40, 80, 560, 120),
        ),
    )

    assert detect_authority_index_item_from_ir(ir, fallback=lambda: "legacy") == (
        "Ex Parte Minister of Safety [1993] 2 All SA 373 (A)"
    )


def test_ir_title_scoring_falls_back_when_no_usable_candidate() -> None:
    ir = make_ir(DocumentTextItem(text="Coram Heard Delivered", page_number=1, label="TEXT", bbox=(40, 80, 560, 120)))

    assert detect_authority_index_item_from_ir(ir, fallback=lambda: "legacy title") == "legacy title"
