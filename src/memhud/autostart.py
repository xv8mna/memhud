"""Start with Windows: one value in the Run key of the user. It needs no admin rights, and Task
Manager lists it under Startup. The value itself says whether this is on, so a value that the user
removed in another way doesn't show as on here."""

from __future__ import annotations

import contextlib
import sys
import winreg
from pathlib import Path

from . import APP_NAME

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
MAX_COMMAND = 260  # characters: Windows runs no longer command line from this key


def command() -> str:
    """The command line that starts this program without a console window."""
    if getattr(sys, "frozen", False):  # the Windows download: the program is the .exe itself
        return f'"{sys.executable}"'
    python = Path(sys.executable)
    if python.name.lower() == "python.exe":
        python = python.with_name("pythonw.exe")
    return f'"{python}" -m memhud'


def is_on() -> bool:
    with contextlib.suppress(OSError), winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.QueryValueEx(key, APP_NAME)
        return True
    return False


def turn_on() -> None:
    text = command()
    if len(text) > MAX_COMMAND:
        raise ValueError(f"The path of this program is too long: {len(text)} characters, and Windows allows {MAX_COMMAND}")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, text)


def turn_off() -> None:
    with (
        contextlib.suppress(FileNotFoundError),
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key,
    ):
        winreg.DeleteValue(key, APP_NAME)
