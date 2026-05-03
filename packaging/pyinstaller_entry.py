"""PyInstaller entry point for the Huguenot Inn macOS app bundle."""

import json
import multiprocessing
import os
from pathlib import Path
from typing import Any

DOCLING_SMOKE_PDF_ENV = "HUGUENOT_DOCLING_SMOKE_PDF"
DOCLING_SMOKE_MODEL_ROOT_ENV = "HUGUENOT_DOCLING_SMOKE_MODEL_ROOT"


def main() -> None:
    multiprocessing.freeze_support()

    smoke_pdf = os.environ.get(DOCLING_SMOKE_PDF_ENV)
    if smoke_pdf:
        _run_docling_smoke(Path(smoke_pdf))
        return

    from huguenot.app import main as app_main

    app_main()


def _run_docling_smoke(pdf_path: Path) -> None:
    from huguenot.documents import DoclingAnalyser
    from huguenot.domain.source_documents import SourceDocument

    model_root = os.environ.get(DOCLING_SMOKE_MODEL_ROOT_ENV)
    analyser = DoclingAnalyser(model_artifacts_path=Path(model_root) if model_root else None)
    try:
        ir = analyser.analyse(SourceDocument.from_path(pdf_path))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "path": str(pdf_path),
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                }
            )
        )
        raise SystemExit(1) from exc
    print(
        json.dumps(
            {
                "status": "ok",
                "path": str(pdf_path),
                "page_count": _json_safe_getattr(ir, "page_count"),
                "title": _json_safe_getattr(ir, "title"),
            }
        )
    )


def _json_safe_getattr(value: Any, name: str) -> Any:
    attr = getattr(value, name, None)
    if isinstance(attr, str | int | float | bool) or attr is None:
        return attr
    return str(attr)


if __name__ == "__main__":
    main()
