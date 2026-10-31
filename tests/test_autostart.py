import sys
import winreg

import pytest

from memhud import APP_NAME, autostart

PARENT = r"Software\MemHUDTests"


@pytest.fixture
def run_key(monkeypatch):
    """A key of its own: the tests must not touch the real Run key."""
    key = rf"{PARENT}\Run"
    monkeypatch.setattr(autostart, "RUN_KEY", key)
    yield key
    for name in (key, PARENT):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, name)
        except FileNotFoundError:
            pass


def test_turn_on_and_off(run_key):
    assert not autostart.is_on()
    autostart.turn_on()
    assert autostart.is_on()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key) as key:
        assert winreg.QueryValueEx(key, APP_NAME)[0] == autostart.command()
    autostart.turn_off()
    assert not autostart.is_on()


def test_turn_off_when_it_is_off(run_key):
    autostart.turn_off()
    assert not autostart.is_on()


def test_the_command_has_no_console_window(monkeypatch):
    monkeypatch.setattr(sys, "executable", r"C:\Some Folder\Scripts\python.exe")
    assert autostart.command() == r'"C:\Some Folder\Scripts\pythonw.exe" -m memhud'


def test_the_download_starts_its_own_exe(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Some Folder\MemHUD\MemHUD.exe")
    assert autostart.command() == r'"C:\Some Folder\MemHUD\MemHUD.exe"'


def test_a_command_that_is_too_long_is_refused(run_key, monkeypatch):
    monkeypatch.setattr(sys, "executable", "C:\\" + "x" * 300 + "\\python.exe")
    with pytest.raises(ValueError, match="too long"):
        autostart.turn_on()
    assert not autostart.is_on()
