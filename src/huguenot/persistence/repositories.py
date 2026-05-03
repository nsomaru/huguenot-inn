from __future__ import annotations

import sqlite3

from huguenot.domain import Court, Matter, Party, PartySide, ProceedingType, normalize_flag_palette

from .database import AppDatabase


class SQLiteCourtRepository:
    def __init__(self, database: AppDatabase) -> None:
        self._database = database

    def list_courts(self) -> list[Court]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.name, h.line AS header_line_2, c.source
                FROM courts c
                LEFT JOIN court_header_lines h ON h.id = c.default_header_line_id
                ORDER BY c.name
                """
            ).fetchall()
        return [
            Court(id=row["id"], name=row["name"], header_line_2=row["header_line_2"], source=row["source"])
            for row in rows
        ]

    def list_header_lines(self) -> list[str]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT line FROM court_header_lines ORDER BY line").fetchall()
        return [row["line"] for row in rows]

    def add_header_line(self, line: str) -> str:
        line = line.strip()
        if not line:
            return ""
        with self._database.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO court_header_lines(line, source) VALUES (?, ?)", (line, "user"))
        return line

    def add_court(self, name: str, header_line_2: str | None = None) -> Court:
        name = name.strip()
        if not name:
            raise ValueError("Court name is required.")

        with self._database.connect() as connection:
            header_id = None
            if header_line_2 and header_line_2.strip():
                header = header_line_2.strip()
                connection.execute(
                    "INSERT OR IGNORE INTO court_header_lines(line, source) VALUES (?, ?)", (header, "user")
                )
                row = connection.execute("SELECT id FROM court_header_lines WHERE line = ?", (header,)).fetchone()
                header_id = row["id"] if row else None

            connection.execute(
                "INSERT OR IGNORE INTO courts(name, default_header_line_id, source) VALUES (?, ?, ?)",
                (name, header_id, "user"),
            )
            if header_id is not None:
                connection.execute(
                    "UPDATE courts SET default_header_line_id = COALESCE(default_header_line_id, ?) WHERE name = ?",
                    (header_id, name),
                )
            row = connection.execute(
                """
                SELECT c.id, c.name, h.line AS header_line_2, c.source
                FROM courts c
                LEFT JOIN court_header_lines h ON h.id = c.default_header_line_id
                WHERE c.name = ?
                """,
                (name,),
            ).fetchone()

        if row is None:
            raise LookupError(name)
        return Court(id=row["id"], name=row["name"], header_line_2=row["header_line_2"], source=row["source"])


class SQLiteMatterRepository:
    def __init__(self, database: AppDatabase) -> None:
        self._database = database

    def save(self, matter: Matter) -> Matter:
        with self._database.connect() as connection:
            court_id = _ensure_court(connection, matter.court)
            header_id = _ensure_header(connection, matter.court.header_line_2)
            if matter.id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO matters(court_id, court_header_line_id, proceeding_type, case_number)
                    VALUES (?, ?, ?, ?)
                    """,
                    (court_id, header_id, matter.proceeding_type.value, matter.case_number),
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("SQLite did not return a matter id.")
                matter_id = int(cursor.lastrowid)
            else:
                matter_id = matter.id
                connection.execute(
                    """
                    UPDATE matters
                    SET court_id = ?, court_header_line_id = ?, proceeding_type = ?, case_number = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (court_id, header_id, matter.proceeding_type.value, matter.case_number, matter_id),
                )
                connection.execute("DELETE FROM parties WHERE matter_id = ?", (matter_id,))

            for party in matter.parties:
                connection.execute(
                    """
                    INSERT INTO parties(matter_id, side, name, position)
                    VALUES (?, ?, ?, ?)
                    """,
                    (matter_id, party.side.value, party.name, party.position),
                )

        saved = self.get(matter_id)
        if saved is None:
            raise LookupError(matter_id)
        return saved

    def list_matters(self) -> list[Matter]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT id FROM matters ORDER BY updated_at DESC, id DESC").fetchall()
        return [matter for row in rows if (matter := self.get(row["id"])) is not None]

    def get(self, matter_id: int) -> Matter | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT m.id, m.proceeding_type, m.case_number,
                       c.id AS court_id, c.name AS court_name, c.source AS court_source,
                       COALESCE(ch.line, dh.line) AS header_line_2
                FROM matters m
                JOIN courts c ON c.id = m.court_id
                LEFT JOIN court_header_lines ch ON ch.id = m.court_header_line_id
                LEFT JOIN court_header_lines dh ON dh.id = c.default_header_line_id
                WHERE m.id = ?
                """,
                (matter_id,),
            ).fetchone()
            if row is None:
                return None
            parties = connection.execute(
                "SELECT id, side, name, position FROM parties WHERE matter_id = ? ORDER BY side, position",
                (matter_id,),
            ).fetchall()

        court = Court(
            id=row["court_id"],
            name=row["court_name"],
            header_line_2=row["header_line_2"],
            source=row["court_source"],
        )
        return Matter(
            id=row["id"],
            court=court,
            proceeding_type=ProceedingType(row["proceeding_type"]),
            case_number=row["case_number"] or "",
            parties=tuple(
                Party(
                    id=party["id"],
                    side=PartySide(party["side"]),
                    name=party["name"],
                    position=party["position"],
                )
                for party in parties
            ),
        )

    def set_last_active(self, matter_id: int | None) -> None:
        with self._database.connect() as connection:
            if matter_id is None:
                connection.execute("DELETE FROM app_settings WHERE key = 'last_active_matter_id'")
                return
            connection.execute(
                """
                INSERT INTO app_settings(key, value) VALUES ('last_active_matter_id', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(matter_id),),
            )

    def get_last_active(self) -> Matter | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT value FROM app_settings WHERE key = 'last_active_matter_id'").fetchone()
        if row is None:
            return None
        try:
            matter_id = int(row["value"])
        except (TypeError, ValueError):
            return None
        return self.get(matter_id)


class SQLiteFlagPaletteRepository:
    def __init__(self, database: AppDatabase) -> None:
        self._database = database

    def list_palette(self) -> list[str]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT colour_hex
                FROM flag_palette_colours
                ORDER BY display_order ASC, id ASC
                """
            ).fetchall()
        return [row["colour_hex"] for row in rows]

    def replace_palette(self, colours: list[str]) -> None:
        normalized = normalize_flag_palette(colours)
        with self._database.connect() as connection:
            connection.execute("DELETE FROM flag_palette_colours")
            connection.executemany(
                """
                INSERT INTO flag_palette_colours(display_order, colour_hex)
                VALUES (?, ?)
                """,
                [(index, colour) for index, colour in enumerate(normalized, start=1)],
            )


def _ensure_header(connection: sqlite3.Connection, line: str | None) -> int | None:
    if not line or not line.strip():
        return None
    text = line.strip()
    connection.execute("INSERT OR IGNORE INTO court_header_lines(line, source) VALUES (?, ?)", (text, "user"))
    row = connection.execute("SELECT id FROM court_header_lines WHERE line = ?", (text,)).fetchone()
    return None if row is None else int(row["id"])


def _ensure_court(connection: sqlite3.Connection, court: Court) -> int:
    if court.id is not None:
        return court.id
    header_id = _ensure_header(connection, court.header_line_2)
    connection.execute(
        "INSERT OR IGNORE INTO courts(name, default_header_line_id, source) VALUES (?, ?, ?)",
        (court.name, header_id, court.source or "user"),
    )
    if header_id is not None:
        connection.execute(
            "UPDATE courts SET default_header_line_id = COALESCE(default_header_line_id, ?) WHERE name = ?",
            (header_id, court.name),
        )
    row = connection.execute("SELECT id FROM courts WHERE name = ?", (court.name,)).fetchone()
    if row is None:
        raise LookupError(court.name)
    return int(row["id"])
