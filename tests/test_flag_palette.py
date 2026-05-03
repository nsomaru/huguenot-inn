from pathlib import Path

import pytest

from huguenot.domain import (
    DEFAULT_FLAG_COLOURS,
    PDFItem,
    assign_flag_colour,
    build_bundle_index_entries,
    normalize_flag_colour,
    normalize_flag_palette,
)


def test_default_flag_palette_matches_product_order() -> None:
    assert DEFAULT_FLAG_COLOURS == (
        "#3467A5",
        "#71B735",
        "#F4DC05",
        "#F13958",
        "#FE6F25",
        "#669EAF",
        "#FF646B",
        "#CD638B",
    )


def test_flag_assignment_repeats_in_order() -> None:
    assigned = [assign_flag_colour(index, DEFAULT_FLAG_COLOURS) for index in range(10)]

    assert assigned[:8] == list(DEFAULT_FLAG_COLOURS)
    assert assigned[8:] == ["#3467A5", "#71B735"]


def test_palette_validation_normalizes_uppercase_and_rejects_bad_values() -> None:
    assert normalize_flag_colour("#abc123") == "#ABC123"
    assert normalize_flag_palette(["#abc123", "#000000"]) == ["#ABC123", "#000000"]

    for value in ("#GGGGGG", "123456", "#12345", "#1234567", ""):
        with pytest.raises(ValueError):
            normalize_flag_colour(value)

    with pytest.raises(ValueError):
        normalize_flag_palette(["#ABC123", "#abc123"])
    with pytest.raises(ValueError):
        normalize_flag_palette([])


def test_bundle_index_entries_carry_page_ranges_items_and_colours() -> None:
    items = [PDFItem(Path("one.pdf"), "One"), PDFItem(Path("two.pdf"), "Two"), PDFItem(Path("three.pdf"), "Three")]
    page_counts = {"one.pdf": 2, "two.pdf": 1, "three.pdf": 3}

    entries = build_bundle_index_entries(
        items,
        get_page_count=lambda item: page_counts[item.path.name],
        flag_colours=["#000001", "#000002"],
    )

    assert [entry.item_number for entry in entries] == [1, 2, 3]
    assert [entry.page_range.display() for entry in entries] == ["1-2", "3", "4-6"]
    assert [entry.flag_colour for entry in entries] == ["#000001", "#000002", "#000001"]
    assert list(entries[0]) == [1, items[0], entries[0].page_range]
