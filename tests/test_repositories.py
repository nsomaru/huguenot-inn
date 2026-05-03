from pathlib import Path

import pytest

from huguenot.application import FlagPaletteService, MatterService
from huguenot.domain import ProceedingType
from huguenot.persistence import (
    SQLiteCourtRepository,
    SQLiteFlagPaletteRepository,
    SQLiteMatterRepository,
    create_app_database,
)


def test_repositories_persist_matter_and_last_active(tmp_path: Path) -> None:
    database = create_app_database(tmp_path / "matters.sqlite3")
    court_repo = SQLiteCourtRepository(database)
    matter_repo = SQLiteMatterRepository(database)
    service = MatterService(matter_repo, court_repo)

    matter = service.create_matter(
        court_name="IN THE HIGH COURT OF SOUTH AFRICA",
        court_header_line_2="(WESTERN CAPE DIVISION, CAPE TOWN)",
        proceeding_type=ProceedingType.APPLICATION,
        case_number="2026-001",
        bringing_party_names=["Axim (Pty) Ltd"],
        opposing_party_names=["Moodie"],
    )

    assert matter.id is not None
    assert service.get_last_active_matter() == matter
    assert service.list_matters()[0].display_name == "Axim (Pty) Ltd v Moodie (2026-001)"
    assert "(WESTERN CAPE DIVISION, CAPE TOWN)" in service.list_header_lines()


def test_user_added_courts_are_listed(tmp_path: Path) -> None:
    database = create_app_database(tmp_path / "matters.sqlite3")
    court_repo = SQLiteCourtRepository(database)

    court_repo.add_court("IN THE SPECIAL TRIBUNAL", "(GAUTENG DIVISION, PRETORIA)")

    assert any(court.name == "IN THE SPECIAL TRIBUNAL" for court in court_repo.list_courts())


def test_flag_palette_repository_lists_and_replaces_palette(tmp_path: Path) -> None:
    database = create_app_database(tmp_path / "flags.sqlite3")
    service = FlagPaletteService(SQLiteFlagPaletteRepository(database))

    assert service.list_palette()[:2] == ["#3467A5", "#71B735"]

    service.replace_palette(["#abcdef", "#123456"])

    assert service.list_palette() == ["#ABCDEF", "#123456"]
    with database.connect() as connection:
        orders = connection.execute("SELECT display_order FROM flag_palette_colours ORDER BY display_order").fetchall()
    assert [row["display_order"] for row in orders] == [1, 2]


def test_flag_palette_repository_rejects_invalid_empty_and_duplicate_palettes(tmp_path: Path) -> None:
    database = create_app_database(tmp_path / "flags.sqlite3")
    service = FlagPaletteService(SQLiteFlagPaletteRepository(database))

    for palette in ([], ["#GGGGGG"], ["#12345"], ["#ABCDEF", "#abcdef"]):
        with pytest.raises(ValueError):
            service.replace_palette(palette)
