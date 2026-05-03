from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from platformdirs import user_data_path

from huguenot.domain.document_ir import (
    DocumentIR,
    DocumentIRIdentity,
    IndexIR,
    OutputGenerationSettings,
    compute_file_checksum,
    document_ir_from_json,
    document_ir_to_json,
    index_ir_from_json,
    index_ir_to_json,
    settings_identity,
)
from huguenot.persistence.database import APP_AUTHOR, APP_NAME

CACHE_SCHEMA_VERSION = "1"
DEFAULT_PARSER_VERSION = "docling-2.92"


def document_checksum(path: Path) -> str:
    return compute_file_checksum(path)


def default_ir_cache_root() -> Path:
    return user_data_path(APP_NAME, APP_AUTHOR) / "ir-cache"


class FilesystemIRCache:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_ir_cache_root()

    def source_ir_path(self, identity: DocumentIRIdentity) -> Path:
        return self.root / "sources" / identity.source_type.value / f"{identity.checksum}.parquet"

    def index_ir_path(self, cache_key: str) -> Path:
        return self.root / "indexes" / f"{cache_key}.parquet"

    def save_source_ir(self, ir: DocumentIR) -> Path:
        path = self.source_ir_path(ir.identity)
        self._write_artifact(path, artifact_type="source", key=ir.identity.checksum, payload=document_ir_to_json(ir))
        return path

    def load_source_ir(self, identity: DocumentIRIdentity) -> DocumentIR | None:
        path = self.source_ir_path(identity)
        try:
            payload = self._read_payload(path, artifact_type="source", key=identity.checksum)
            ir = document_ir_from_json(payload)
        except Exception:
            return None
        if ir.identity.checksum != identity.checksum or ir.identity.source_type != identity.source_type:
            return None
        return ir

    def save_index_ir(self, ir: IndexIR) -> Path:
        path = self.index_ir_path(ir.cache_key)
        self._write_artifact(path, artifact_type="index", key=ir.cache_key, payload=index_ir_to_json(ir))
        return path

    def load_index_ir(self, cache_key: str) -> IndexIR | None:
        path = self.index_ir_path(cache_key)
        try:
            payload = self._read_payload(path, artifact_type="index", key=cache_key)
            ir = index_ir_from_json(payload)
        except Exception:
            return None
        return ir if ir.cache_key == cache_key else None

    def index_key(
        self,
        identities: tuple[DocumentIRIdentity, ...] | list[DocumentIRIdentity],
        *,
        separator_titles: tuple[str, ...] = (),
        matter_context: str = "",
        settings: OutputGenerationSettings | None = None,
        schema_version: str = CACHE_SCHEMA_VERSION,
        parser_version: str = DEFAULT_PARSER_VERSION,
    ) -> str:
        payload: dict[str, Any] = {
            "schema_version": schema_version,
            "parser_version": parser_version,
            "sources": [
                {
                    "checksum": identity.checksum,
                    "source_type": identity.source_type.value,
                    "parser_version": identity.parser_version,
                }
                for identity in identities
            ],
            "separator_titles": list(separator_titles),
            "matter_context": matter_context,
            "settings": settings_identity(settings or OutputGenerationSettings()),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def cache_size_bytes(self) -> int:
        if not self.root.exists():
            return 0
        return sum(path.stat().st_size for path in self.root.rglob("*.parquet") if path.is_file())

    def clear_cache(self) -> int:
        removed = 0
        if not self.root.exists():
            return removed
        for path in list(self.root.rglob("*.parquet")):
            if not path.is_file():
                continue
            removed += path.stat().st_size
            path.unlink()
        _remove_empty_dirs(self.root)
        return removed

    def _write_artifact(self, path: Path, *, artifact_type: str, key: str, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.table(
            {
                "schema_version": [CACHE_SCHEMA_VERSION],
                "artifact_type": [artifact_type],
                "key": [key],
                "payload_json": [payload],
            }
        )
        pq.write_table(table, path)

    def _read_payload(self, path: Path, *, artifact_type: str, key: str) -> str:
        table = pq.read_table(path)
        rows = table.to_pylist()
        if len(rows) != 1:
            raise ValueError("IR artifact must contain exactly one row")
        row = rows[0]
        if row.get("schema_version") != CACHE_SCHEMA_VERSION:
            raise ValueError("Unsupported IR cache schema")
        if row.get("artifact_type") != artifact_type or row.get("key") != key:
            raise ValueError("IR artifact identity mismatch")
        payload = row.get("payload_json")
        if not isinstance(payload, str):
            raise ValueError("IR artifact payload is missing")
        return payload


def _remove_empty_dirs(root: Path) -> None:
    for directory in sorted(
        (path for path in root.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
