from __future__ import annotations

from huguenot.domain import Court, Matter, Party, PartySide, ProceedingType, validate_matter

from .protocols import CourtRepository, MatterRepository


class MatterService:
    def __init__(self, matter_repository: MatterRepository, court_repository: CourtRepository) -> None:
        self._matter_repository = matter_repository
        self._court_repository = court_repository

    def list_courts(self) -> list[Court]:
        return self._court_repository.list_courts()

    def list_header_lines(self) -> list[str]:
        return self._court_repository.list_header_lines()

    def add_court(self, name: str, header_line_2: str | None = None) -> Court:
        return self._court_repository.add_court(name, header_line_2)

    def add_header_line(self, line: str) -> str:
        return self._court_repository.add_header_line(line)

    def create_matter(
        self,
        *,
        court_name: str,
        court_header_line_2: str | None,
        proceeding_type: ProceedingType,
        case_number: str,
        bringing_party_names: list[str],
        opposing_party_names: list[str],
    ) -> Matter:
        court = self._court_repository.add_court(court_name, court_header_line_2)
        if court_header_line_2:
            self._court_repository.add_header_line(court_header_line_2)

        parties = [
            Party(name=name.strip(), side=PartySide.BRINGING, position=index)
            for index, name in enumerate(bringing_party_names, start=1)
            if name.strip()
        ]
        parties.extend(
            Party(name=name.strip(), side=PartySide.OPPOSING, position=index)
            for index, name in enumerate(opposing_party_names, start=1)
            if name.strip()
        )

        matter = Matter(
            court=court,
            proceeding_type=proceeding_type,
            case_number=case_number.strip(),
            parties=tuple(parties),
        )
        validate_matter(matter)
        saved = self._matter_repository.save(matter)
        if saved.id is not None:
            self._matter_repository.set_last_active(saved.id)
        return saved

    def list_matters(self) -> list[Matter]:
        return self._matter_repository.list_matters()

    def set_active_matter(self, matter_id: int | None) -> Matter | None:
        self._matter_repository.set_last_active(matter_id)
        if matter_id is None:
            return None
        return self._matter_repository.get(matter_id)

    def get_last_active_matter(self) -> Matter | None:
        return self._matter_repository.get_last_active()
