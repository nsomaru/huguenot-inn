from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any


def root_identity_options(application_name: str) -> dict[str, str]:
    """Return Tk root options that name the application before Tk initializes."""
    return {"baseName": application_name}


def configure_app_identity(root: Any, application_name: str) -> None:
    """Apply best-effort Tk application naming for window managers and macOS."""
    _try_tk_call(root, "tk", "appname", application_name)
    if _try_tk_call(root, "tk", "windowingsystem") != "aqua":
        return
    # Tk variants have exposed both names over time. Try the documented
    # capitalized form first and fall back without failing startup.
    if _try_tk_call(root, "tk::mac::SetApplicationName", application_name) is None:
        _try_tk_call(root, "tk::mac::setApplicationName", application_name)


def configure_macos_quit(root: Any, command: Callable[[], object]) -> None:
    """Route macOS Command+Q through the app's normal close callback when supported."""
    if _try_tk_call(root, "tk", "windowingsystem") != "aqua":
        return
    try:
        root.createcommand("tk::mac::Quit", command)
    except (AttributeError, tk.TclError):
        return


def _try_tk_call(root: Any, *args: str) -> Any | None:
    try:
        return root.tk.call(*args)
    except tk.TclError:
        return None
