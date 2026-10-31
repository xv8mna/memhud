"""Starting the program, and the tray icon that holds it together while it runs."""

from __future__ import annotations

import contextlib
import ctypes
import logging
import logging.handlers
import os
import sys
import traceback
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from . import APP_FOLDER, APP_NAME, COMMAND
from .config import Config, load, save
from .memory import read_memory, read_programs
from .overlay import OverlayWindow
from .rows import build_rows
from .settings_window import SettingsWindow

log = logging.getLogger("memhud")

_ALREADY_EXISTS = 183  # ERROR_ALREADY_EXISTS
# tools\build.py: the built program starts, updates the overlay and ends. Exit code 4: an unexpected error
STARTUP_CHECK = "MEMHUD_STARTUP_CHECK"
_errors = 0  # unexpected errors since the start


class Tray:
    """The running program: a timer reads the memory, and the overlay and the tray icon show it."""

    def __init__(self, app: QApplication, config: Config) -> None:
        self.config = config
        self.overlay = OverlayWindow(config)
        self.settings: SettingsWindow | None = None  # made when it is first opened
        self.timer = QTimer(interval=config.interval_ms, timeout=self.update)
        self._saver = QTimer(singleShot=True, interval=500, timeout=self.save)  # not with every step of a spin box
        self._shown = QAction("Show overlay", checkable=True, checked=True, toggled=self.overlay.setVisible)
        self.menu = QMenu()
        self.menu.addAction(self._shown)
        self.menu.addAction("Settings…", self.open_settings)
        self.menu.addSeparator()
        self.menu.addAction("Quit", app.quit)
        self.icon = QSystemTrayIcon(_icon())
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._icon_clicked)
        app.aboutToQuit.connect(self._quitting)

    def start(self) -> None:
        self.update()
        self.overlay.show()
        self.icon.show()
        self.timer.start()

    def update(self) -> None:
        rows = build_rows(read_memory(), read_programs(self.config.program_memory), self.config)
        self.overlay.set_rows(rows)
        self.overlay.hold_place()
        self.icon.setToolTip("\n".join(f"{row.label} {row.value}" for row in rows[:2]) or APP_NAME)

    def open_settings(self) -> None:
        if self.settings is None:
            self.settings = SettingsWindow(self.config)
            self.settings.changed.connect(self._settings_changed)
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def _settings_changed(self) -> None:
        self.timer.setInterval(self.config.interval_ms)
        self.overlay.apply_config()
        self.update()
        self._saver.start()

    def save(self) -> None:
        try:
            save(self.config)
        except OSError as error:  # a setting less, no reason to stop
            log.warning("The settings were not saved: %s", error)

    def _icon_clicked(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.open_settings()

    def _quitting(self) -> None:
        if self._saver.isActive():
            self.save()
        self.icon.hide()


def main() -> int:
    _setup_logging()
    sys.excepthook = _excepthook
    _set_windows_app_id()
    QApplication.setApplicationName(APP_NAME)
    app = QApplication.instance() or QApplication(sys.argv)
    _set_look(app)
    app.setWindowIcon(_icon())
    app.setQuitOnLastWindowClosed(False)  # the settings window can close, the overlay has no close button
    check = bool(os.environ.get(STARTUP_CHECK))
    if not check and _already_runs():
        QMessageBox.information(None, APP_NAME, f"{APP_NAME} already runs. Its icon is in the notification area.")
        return 0
    tray = Tray(app, load())
    tray.start()
    if check:
        QTimer.singleShot(2500, lambda: app.exit(4 if _errors else 0))
    return app.exec()


def _set_look(app: QApplication) -> None:
    app.setStyle("Fusion")  # built in: the Windows download has no other styles
    # In dark mode Windows gives check boxes a blue base. Fusion fills the whole box with the base,
    # so a box that is not ticked would look ticked.
    app.setPalette(app.palette(), "QCheckBox")


def _already_runs() -> bool:
    """Whether another copy runs: autostart and a start by hand must not give two overlays. The named
    mutex goes away by itself when this program ends, however it ends."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW(None, False, f"Local\\{APP_NAME}")
    return ctypes.get_last_error() == _ALREADY_EXISTS


def _icon() -> QIcon:
    return QIcon(draw_icon(64))


def draw_icon(size: int) -> QPixmap:
    """Three bars, drawn here so that the program needs no image file."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 64, size / 64)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#20242C"))
    painter.drawRoundedRect(0, 0, 64, 64, 12, 12)
    for number, (height, color) in enumerate(((26, "#4CC38A"), (40, "#FFC83D"), (54, "#FF5A5A"))):
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(7 + number * 18, 59 - height, 14, height, 3, 3)
    painter.end()
    return pixmap


def _setup_logging() -> None:
    folder = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / APP_FOLDER
    try:
        folder.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            folder / f"{COMMAND}.log", maxBytes=1_000_000, backupCount=1, encoding="utf-8"
        )
    except OSError:
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)


def _excepthook(kind, value, tb) -> None:
    """Unexpected errors go to the log file only: a message box would take the focus from a game."""
    global _errors
    _errors += 1
    log.error("Unexpected error:\n%s", "".join(traceback.format_exception(kind, value, tb)))


def _set_windows_app_id() -> None:
    """Show the app's own icon in the taskbar instead of Python's."""
    with contextlib.suppress(OSError, AttributeError):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{APP_NAME}.Desktop")


if __name__ == "__main__":
    raise SystemExit(main())
