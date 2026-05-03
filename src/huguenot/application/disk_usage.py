from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from huguenot.documents.ir_cache import FilesystemIRCache


@dataclass(frozen=True)
class DiskUsage:
    sqlite_bytes: int
    cache_bytes: int


class DiskUsageService:
    def __init__(self, *, database_path: Path, cache: FilesystemIRCache) -> None:
        self._database_path = database_path
        self._cache = cache

    def calculate(self) -> DiskUsage:
        sqlite_size = self._database_path.stat().st_size if self._database_path.exists() else 0
        return DiskUsage(sqlite_bytes=sqlite_size, cache_bytes=self._cache.cache_size_bytes())

    def clear_cache(self) -> int:
        return self._cache.clear_cache()
