from pathlib import Path

from huguenot.persistence import create_app_database


def test_startup_migrations_are_idempotent_and_seed_courts(tmp_path: Path) -> None:
    db_path = tmp_path / "huguenot.sqlite3"
    first = create_app_database(db_path)
    first.migrate()
    second = create_app_database(db_path)
    second.migrate()

    with second.connect() as connection:
        court_count = connection.execute("SELECT COUNT(*) FROM courts").fetchone()[0]
        header_count = connection.execute("SELECT COUNT(*) FROM court_header_lines").fetchone()[0]
        yoyo_count = connection.execute("SELECT COUNT(*) FROM _yoyo_migration").fetchone()[0]

    assert court_count >= 4
    assert header_count >= 10
    assert yoyo_count >= 1


def test_flag_palette_migration_seeds_defaults_and_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "huguenot.sqlite3"
    database = create_app_database(db_path)
    database.migrate()

    with database.connect() as connection:
        rows = connection.execute(
            "SELECT display_order, colour_hex FROM flag_palette_colours ORDER BY display_order"
        ).fetchall()

    assert [(row["display_order"], row["colour_hex"]) for row in rows] == [
        (1, "#3467A5"),
        (2, "#71B735"),
        (3, "#F4DC05"),
        (4, "#F13958"),
        (5, "#FE6F25"),
        (6, "#669EAF"),
        (7, "#FF646B"),
        (8, "#CD638B"),
    ]


def test_flag_palette_migration_depends_on_initial_migration() -> None:
    migration = Path("src/huguenot/persistence/migrations/0002_flag_palette_colours.sql").read_text()

    assert "-- depends: 0001_initial" in migration
