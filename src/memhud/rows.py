"""What the overlay writes: the numbers as rows of text, with their alarm level. No Qt here."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .memory import Memory, top_programs

NORMAL, WARNING, ALARM = range(3)
_MAX_NAME = 18  # characters: a long program name must not make the overlay wide


@dataclass(frozen=True)
class Row:
    label: str
    value: str
    level: int = NORMAL


def build_rows(memory: Memory, programs: dict[str, int], config: Config) -> list[Row]:
    """The rows that the settings ask for, top to bottom."""
    rows = []
    if config.show_ram:
        rows.append(_usage("RAM", memory.ram_used, memory.ram_total, config))
    if config.show_commit:
        rows.append(_usage("COMMIT", memory.commit_used, memory.commit_limit, config))
    top = top_programs(
        programs,
        config.top_count if config.show_top else 0,
        config.watch_label,
        config.watch_programs if config.show_watch else [],
    )
    return rows + [Row(_short(program.name), f"{_gb(program.size)} GB") for program in top]


def _usage(label: str, used: int, total: int, config: Config) -> Row:
    percent = 100 * used / total if total else 0.0
    level = NORMAL
    if percent >= config.warning_percent:
        level = WARNING
    if percent >= config.alarm_percent:
        level = ALARM
    return Row(label, f"{_gb(used)} / {_gb(total)} GB {percent:3.0f}%", level)


def _gb(size: int) -> str:
    return f"{size / 1024**3:.1f}"


def _short(name: str) -> str:
    return name if len(name) <= _MAX_NAME else name[: _MAX_NAME - 1] + "…"
