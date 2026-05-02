from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from huguenot import __version__


@dataclass(frozen=True)
class AboutMetadata:
    application_name: str
    version: str
    license_notice: str
    author: str
    contact: str


ABOUT_METADATA = AboutMetadata(
    application_name="Huguenot Inn",
    version=__version__,
    license_notice="Licensed under the GNU General Public License v3.0 (GPLv3).",
    author="Nikhil Somaru",
    contact="nikhil@capebar.co.za",
)


def app_icon_path() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / "assets" / "huguenot-inn-icon.png"
    return Path(__file__).resolve().parents[3] / "packaging" / "assets" / "huguenot-inn-icon.png"


def about_icon_path() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / "assets" / "huguenot-inn-icon-64.png"
    return Path(__file__).resolve().parents[3] / "packaging" / "assets" / "huguenot-inn-icon-64.png"
