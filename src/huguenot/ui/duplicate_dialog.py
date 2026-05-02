from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from huguenot.application import DuplicateDecision, DuplicatePDF

DUPLICATE_ADD_ANYWAY_LABEL = "Add Anyway"
DUPLICATE_SKIP_LABEL = "Skip"
DUPLICATE_SKIP_ALL_LABEL_TEMPLATE = "Skip all {count} duplicates"


def ask_duplicate_decision(parent: Any, duplicate: DuplicatePDF, remaining_duplicates: int) -> DuplicateDecision:
    dialog = tk.Toplevel(parent)
    dialog.title("Duplicate citation")
    dialog.transient(parent)
    dialog.resizable(False, False)
    decision = tk.StringVar(value=DuplicateDecision.SKIP.value)
    is_closed = False

    def release_grab() -> None:
        try:
            if dialog.grab_current() is dialog:
                dialog.grab_release()
        except tk.TclError:
            return

    def choose(value: DuplicateDecision) -> None:
        nonlocal is_closed
        decision.set(value.value)
        if is_closed:
            return
        is_closed = True
        release_grab()
        dialog.destroy()

    dialog.protocol("WM_DELETE_WINDOW", lambda: choose(DuplicateDecision.SKIP))
    outer = ttk.Frame(dialog, padding=14)
    outer.pack(fill="both", expand=True)
    message = (
        "This PDF appears to duplicate an authority already in the list.\n\n"
        f"New file: {duplicate.path.name}\n"
        f"Detected citation: {duplicate.title}\n"
        f"Existing citation: {duplicate.duplicate_title}\n\n"
        "Do you want to add it anyway or skip it?"
    )
    ttk.Label(outer, text=message, justify="left", wraplength=460).pack(anchor="w")
    actions = ttk.Frame(outer)
    actions.pack(fill="x", pady=(14, 0))

    add_anyway = ttk.Button(
        actions,
        text=DUPLICATE_ADD_ANYWAY_LABEL,
        command=lambda: choose(DuplicateDecision.ADD_ANYWAY),
    )
    add_anyway.pack(side="right", padx=(8, 0))
    skip = ttk.Button(actions, text=DUPLICATE_SKIP_LABEL, command=lambda: choose(DuplicateDecision.SKIP))
    skip.pack(side="right", padx=(8, 0))
    ttk.Button(
        actions,
        text=DUPLICATE_SKIP_ALL_LABEL_TEMPLATE.format(count=remaining_duplicates),
        command=lambda: choose(DuplicateDecision.SKIP_ALL),
    ).pack(side="right")

    try:
        dialog.update_idletasks()
        dialog.wait_visibility()
        dialog.grab_set()
        dialog.lift()
        skip.focus_set()
        parent.wait_window(dialog)
    finally:
        release_grab()
    return DuplicateDecision(decision.get())
