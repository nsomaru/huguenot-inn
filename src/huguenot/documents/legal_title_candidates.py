from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable

from huguenot.domain.document_ir import DocumentIR, DocumentTextItem
from huguenot.domain.legal_titles import normalize_legal_display_title
from huguenot.pdf.authority_detection import titlecase_parties_before_year

LEGAL_PATTERN_RE = re.compile(r"\b(?:v|vs|ex parte|in re|n[.]?o[.]?)\b", re.IGNORECASE)
SA_CITATION_RE = re.compile(
    r"(?:\[[0-9]{4}\]\s*[0-9]*\s*[A-Z][A-Za-z ]+\s*[0-9]+\s*\([A-Z]+\)|"
    r"[0-9]{4}\s*\([0-9]+\)\s*[A-Z]{1,4}\s*[0-9]+\s*\([A-Z]+\)|"
    r"\[[0-9]{4}\]\s*Z[A-Z]+\s*[0-9]+)",
    re.IGNORECASE,
)
BAD_WORD_RE = re.compile(r"\b(?:JUDGMENT|CORAM|HEARD|DELIVERED)\b", re.IGNORECASE)


def detect_authority_index_item_from_ir(ir: DocumentIR | None, *, fallback: Callable[[], str]) -> str:
    if ir is None:
        return fallback()
    candidate = best_title_candidate(ir)
    return fallback() if candidate is None else candidate


def best_title_candidate(ir: DocumentIR) -> str | None:
    repeated = Counter(_normalized_text(item.text) for item in ir.text_items if item.text.strip())
    best: tuple[int, int, str] | None = None
    for index, item in enumerate(ir.text_items):
        text = _clean_candidate(item.text)
        if not _looks_like_case_title(text):
            continue
        score = _score_item(item, ir, repeated)
        if score < 30:
            continue
        normalized = _normalize_candidate(text)
        if best is None or score > best[0] or (score == best[0] and index < best[1]):
            best = (score, index, normalized)
    return None if best is None else best[2]


def _score_item(item: DocumentTextItem, ir: DocumentIR, repeated: Counter[str]) -> int:
    label = (item.label or "").upper()
    score = 0
    if label == "TITLE":
        score += 40
    if label == "SECTION_HEADER":
        score += 25
    if item.page_number == 1:
        score += 25
    if _is_top_third(item, ir):
        score += 20
    if LEGAL_PATTERN_RE.search(item.text):
        score += 30
    if SA_CITATION_RE.search(item.text):
        score += 30
    if _is_all_caps_title_block(item.text):
        score += 10
    if repeated[_normalized_text(item.text)] > 1:
        score -= 30
    if label in {"PAGE_HEADER", "PAGE_FOOTER", "HEADER", "FOOTER"}:
        score -= 50
    if BAD_WORD_RE.search(item.text):
        score -= 20
    return score


def _is_top_third(item: DocumentTextItem, ir: DocumentIR) -> bool:
    if item.bbox is None:
        return False
    page = next((page for page in ir.pages if page.number == item.page_number), None)
    if page is None or not page.height:
        return False
    return item.bbox[1] <= page.height * 0.35


def _is_all_caps_title_block(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return False
    uppercase = sum(1 for char in letters if char.upper() == char)
    return uppercase / len(letters) >= 0.75


def _looks_like_case_title(text: str) -> bool:
    return bool(LEGAL_PATTERN_RE.search(text) or SA_CITATION_RE.search(text)) and not _only_bad_words(text)


def _only_bad_words(text: str) -> bool:
    stripped = BAD_WORD_RE.sub("", text).strip(" :;,-")
    return not stripped


def _normalize_candidate(text: str) -> str:
    titlecased = titlecase_parties_before_year(text)
    return normalize_legal_display_title(titlecased)


def _clean_candidate(text: str) -> str:
    return " ".join(text.split()).strip(" -–—:")


def _normalized_text(text: str) -> str:
    return _clean_candidate(text).casefold()
