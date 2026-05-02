from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from platformdirs import user_data_path
from yoyo import get_backend, read_migrations

APP_NAME = "Huguenot Inn"
APP_AUTHOR = "Huguenot"


@dataclass(frozen=True)
class AppDatabase:
    path: Path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def migrate(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        migrations_resource = resources.files("huguenot.persistence").joinpath("migrations")
        with resources.as_file(migrations_resource) as migrations_path:
            backend = get_backend(_sqlite_url(self.path))
            migrations = read_migrations(str(migrations_path))
            with backend.lock():
                backend.apply_migrations(backend.to_apply(migrations))


def default_database_path() -> Path:
    return user_data_path(APP_NAME, APP_AUTHOR) / "huguenot.sqlite3"


def create_app_database(path: Path | None = None, *, migrate: bool = True) -> AppDatabase:
    database = AppDatabase(path or default_database_path())
    if migrate:
        database.migrate()
    return database


def _sqlite_url(path: Path) -> str:
    normalized = path.as_posix()
    return f"sqlite:///{normalized}" if not path.is_absolute() else f"sqlite:////{normalized.lstrip('/')}"
