from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass

from .models import PageRange, PDFItem

DEFAULT_FLAG_COLOURS: tuple[str, ...] = (
    "#3467A5",
    "#71B735",
    "#F4DC05",
    "#F13958",
    "#FE6F25",
    "#669EAF",
    "#FF646B",
    "#CD638B",
)

FLAG_COLOUR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class BundleIndexEntry:
    item_number: int
    item: PDFItem
    page_range: PageRange
    flag_colour: str | None = None

    def __iter__(self) -> Iterator[object]:
        """Preserve tuple-unpacking compatibility with the old index-entry shape."""
        yield self.item_number
        yield self.item
        yield self.page_range


def normalize_flag_colour(colour: str) -> str:
    value = colour.strip()
    if not FLAG_COLOUR_RE.fullmatch(value):
        raise ValueError(f"Invalid flag colour: {colour!r}")
    return value.upper()


def normalize_flag_palette(colours: Iterable[str]) -> list[str]:
    normalized = [normalize_flag_colour(colour) for colour in colours]
    if not normalized:
        raise ValueError("At least one flag colour is required.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Flag colours must be unique.")
    return normalized


def assign_flag_colour(index: int, colours: Sequence[str]) -> str:
    palette = normalize_flag_palette(colours)
    return palette[index % len(palette)]


def build_bundle_index_entries(
    pdf_items: Sequence[PDFItem],
    *,
    get_page_count: Callable[[PDFItem], int],
    start_page: int = 1,
    flag_colours: Sequence[str] | None = None,
) -> list[BundleIndexEntry]:
    palette = normalize_flag_palette(flag_colours) if flag_colours is not None else None
    entries: list[BundleIndexEntry] = []
    current_page = start_page
    for index, item in enumerate(pdf_items):
        try:
            page_count = max(1, get_page_count(item))
        except Exception:
            page_count = 1
        page_range = PageRange(current_page, current_page + page_count - 1)
        colour = None if palette is None else palette[index % len(palette)]
        entries.append(BundleIndexEntry(index + 1, item, page_range, colour))
        current_page += page_count
    return entries
