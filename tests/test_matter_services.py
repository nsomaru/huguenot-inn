from pathlib import Path

from huguenot.application import MatterService
from huguenot.domain import ProceedingType
from huguenot.persistence import SQLiteCourtRepository, SQLiteMatterRepository, create_app_database


def test_matter_service_creates_active_matter_and_exposes_dropdown_entries(tmp_path: Path) -> None:
    database = create_app_database(tmp_path / "matters.sqlite3")
    service = MatterService(SQLiteMatterRepository(database), SQLiteCourtRepository(database))

    matter = service.create_matter(
        court_name="IN THE HIGH COURT OF SOUTH AFRICA",
        court_header_line_2="(WESTERN CAPE LOCAL DIVISION, CAPE TOWN)",
        proceeding_type=ProceedingType.ACTION,
        case_number="",
        bringing_party_names=["Plaintiff One"],
        opposing_party_names=["Defendant One"],
    )

    assert service.get_last_active_matter() == matter
    assert any(court.name == "IN THE HIGH COURT OF SOUTH AFRICA" for court in service.list_courts())
    assert "(WESTERN CAPE LOCAL DIVISION, CAPE TOWN)" in service.list_header_lines()
