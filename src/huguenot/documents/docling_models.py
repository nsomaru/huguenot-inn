from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path

from huguenot.persistence.database import APP_AUTHOR, APP_NAME

MODEL_MARKER_VERSION = "docling-2.92"


@dataclass(frozen=True)
class DoclingModelStatus:
    stage: str
    message: str
    current: int = 0
    total: int = 0


DoclingModelProgress = Callable[[DoclingModelStatus], None]
DoclingModelDownloader = Callable[[DoclingModelProgress], None]


def default_docling_model_root() -> Path:
    return user_data_path(APP_NAME, APP_AUTHOR) / "docling-models"


class DoclingModelManager:
    def __init__(
        self,
        *,
        cache_root: Path | None = None,
        downloader: DoclingModelDownloader | None = None,
        marker_version: str = MODEL_MARKER_VERSION,
    ) -> None:
        self.cache_root = cache_root or default_docling_model_root()
        self._downloader = downloader or self._download_docling_models
        self._marker_version = marker_version

    @property
    def marker_path(self) -> Path:
        return self.cache_root / ".huguenot-docling-models-ready.json"

    def models_ready(self) -> bool:
        try:
            marker = json.loads(self.marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        return marker.get("marker_version") == self._marker_version

    def mark_ready(self) -> None:
        self.cache_root.mkdir(parents=True, exist_ok=True)
        payload = {"marker_version": self._marker_version}
        self.marker_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def ensure_models(self, progress: DoclingModelProgress) -> None:
        progress(DoclingModelStatus("models-checking", "Checking Docling models"))
        if self.models_ready():
            progress(DoclingModelStatus("models-ready", "Docling models ready"))
            return
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self._downloader(progress)
        self.mark_ready()
        progress(DoclingModelStatus("models-ready", "Docling models ready"))

    def _download_docling_models(self, progress: DoclingModelProgress) -> None:
        from docling.utils.model_downloader import download_models

        progress(DoclingModelStatus("models-downloading", "Downloading Docling layout model", 1, 3))
        download_models(
            output_dir=self.cache_root,
            progress=False,
            with_layout=True,
            with_tableformer=False,
            with_tableformer_v2=False,
            with_code_formula=False,
            with_picture_classifier=False,
            with_smolvlm=False,
            with_granitedocling=False,
            with_granitedocling_mlx=False,
            with_smoldocling=False,
            with_smoldocling_mlx=False,
            with_granite_vision=False,
            with_granite_chart_extraction=False,
            with_granite_chart_extraction_v4=False,
            with_rapidocr=False,
            with_easyocr=False,
        )
        progress(DoclingModelStatus("models-downloading", "Downloading Docling table model", 2, 3))
        download_models(
            output_dir=self.cache_root,
            progress=False,
            with_layout=False,
            with_tableformer=True,
            with_tableformer_v2=False,
            with_code_formula=False,
            with_picture_classifier=False,
            with_smolvlm=False,
            with_granitedocling=False,
            with_granitedocling_mlx=False,
            with_smoldocling=False,
            with_smoldocling_mlx=False,
            with_granite_vision=False,
            with_granite_chart_extraction=False,
            with_granite_chart_extraction_v4=False,
            with_rapidocr=False,
            with_easyocr=False,
        )
        progress(DoclingModelStatus("models-downloading", "Downloading Docling OCR model", 3, 3))
        download_models(
            output_dir=self.cache_root,
            progress=False,
            with_layout=False,
            with_tableformer=False,
            with_tableformer_v2=False,
            with_code_formula=False,
            with_picture_classifier=False,
            with_smolvlm=False,
            with_granitedocling=False,
            with_granitedocling_mlx=False,
            with_smoldocling=False,
            with_smoldocling_mlx=False,
            with_granite_vision=False,
            with_granite_chart_extraction=False,
            with_granite_chart_extraction_v4=False,
            with_rapidocr=True,
            with_easyocr=False,
        )
