from pathlib import Path

import pytest

from huguenot.documents import (
    FontResolver,
    LibreOfficeConverter,
    PDFRenderer,
    RendererPreference,
    choose_pdf_renderer,
)


def test_font_resolver_prefers_times_new_roman_when_available() -> None:
    resolver = FontResolver(lambda: ["Arial", "Times New Roman", "Helvetica"])

    assert resolver.resolve().family == "Times New Roman"


def test_font_resolver_uses_selected_font_when_available() -> None:
    resolver = FontResolver(lambda: ["Arial", "Times New Roman", "Helvetica"])

    assert resolver.resolve("Arial").family == "Arial"


def test_renderer_preference_selects_reportlab_without_checking_libreoffice() -> None:
    assert (
        choose_pdf_renderer(RendererPreference(PDFRenderer.REPORTLAB), libreoffice_available=lambda: True)
        is PDFRenderer.REPORTLAB
    )


def test_renderer_preference_auto_uses_reportlab_by_default() -> None:
    assert (
        choose_pdf_renderer(RendererPreference(PDFRenderer.AUTOMATIC), libreoffice_available=lambda: True)
        is PDFRenderer.REPORTLAB
    )
    assert (
        choose_pdf_renderer(RendererPreference(PDFRenderer.AUTOMATIC), libreoffice_available=lambda: False)
        is PDFRenderer.REPORTLAB
    )


def test_renderer_preference_explicit_libreoffice_raises_when_unavailable() -> None:
    with pytest.raises(RuntimeError, match="LibreOffice"):
        choose_pdf_renderer(RendererPreference(PDFRenderer.LIBREOFFICE), libreoffice_available=lambda: False)


def test_libreoffice_locator_checks_path_and_macos_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/soffice" if name == "soffice" else None)
    assert LibreOfficeConverter.find_executable() == "/usr/local/bin/soffice"

    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr(
        Path, "exists", lambda self: str(self) == "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    )
    assert LibreOfficeConverter.find_executable() == "/Applications/LibreOffice.app/Contents/MacOS/soffice"


def test_libreoffice_locator_checks_linux_standard_locations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr(Path, "exists", lambda self: str(self) == "/usr/bin/libreoffice")

    assert LibreOfficeConverter.find_executable() == "/usr/bin/libreoffice"


def test_libreoffice_locator_checks_linux_flatpak_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr(
        Path,
        "exists",
        lambda self: str(self) == "/var/lib/flatpak/exports/bin/org.libreoffice.LibreOffice",
    )

    assert LibreOfficeConverter.find_executable() == "/var/lib/flatpak/exports/bin/org.libreoffice.LibreOffice"


def test_libreoffice_locator_checks_windows_install_locations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setenv("ProgramFiles", "C:/Program Files")
    monkeypatch.setenv("ProgramFiles(x86)", "C:/Program Files (x86)")
    monkeypatch.setenv("LOCALAPPDATA", "C:/Users/example/AppData/Local")
    expected = "C:/Program Files/LibreOffice/program/soffice.exe"
    monkeypatch.setattr(Path, "exists", lambda self: str(self).replace("\\", "/") == expected)

    executable = LibreOfficeConverter.find_executable()

    assert executable is not None
    assert executable.replace("\\", "/") == expected


def test_libreoffice_locator_returns_none_when_no_candidates_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr(Path, "exists", lambda _self: False)

    assert LibreOfficeConverter.find_executable() is None


def test_libreoffice_available_runs_mockable_usability_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return object()

    monkeypatch.setattr("subprocess.run", fake_run)
    converter = LibreOfficeConverter(executable="/Applications/LibreOffice.app/Contents/MacOS/soffice")

    assert converter.libreoffice_available() is True
    assert converter.libreoffice_available() is True
    assert calls == [["/Applications/LibreOffice.app/Contents/MacOS/soffice", "--headless", "--version"]]


def test_renderer_preference_auto_defaults_to_reportlab_without_libreoffice_probe() -> None:
    def fail_if_called() -> bool:
        raise AssertionError("Automatic renderer should not probe LibreOffice when ReportLab is the default")

    assert (
        choose_pdf_renderer(RendererPreference(PDFRenderer.AUTOMATIC), libreoffice_available=fail_if_called)
        is PDFRenderer.REPORTLAB
    )


def test_pdf_renderer_does_not_conflate_word_converter() -> None:
    assert "WORD" not in PDFRenderer.__members__
