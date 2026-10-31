"""The settings, and the file of the user that holds them. No Qt here."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import APP_FOLDER

VERSION = 1  # of the file: raise it when a setting changes its meaning
CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")
MEASURES = ("ram", "commit")  # what the numbers of the programs count: see read_programs
_CHOICES = {"corner": CORNERS, "program_memory": MEASURES}
_COLOR = re.compile(r"#[0-9a-fA-F]{6}")
_RANGES = {
    "top_count": (1, 8),
    "margin_x": (0, 4000),
    "margin_y": (0, 4000),
    "font_size": (6, 48),
    "background_opacity": (0, 100),
    "warning_percent": (1, 100),
    "alarm_percent": (1, 100),
    "interval_ms": (250, 10000),
}


@dataclass
class Config:
    # What the overlay shows
    show_ram: bool = True
    show_commit: bool = True
    show_top: bool = True
    top_count: int = 3
    program_memory: str = "ram"
    show_watch: bool = True
    watch_label: str = "Group"
    watch_programs: list[str] = field(default_factory=list)  # empty: no line for the group
    # Where: an empty screen is the main monitor
    screen: str = ""
    corner: str = "top-right"
    margin_x: int = 16
    margin_y: int = 16
    # How it looks
    font_size: int = 11
    text_color: str = "#FFFFFF"
    background_color: str = "#000000"
    background_opacity: int = 55
    # When a row changes its color
    warning_percent: int = 80
    warning_color: str = "#FFC83D"
    alarm_percent: int = 90
    alarm_color: str = "#FF5A5A"
    interval_ms: int = 1000


def settings_file() -> Path:
    return Path(os.environ.get("APPDATA") or Path.home()) / APP_FOLDER / "settings.json"


def load(file: Path | None = None) -> Config:
    """The saved settings. A setting that is missing or wrong keeps its default: a damaged file
    must not stop the overlay."""
    config = Config()
    try:
        saved = json.loads((file or settings_file()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return config
    if isinstance(saved, dict):
        for item in fields(Config):
            if item.name in saved:
                setattr(config, item.name, _checked(item.name, saved[item.name], getattr(config, item.name)))
    return config


def save(config: Config, file: Path | None = None) -> None:
    """Writes a new file first and then swaps it in: a full disk can't damage the old one."""
    file = file or settings_file()
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_suffix(".tmp")
    temporary.write_text(json.dumps({"version": VERSION, **asdict(config)}, indent=2), encoding="utf-8")
    temporary.replace(file)


def _checked(name: str, value: object, default: object) -> object:
    """``value`` if the setting ``name`` can use it, else ``default``. A number that is out of range
    moves to the end of the range."""
    if type(value) is not type(default):  # also keeps True out of the numbers
        return default
    if name in _RANGES:
        low, high = _RANGES[name]
        return min(max(value, low), high)
    if name.endswith("_color") and not _COLOR.fullmatch(value):
        return default
    if name in _CHOICES and value not in _CHOICES[name]:
        return default
    if isinstance(value, list) and not all(isinstance(item, str) for item in value):
        return default
    return value
