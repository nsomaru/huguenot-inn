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
