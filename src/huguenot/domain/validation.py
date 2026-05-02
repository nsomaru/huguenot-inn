from __future__ import annotations

from .models import Matter, PartySide


class MatterValidationError(ValueError):
    pass


def validate_matter(matter: Matter) -> None:
    if not matter.court.name.strip():
        raise MatterValidationError("Court name is required.")

    if not matter.proceeding_type:
        raise MatterValidationError("Proceeding type is required.")

    if not any(p.side == PartySide.BRINGING and p.name.strip() for p in matter.parties):
        raise MatterValidationError("At least one bringing party is required.")

    if not any(p.side == PartySide.OPPOSING and p.name.strip() for p in matter.parties):
        raise MatterValidationError("At least one opposing party is required.")
