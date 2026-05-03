from pathlib import Path

from huguenot.documents.docling_models import DoclingModelManager, DoclingModelStatus


def test_docling_model_manager_reports_not_ready_without_marker(tmp_path: Path) -> None:
    manager = DoclingModelManager(cache_root=tmp_path, downloader=lambda _progress: None)

    assert manager.models_ready() is False


def test_docling_model_manager_downloads_once_and_writes_ready_marker(tmp_path: Path) -> None:
    calls: list[str] = []
    events: list[DoclingModelStatus] = []

    def downloader(progress):
        calls.append("download")
        progress(DoclingModelStatus("models-downloading", "Downloading fixture models", 1, 1))

    manager = DoclingModelManager(cache_root=tmp_path, downloader=downloader)

    manager.ensure_models(events.append)

    assert calls == ["download"]
    assert [event.stage for event in events] == ["models-checking", "models-downloading", "models-ready"]
    assert manager.models_ready() is True


def test_docling_model_manager_skips_download_when_ready(tmp_path: Path) -> None:
    calls: list[str] = []
    manager = DoclingModelManager(cache_root=tmp_path, downloader=lambda _progress: calls.append("download"))
    manager.mark_ready()
    events: list[DoclingModelStatus] = []

    manager.ensure_models(events.append)

    assert calls == []
    assert [event.stage for event in events] == ["models-checking", "models-ready"]
    assert events[-1].message == "Docling models ready"
