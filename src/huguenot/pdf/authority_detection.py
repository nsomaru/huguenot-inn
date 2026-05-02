from __future__ import annotations

import re
from pathlib import Path

import fitz

from huguenot.domain.legal_titles import normalize_legal_display_title

REGEX_FLAGS = re.IGNORECASE | re.VERBOSE
PARTY_CHARS = "A-Za-zÀ-ÖØ-öø-ÿ0-9&'’’.(), -"

CASE_NAME_RE = rf"""
(?:
    The[ ]+State[ ]+v[ ]+[A-ZÀ-ÖØ-Þ][{PARTY_CHARS}]{{1,120}}
  | S[ ]+v[ ]+[A-ZÀ-ÖØ-Þ][{PARTY_CHARS}]{{1,120}}
  | Ex[ ]+parte[ ]+[A-ZÀ-ÖØ-Þ][{PARTY_CHARS}]{{1,170}}
  | In[ ]+re[ ]+[A-ZÀ-ÖØ-Þ][{PARTY_CHARS}]{{1,170}}
  | [A-ZÀ-ÖØ-Þ][{PARTY_CHARS}]{{1,170}}?[ ]+(?:v|vs[.]?)[ ]+[A-ZÀ-ÖØ-Þ][{PARTY_CHARS}]{{1,220}}?
)
"""

SA_REPORT_RE = r"""
[0-9]{4}[ ]*[(][0-9]+[)][ ]*
(?:SA|SACR|BCLR)[ ]+
[0-9]+[ ]*
[(][A-Z][A-Z0-9]{0,12}[)]
"""

ALL_SA_RE = r"""
\[[0-9]{4}\][ ]*
[0-9]+[ ]*
All[ ]*SA[ ]+
[0-9]+[ ]*
[(][A-Z][A-Z0-9]{0,12}[)]
"""

LABOUR_REPORT_RE = r"""
(?:[0-9]{4}|[(][0-9]{4}[)])[ ]*
[0-9]+[ ]*
(?:ILJ|BLLR|BALR)[ ]+
[0-9]+[ ]*
[(][A-Z][A-Z0-9]{0,12}[)]
"""

JDR_JOL_RE = r"""
(?:\[[0-9]{4}\]|[0-9]{4})[ ]*
(?:JDR|JOL)[ ]+
[0-9]{3,8}[ ]*
[(][A-Z][A-Z0-9]{0,12}[)]
"""

NEUTRAL_SA_RE = r"""
(?:[(][A-Za-z0-9 .,/-]+[)][ ]*)?
\[[0-9]{4}\][.]?[ ]*
ZA[A-Z0-9]{2,14}[ ]+
[0-9]+
(?:[ ]*[(][0-9]{1,2}[ ]+[A-Za-z]+[ ]+[0-9]{4}[)])?
"""

OLD_REPORT_RE = r"""
[0-9]{4}[ ]+
(?:AD|A|NPD|TPD|CPD|OPD|WLD|GWLD|GWL|W|T|E|C|N|O|SE|Tk|Ck)[ ]+
[0-9]+
"""

ANY_CITATION_RE = rf"""
(?:
    {SA_REPORT_RE}
  | {ALL_SA_RE}
  | {LABOUR_REPORT_RE}
  | {JDR_JOL_RE}
  | {NEUTRAL_SA_RE}
  | {OLD_REPORT_RE}
)
"""

FULL_CITATION_PATTERNS = [
    re.compile(rf"(?P<citation>{CASE_NAME_RE}[ ]+{SA_REPORT_RE})", REGEX_FLAGS),
    re.compile(rf"(?P<citation>{CASE_NAME_RE}[ ]+{ALL_SA_RE})", REGEX_FLAGS),
    re.compile(rf"(?P<citation>{CASE_NAME_RE}[ ]+{LABOUR_REPORT_RE})", REGEX_FLAGS),
    re.compile(rf"(?P<citation>{CASE_NAME_RE}[ ]+{JDR_JOL_RE})", REGEX_FLAGS),
    re.compile(rf"(?P<citation>{CASE_NAME_RE}[ ]+{NEUTRAL_SA_RE})", REGEX_FLAGS),
    re.compile(rf"(?P<citation>{CASE_NAME_RE}[ ]+{OLD_REPORT_RE})", REGEX_FLAGS),
]

LABELED_FULL_CITATION_PATTERNS = [
    re.compile(
        rf"(?:Neutral[ ]+citation|Citation)[ ]*:[ ]*(?P<citation>{CASE_NAME_RE}[ ]+{ANY_CITATION_RE})",
        REGEX_FLAGS,
    ),
]

CASE_NAME_PATTERN = re.compile(rf"(?P<name>{CASE_NAME_RE})", REGEX_FLAGS)

REPORT_ONLY_PATTERNS = [
    re.compile(rf"(?P<citation>{SA_REPORT_RE})", REGEX_FLAGS),
    re.compile(rf"(?P<citation>{ALL_SA_RE})", REGEX_FLAGS),
    re.compile(rf"(?P<citation>{LABOUR_REPORT_RE})", REGEX_FLAGS),
    re.compile(rf"(?P<citation>{JDR_JOL_RE})", REGEX_FLAGS),
    re.compile(rf"(?P<citation>{NEUTRAL_SA_RE})", REGEX_FLAGS),
    re.compile(rf"(?P<citation>{OLD_REPORT_RE})", REGEX_FLAGS),
]

BAD_CONTEXT_RE = re.compile(
    r"cases?[ ]+(?:cited|considered|referred[ ]+to)|authorities|statutes|legislation|annotations?|"
    r"flynote|headnote|catchwords?|summary",
    re.IGNORECASE,
)

SECTION_BOUNDARY_RE = re.compile(
    r"(?:JUDGMENT|ORDER|REASONS|CORAM|HEARD|DELIVERED|DATE[ ]+OF[ ]+JUDGMENT|APPEARANCES|COUNSEL|ATTORNEYS)",
    re.IGNORECASE,
)

LEADING_NOISE_RE = re.compile(
    r"^(?:see also|see|cf|compare|but see|contra|in|the matter of|matter between)[ ]+",
    re.IGNORECASE,
)

TRAILING_NOISE_RE = re.compile(r"[ ,.;:]+$")

YEAR_MARKER_RE = re.compile(
    r"\[[0-9]{4}\]|[(][0-9]{4}[)]|[0-9]{4}[ ]*[(][0-9]+[)]|"
    r"[0-9]{4}[ ]+(?:AD|A|NPD|TPD|CPD|OPD|WLD|GWLD|GWL|W|T|E|C|N|O|SE|Tk|Ck)",
    re.IGNORECASE,
)

SPECIAL_WORDS = {
    "pty": "Pty",
    "ltd": "Ltd",
    "limited": "Limited",
    "inc": "Inc",
    "cc": "CC",
    "npc": "NPC",
    "no": "NO",
    "nno": "NNO",
    "mec": "MEC",
    "ccma": "CCMA",
    "numsa": "NUMSA",
    "satawu": "SATAWU",
    "nehawu": "NEHAWU",
    "sars": "SARS",
    "saps": "SAPS",
    "raf": "RAF",
    "sabc": "SABC",
    "sadtu": "SADTU",
    "cosatu": "COSATU",
    "lra": "LRA",
    "bcea": "BCEA",
    "uif": "UIF",
    "seta": "SETA",
    "soc": "SOC",
    "ndpp": "NDPP",
    "djp": "DJP",
    "aj": "AJ",
    "jp": "JP",
    "est": "Est",
    "sahrc": "SAHRC",
    "iec": "IEC",
    "icasa": "ICASA",
    "sc": "SC",
}

LOWERCASE_WORDS = {
    "v",
    "vs",
    "and",
    "or",
    "of",
    "for",
    "in",
    "on",
    "at",
    "to",
    "by",
    "from",
    "with",
}

INITIALS_RE = re.compile(r"^(?:[A-Z][.])+$")


def smart_title_word(word: str, *, is_first_word: bool = False) -> str:
    if not word:
        return word

    key = word.casefold().strip(".")

    if key in SPECIAL_WORDS:
        return SPECIAL_WORDS[key]

    if INITIALS_RE.match(word):
        return word.upper()

    if key in LOWERCASE_WORDS and not is_first_word:
        return key

    if "-" in word:
        return "-".join(
            smart_title_word(part, is_first_word=is_first_word and index == 0)
            for index, part in enumerate(word.split("-"))
        )

    if "’" in word:
        return "’".join(
            smart_title_word(part, is_first_word=is_first_word and index == 0)
            for index, part in enumerate(word.split("’"))
        )

    if "'" in word:
        return "'".join(
            smart_title_word(part, is_first_word=is_first_word and index == 0)
            for index, part in enumerate(word.split("'"))
        )

    return word[:1].upper() + word[1:].lower()


def smart_title_party_text(text: str) -> str:
    normalized = normalize_legal_display_title(text)
    if normalized != text:
        return normalized

    parts = re.split(r"([^A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+)", text)
    output: list[str] = []
    word_count = 0

    for index, part in enumerate(parts):
        if index % 2 == 0 and part:
            output.append(smart_title_word(part, is_first_word=(word_count == 0)))
            word_count += 1
        else:
            output.append(part)

    return "".join(output)


def clean_title_or_citation(text: str) -> str:
    text = text.replace(chr(173), "")
    text = " ".join(text.split()).strip()
    text = re.sub(r" +([,.;:])", lambda m: m.group(1), text)
    text = re.sub(r"[(] +", "(", text)
    text = re.sub(r" +[)]", ")", text)
    text = LEADING_NOISE_RE.sub("", text)
    text = TRAILING_NOISE_RE.sub("", text)
    return text.strip()


def titlecase_parties_before_year(citation: str) -> str:
    citation = clean_title_or_citation(citation)
    match = YEAR_MARKER_RE.search(citation)
    if not match:
        return citation
    parties = citation[: match.start()].strip()
    rest = citation[match.start() :].strip()
    if not parties:
        return citation
    return f"{normalize_legal_display_title(parties)} {rest}".strip()


def strip_juta_source_noise(text: str) -> str:
    month_names = "January|February|March|April|May|June|July|August|September|October|November|December"
    text = re.sub(
        rf"Source *:.*?/[0-9]{{4}}/(?:{month_names})/",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(
        rf"Source *:.*?Chronological +listing +[0-9]{{4}} +(?:{month_names}) +",
        "",
        text,
        flags=re.IGNORECASE,
    )


def normalise_pdf_text(text: str) -> str:
    text = text.replace(chr(173), "")
    text = re.sub(
        r"([A-Za-zÀ-ÖØ-öø-ÿ])- +([A-Za-zÀ-ÖØ-öø-ÿ])",
        lambda m: m.group(1) + m.group(2),
        text,
    )
    text = " ".join(text.split())
    return strip_juta_source_noise(text)


def clean_filename_title(path: Path) -> str:
    title = path.stem
    title = re.sub(r"[_]+", " ", title)
    title = re.sub(r" +- +", " - ", title)
    title = " ".join(title.split()).strip()
    return title or path.name


def top_text_from_first_page(doc: fitz.Document, top_fraction: float = 0.60) -> str:
    if doc.page_count == 0:
        return ""
    page = doc[0]
    cutoff_y = page.rect.y0 + page.rect.height * top_fraction
    blocks = page.get_text("blocks", sort=True)
    parts = [str(block[:5][4]) for block in blocks if block[1] <= cutoff_y]
    return normalise_pdf_text(chr(10).join(parts))


def first_pages_text(doc: fitz.Document, pages: int = 2) -> str:
    parts = [str(doc[i].get_text("text", sort=True)) for i in range(min(pages, doc.page_count))]
    return normalise_pdf_text(chr(10).join(parts))


def text_before_first_boundary(text: str) -> str:
    match = SECTION_BOUNDARY_RE.search(text)
    return text if not match else text[: match.start()]


def candidate_penalty_for_context(text: str, start: int) -> int:
    context = text[max(0, start - 160) : start]
    return -140 if BAD_CONTEXT_RE.search(context) else 0


def find_first_report_after(text: str, start: int, window: int = 600) -> str | None:
    snippet = text[start : start + window]
    best: tuple[int, str] | None = None
    for pattern in REPORT_ONLY_PATTERNS:
        for match in pattern.finditer(snippet):
            citation = clean_title_or_citation(match.group("citation"))
            if citation and (best is None or match.start() < best[0]):
                best = (match.start(), citation)
    return None if best is None else best[1]


def find_best_full_citation_candidate(text: str, base_score: int) -> tuple[int, str] | None:
    best: tuple[int, str] | None = None

    for pattern in LABELED_FULL_CITATION_PATTERNS:
        for match in pattern.finditer(text):
            candidate = titlecase_parties_before_year(match.group("citation"))
            if not candidate:
                continue
            score = base_score + 160 + candidate_penalty_for_context(text, match.start())
            score -= min(match.start() // 200, 25)
            if best is None or score > best[0]:
                best = (score, candidate)

    for pattern in FULL_CITATION_PATTERNS:
        for match in pattern.finditer(text):
            candidate = titlecase_parties_before_year(match.group("citation"))
            if not candidate:
                continue
            score = base_score + 90 + candidate_penalty_for_context(text, match.start())
            score -= min(match.start() // 120, 45)
            if best is None or score > best[0]:
                best = (score, candidate)
    return best


def find_case_name_plus_nearby_report(text: str) -> tuple[int, str] | None:
    for match in CASE_NAME_PATTERN.finditer(text):
        if candidate_penalty_for_context(text, match.start()) < 0:
            continue
        name = clean_title_or_citation(match.group("name"))
        if not name or len(name) > 260:
            continue
        report = find_first_report_after(text, match.end())
        if report:
            return match.start(), titlecase_parties_before_year(f"{name} {report}")
    return None


def detect_authority_index_item(path: Path) -> str:
    fallback = clean_filename_title(path)
    try:
        doc = fitz.open(path)
    except Exception:
        return fallback

    try:
        if doc.page_count == 0:
            return fallback

        top_first_page = top_text_from_first_page(doc)
        first_two_pages = first_pages_text(doc, pages=2)
        early_text = text_before_first_boundary(first_two_pages)
        title_text = top_first_page or early_text[:3500]
        candidates: list[tuple[int, str]] = []

        for text, base_score in [
            (title_text, 90),
            (early_text, 55),
            (first_two_pages[:5500], 15),
        ]:
            full = find_best_full_citation_candidate(text, base_score)
            if full is not None:
                candidates.append(full)
            nearby = find_case_name_plus_nearby_report(text)
            if nearby is not None:
                start, citation = nearby
                score = base_score + 60 + candidate_penalty_for_context(text, start)
                score -= min(start // 120, 45)
                candidates.append((score, citation))

        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1]
        return fallback
    finally:
        doc.close()
