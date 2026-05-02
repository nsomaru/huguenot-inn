from pathlib import Path
from typing import Any

from huguenot.application.duplicates import DuplicateDecision, DuplicatePDF, plan_pdf_additions
from huguenot.domain import PDFItem


def test_plan_pdf_additions_skips_existing_paths_before_duplicate_citation(tmp_path: Path) -> None:
    existing_path = tmp_path / "existing.pdf"
    existing_path.write_bytes(b"pdf")

    result = plan_pdf_additions(
        [PDFItem(existing_path, "S v Makwanyane [1995] ZACC 3")],
        [existing_path],
        detect_title=lambda path: "S v Makwanyane [1995] ZACC 3",
        decide_duplicate=lambda _duplicate, _remaining: DuplicateDecision.ADD_ANYWAY,
    )

    assert result.added == []
    assert result.skipped_existing_paths == [existing_path.resolve()]
    assert result.duplicates == []


def test_plan_pdf_additions_handles_add_skip_and_skip_all(tmp_path: Path) -> None:
    existing_path = tmp_path / "existing.pdf"
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    third = tmp_path / "third.pdf"
    for path in (existing_path, first, second, third):
        path.write_bytes(b"pdf")

    decisions = iter([DuplicateDecision.ADD_ANYWAY, DuplicateDecision.SKIP_ALL])
    result = plan_pdf_additions(
        [PDFItem(existing_path, "S v Makwanyane [1995] ZACC 3")],
        [first, second, third],
        detect_title=lambda _path: " S   v Makwanyane [1995] ZACC 3 ",
        decide_duplicate=lambda _duplicate, _remaining: next(decisions),
    )

    assert [item.path for item in result.added] == [first]
    assert len(result.duplicates) == 3
    assert [duplicate.path for duplicate in result.skipped_duplicates] == [second, third]


def test_duplicate_modal_labels_match_prd() -> None:
    from huguenot.ui.app import (
        DUPLICATE_ADD_ANYWAY_LABEL,
        DUPLICATE_SKIP_ALL_LABEL_TEMPLATE,
        DUPLICATE_SKIP_LABEL,
    )

    assert DUPLICATE_ADD_ANYWAY_LABEL == "Add Anyway"
    assert DUPLICATE_SKIP_LABEL == "Skip"
    assert DUPLICATE_SKIP_ALL_LABEL_TEMPLATE.format(count=3) == "Skip all 3 duplicates"


def test_drop_duplicate_review_is_scheduled_after_idle(tmp_path: Path) -> None:
    from huguenot.ui.app import PDFCombinerNumbererTOCIndexApp

    pdf = tmp_path / "duplicate.pdf"
    pdf.write_bytes(b"pdf")
    app = PDFCombinerNumbererTOCIndexApp.__new__(PDFCombinerNumbererTOCIndexApp)
    calls: list[tuple[str, Any]] = []

    app.parse_drop_files = lambda data: calls.append(("parse", data)) or [pdf]  # type: ignore[method-assign]
    app.add_paths = lambda paths: calls.append(("add", paths))  # type: ignore[method-assign]
    app.after_idle = lambda callback, *args: calls.append(("after_idle", (callback, args)))  # type: ignore[method-assign]

    app.on_drop(type("DropEvent", (), {"data": str(pdf)})())

    assert calls == [("parse", str(pdf)), ("after_idle", (app.add_paths, ([pdf],)))]

    callback, args = calls[1][1]
    callback(*args)

    assert calls[-1] == ("add", [pdf])


def test_duplicate_dialog_waits_until_visible_before_grab_and_releases_grab(monkeypatch, tmp_path: Path) -> None:
    from huguenot.ui import duplicate_dialog

    events: list[str] = []

    class FakeParent:
        def wait_window(self, dialog) -> None:
            events.append("parent.wait_window")
            dialog._buttons["Skip"].invoke()

    class FakeDialog:
        def __init__(self, parent) -> None:
            self.parent = parent
            self._buttons = {}
            events.append("dialog.create")

        def title(self, _value: str) -> None:
            events.append("dialog.title")

        def transient(self, _parent) -> None:
            events.append("dialog.transient")

        def resizable(self, _width: bool, _height: bool) -> None:
            events.append("dialog.resizable")

        def protocol(self, _name: str, _command) -> None:
            events.append("dialog.protocol")

        def update_idletasks(self) -> None:
            events.append("dialog.update_idletasks")

        def wait_visibility(self) -> None:
            events.append("dialog.wait_visibility")

        def grab_set(self) -> None:
            events.append("dialog.grab_set")

        def grab_current(self):
            return self

        def grab_release(self) -> None:
            events.append("dialog.grab_release")

        def lift(self) -> None:
            events.append("dialog.lift")

        def destroy(self) -> None:
            events.append("dialog.destroy")

    class FakeStringVar:
        def __init__(self, value: str) -> None:
            self._value = value

        def set(self, value: str) -> None:
            self._value = value

        def get(self) -> str:
            return self._value

    class FakeWidget:
        def __init__(self, *args, **kwargs) -> None:
            self.parent = args[0] if args else None
            self.command = kwargs.get("command")
            self.text = kwargs.get("text")
            root = self.parent
            while root is not None and not hasattr(root, "_buttons"):
                root = getattr(root, "parent", None)
            if self.text and root is not None:
                root._buttons[self.text] = self

        def pack(self, *args, **kwargs):
            return None

        def focus_set(self) -> None:
            events.append(f"{self.text}.focus_set")

        def invoke(self) -> None:
            assert self.command is not None
            self.command()

    monkeypatch.setattr(duplicate_dialog.tk, "Toplevel", FakeDialog)
    monkeypatch.setattr(duplicate_dialog.tk, "StringVar", FakeStringVar)
    monkeypatch.setattr(duplicate_dialog.ttk, "Frame", FakeWidget)
    monkeypatch.setattr(duplicate_dialog.ttk, "Label", FakeWidget)
    monkeypatch.setattr(duplicate_dialog.ttk, "Button", FakeWidget)

    duplicate = DuplicatePDF(
        path=tmp_path / "new.pdf",
        title="S v Makwanyane [1995] ZACC 3",
        duplicate_title="S v Makwanyane [1995] ZACC 3",
        duplicate_path=tmp_path / "existing.pdf",
    )

    assert duplicate_dialog.ask_duplicate_decision(FakeParent(), duplicate, 2) is DuplicateDecision.SKIP
    assert events.index("dialog.wait_visibility") < events.index("dialog.grab_set")
    assert "dialog.grab_release" in events
