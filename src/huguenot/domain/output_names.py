from __future__ import annotations

import re

from .models import Matter

UNSAFE_FILENAME_CHARS_RE = re.compile(r"[^a-z0-9]+")
DASH_RUN_RE = re.compile(r"-+")


def safe_filename_token(value: str, *, fallback: str = "matter") -> str:
    token = UNSAFE_FILENAME_CHARS_RE.sub("-", value.casefold()).strip("-")
    token = DASH_RUN_RE.sub("-", token)
    return token or fallback


def matter_output_root(matter: Matter) -> str:
    bringing = matter.bringing_parties[0].name if matter.bringing_parties else "bringing-party"
    opposing = matter.opposing_parties[0].name if matter.opposing_parties else "opposing-party"
    bringing_token = safe_filename_token(bringing, fallback="bringing-party")
    opposing_token = safe_filename_token(opposing, fallback="opposing-party")
    return f"{bringing_token}_v_{opposing_token}"


def matter_output_filename(matter: Matter, document_type: str, extension: str) -> str:
    suffix = extension if extension.startswith(".") else f".{extension}"
    return f"{matter_output_root(matter)}_{document_type.strip().upper()}{suffix.lower()}"
