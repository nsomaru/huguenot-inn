from __future__ import annotations

import re

YEAR_MARKER_RE = re.compile(
    r"\[[0-9]{4}\]|[(][0-9]{4}[)]|[0-9]{4}[ ]*[(][0-9]+[)]|"
    r"[0-9]{4}[ ]+(?:AD|A|NPD|TPD|CPD|OPD|WLD|GWLD|GWL|W|T|E|C|N|O|SE|Tk|Ck)",
    re.IGNORECASE,
)

LEGAL_INDICATOR_RE = re.compile(
    r"\b(?:V|VS|EN|VAN|DIE|HOF|SAAK|MINISTER|STAAT|BPK|EDMS|EIENDOMS|BEPERK|PTY|LTD|CC|"
    r"APPLIKANT|RESPONDENT|POLISIE|SEKURITEIT|BORGAANSOEK|STRAFVERRIGTINGE)\b|N[.]O[.]|N[.]N[.]O[.]|T/A",
)

LOWERCASE_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "de",
    "den",
    "der",
    "die",
    "en",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "onder",
    "or",
    "saak",
    "strafverrigtinge",
    "te",
    "ten",
    "ter",
    "the",
    "to",
    "tussen",
    "van",
    "with",
}

SPECIAL_WORDS = {
    "absa": "ABSA",
    "acl": "ACL",
    "aj": "AJ",
    "bk": "BK",
    "bpk": "Bpk",
    "cc": "CC",
    "edms": "Edms",
    "eiendoms": "Eiendoms",
    "fze": "FZE",
    "kc": "KC",
    "ltd": "Ltd",
    "limited": "Limited",
    "n.o": "N.O.",
    "n.o.": "N.O.",
    "n.n.o": "N.N.O.",
    "n.n.o.": "N.N.O.",
    "no": "NO",
    "nno": "NNO",
    "pty": "Pty",
    "sa": "SA",
    "sc": "SC",
    "t/a": "t/a",
    "v": "v",
    "vs": "v",
}

UPPERCASE_LETTER_RE = re.compile(r"[A-ZÀ-ÖØ-Þ]")
LOWERCASE_LETTER_RE = re.compile(r"[a-zà-öø-ÿ]")
INITIALS_RE = re.compile(r"^[A-Z](?:[.][A-Z])+[.]?$")
AMPERSAND_INITIALISM_RE = re.compile(r"^[A-Z](?:&[A-Z])+$")


def should_normalize_legal_title(text: str) -> bool:
    """Return whether a display title is safe to normalize with conservative rules."""
    candidate = " ".join(text.split()).strip()
    if not candidate or LOWERCASE_LETTER_RE.search(candidate):
        return False
    if candidate.casefold() == "hoe hof":
        return False
    return bool(UPPERCASE_LETTER_RE.search(candidate) and LEGAL_INDICATOR_RE.search(candidate))


def normalize_legal_display_title(text: str) -> str:
    """Normalize an all-caps South African legal display title without touching unsafe text.

    The helper is deliberately pure text-in/text-out. It does not infer missing
    diacritics, translate between English and Afrikaans, or mutate persisted matter data.
    """
    if not should_normalize_legal_title(text):
        return text

    match = YEAR_MARKER_RE.search(text)
    if match is None:
        return _normalize_words(text)

    parties = text[: match.start()].rstrip()
    rest = text[match.start() :].lstrip()
    if not parties:
        return text
    return f"{_normalize_words(parties)} {rest}".strip()


def _normalize_words(text: str) -> str:
    parts = re.split(r"(\s+)", text)
    word_index = 0
    after_case_separator = False
    output: list[str] = []

    for part in parts:
        if not part or part.isspace():
            output.append(part)
            continue

        normalized = _normalize_token(part, is_first=word_index == 0, after_case_separator=after_case_separator)
        output.append(normalized)
        core = _token_core(part).casefold()
        after_case_separator = core in {"v", "vs"}
        word_index += 1

    return "".join(output)


def _token_core(token: str) -> str:
    return token.strip("()[]{}.,:;")


def _normalize_token(token: str, *, is_first: bool, after_case_separator: bool) -> str:
    if token in {"&"}:
        return token
    if INITIALS_RE.match(token):
        return token.upper()
    if AMPERSAND_INITIALISM_RE.match(token):
        return token.upper()

    leading = ""
    trailing = ""
    core = token
    while core and core[0] in "([{":
        leading += core[0]
        core = core[1:]
    while core and core[-1] in ")]}.,:;":
        trailing = core[-1] + trailing
        core = core[:-1]

    if not core:
        return token

    if "/" in core:
        replacement = _normalize_slash_token(core)
    elif "-" in core:
        replacement = "-".join(
            _normalize_token(part, is_first=is_first and index == 0, after_case_separator=after_case_separator)
            for index, part in enumerate(core.split("-"))
        )
    elif core in {"'N", "’N"}:
        replacement = core[0] + "n"
    else:
        replacement = _normalize_simple_core(core, is_first=is_first, after_case_separator=after_case_separator)

    return f"{leading}{replacement}{trailing}"


def _normalize_slash_token(core: str) -> str:
    key = core.casefold()
    if key in SPECIAL_WORDS:
        return SPECIAL_WORDS[key]
    return "/".join(part.lower() if part.casefold() in {"a"} else part for part in core.split("/"))


def _normalize_simple_core(core: str, *, is_first: bool, after_case_separator: bool) -> str:
    key = core.casefold().strip(".")
    if key in SPECIAL_WORDS:
        return SPECIAL_WORDS[key]
    if len(core) == 1 and core.isalpha():
        return core.upper()
    if key in LOWERCASE_WORDS and not (is_first or after_case_separator):
        return key
    if key in LOWERCASE_WORDS and key != "a":
        return key[:1].upper() + key[1:]
    return core[:1].upper() + core[1:].lower()
