from pathlib import Path

from huguenot.domain import (
    BundleIndexEntry,
    IndexSeparator,
    IndexSeparatorEntry,
    PDFItem,
    build_bundle_index_entries,
    build_bundle_index_rows,
    pdf_items_from_bundle_items,
)


def test_build_bundle_index_entries_keeps_legacy_entry_shape() -> None:
    item = PDFItem(Path("one.pdf"), "One")

    rows = build_bundle_index_entries([item], get_page_count=lambda _item: 2)

    assert rows == [BundleIndexEntry(1, item, rows[0].page_range)]
    number, unpacked_item, page_range = rows[0]
    assert number == 1
    assert unpacked_item == item
    assert page_range == rows[0].page_range
    assert rows[0].page_range.display() == "1-2"


def test_build_bundle_index_rows_includes_separators_without_consuming_numbers_or_pages() -> None:
    first = PDFItem(Path("first.pdf"), "First")
    second = PDFItem(Path("second.pdf"), "Second")

    rows = build_bundle_index_rows(
        [IndexSeparator("Cases"), first, IndexSeparator("Statutes"), second],
        get_page_count=lambda item: 2 if item is first else 3,
        flag_colours=["#3467A5", "#71B735"],
    )

    assert rows[0] == IndexSeparatorEntry("Cases")
    assert rows[2] == IndexSeparatorEntry("Statutes")
    assert isinstance(rows[1], BundleIndexEntry)
    assert isinstance(rows[3], BundleIndexEntry)
    assert rows[1].item_number == 1
    assert rows[1].page_range.display() == "1-2"
    assert rows[1].flag_colour == "#3467A5"
    assert rows[3].item_number == 2
    assert rows[3].page_range.display() == "3-5"
    assert rows[3].flag_colour == "#71B735"


def test_pdf_items_from_bundle_items_filters_separators() -> None:
    item = PDFItem(Path("one.pdf"), "One")

    assert pdf_items_from_bundle_items([IndexSeparator("Cases"), item]) == [item]
