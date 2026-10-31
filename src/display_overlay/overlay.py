"""The window that shows the rows above everything else on the screen.

A game under it must not notice it: the window takes no clicks and no keys, and it never becomes
the active window. It is a normal window of its own and doesn't touch the game. That also sets its
limit: Windows gives a game in exclusive fullscreen the whole screen, so the window may not show
there. Borderless mode works.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPaintEvent, QScreen
from PySide6.QtWidgets import QWidget

from . import APP_NAME
from .config import Config
from .rows import ALARM, NORMAL, WARNING, Row

_FONT = "Consolas"  # same width for all digits: the numbers must not move when they change
_FLAGS = (
    Qt.WindowType.Tool  # not in the taskbar and not in Alt+Tab
    | Qt.WindowType.FramelessWindowHint
    | Qt.WindowType.WindowStaysOnTopHint
    | Qt.WindowType.WindowTransparentForInput  # clicks go to the window below
    | Qt.WindowType.WindowDoesNotAcceptFocus
    | Qt.WindowType.NoDropShadowWindowHint
)

_user32 = ctypes.WinDLL("user32")
_user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND] + [ctypes.c_int] * 4 + [wintypes.UINT]
_TOPMOST = -1  # HWND_TOPMOST
_NO_SIZE, _NO_MOVE, _NO_ACTIVATE = 0x0001, 0x0002, 0x0010


class OverlayWindow(QWidget):
    def __init__(self, config: Config) -> None:
        super().__init__(None, _FLAGS)
        self.config = config
        self.rows: list[Row] = []
        self.setWindowTitle(APP_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.apply_config()

    def apply_config(self) -> None:
        """Draws the window again after a change of the settings."""
        self.setFont(QFont(_FONT, self.config.font_size))
        self._fit()
        self.update()

    def set_rows(self, rows: list[Row]) -> None:
        if rows != self.rows:
            self.rows = rows
            self._fit()
            self.update()

    def hold_place(self) -> None:
        """Back to the corner and to the top, on every update. A game can change the size of the
        monitor, a monitor can go away, and a later always-on-top window comes above this one."""
        self._place()
        if self.isVisible():
            _user32.SetWindowPos(int(self.winId()), _TOPMOST, 0, 0, 0, 0, _NO_SIZE | _NO_MOVE | _NO_ACTIVATE)

    def _padding(self) -> int:
        return self.fontMetrics().height() // 2

    def _fit(self) -> None:
        """The size that the text needs. A window without rows stays, small and empty."""
        metrics = self.fontMetrics()
        labels = max((metrics.horizontalAdvance(row.label) for row in self.rows), default=0)
        values = max((metrics.horizontalAdvance(row.value) for row in self.rows), default=0)
        if self.rows:
            width = 2 * self._padding() + labels + metrics.horizontalAdvance("  ") + values
            self.setFixedSize(width, 2 * self._padding() + len(self.rows) * metrics.height())
        else:
            self.setFixedSize(1, 1)
        self._place()

    def _place(self) -> None:
        """In the corner of the whole monitor: a game covers the taskbar too."""
        area = self._screen().geometry()
        left = area.left() + self.config.margin_x
        right = area.left() + area.width() - self.config.margin_x - self.width()
        top = area.top() + self.config.margin_y
        bottom = area.top() + area.height() - self.config.margin_y - self.height()
        self.move(left if self.config.corner.endswith("left") else right, top if self.config.corner.startswith("top") else bottom)

    def _screen(self) -> QScreen:
        """The chosen monitor, or the main monitor when that one is gone."""
        for screen in QGuiApplication.screens():
            if screen.name() == self.config.screen:
                return screen
        return QGuiApplication.primaryScreen()

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.rows:
            return
        colors = {
            NORMAL: self.config.text_color,
            WARNING: self.config.warning_color,
            ALARM: self.config.alarm_color,
        }
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = QColor(self.config.background_color)
        background.setAlpha(round(self.config.background_opacity * 255 / 100))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(self.rect(), self._padding() / 2, self._padding() / 2)
        metrics = self.fontMetrics()
        for number, row in enumerate(self.rows):
            baseline = self._padding() + metrics.ascent() + number * metrics.height()
            painter.setPen(QColor(colors[row.level]))
            painter.drawText(self._padding(), baseline, row.label)
            painter.drawText(self.width() - self._padding() - metrics.horizontalAdvance(row.value), baseline, row.value)
