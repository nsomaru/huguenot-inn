from __future__ import annotations

import tkinter as tk
from typing import Any


def configure_app_identity(root: Any, application_name: str) -> None:
    """Apply best-effort Tk application naming for window managers and macOS."""
    _try_tk_call(root, "tk", "appname", application_name)
    if _try_tk_call(root, "tk", "windowingsystem") != "aqua":
        return
    # Tk variants have exposed both names over time. Try the documented
    # capitalized form first and fall back without failing startup.
    if _try_tk_call(root, "tk::mac::SetApplicationName", application_name) is None:
        _try_tk_call(root, "tk::mac::setApplicationName", application_name)


def _try_tk_call(root: Any, *args: str) -> Any | None:
    try:
        return root.tk.call(*args)
    except tk.TclError:
        return None
