"""The settings window. The overlay is its preview: every change shows there at once."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields
from typing import Any

from PySide6.QtCore import Signal, SignalInstance
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPaintEvent, QPalette, QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, autostart
from .config import Config

_CORNERS = [
    ("Top left", "top-left"),
    ("Top right", "top-right"),
    ("Bottom left", "bottom-left"),
    ("Bottom right", "bottom-right"),
]
_PROGRAM_MEMORY = [("RAM", "ram"), ("Commit memory", "commit")]


class ColorButton(QPushButton):
    """Shows a color, and opens the color dialog when clicked."""

    picked = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.color = "#000000"
        self.setFixedWidth(64)
        self.clicked.connect(self._pick)

    def set_color(self, color: str) -> None:
        self.color = color
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Only the color: a style would shade the button, and the color must look as it is."""
        painter = QPainter(self)
        painter.setBrush(QColor(self.color))
        painter.setPen(self.palette().color(QPalette.ColorRole.Mid))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def _pick(self) -> None:
        color = QColorDialog.getColor(QColor(self.color), self, "Pick a color")
        if color.isValid():
            self.set_color(color.name())
            self.picked.emit(color.name())


class SettingsWindow(QWidget):
    changed = Signal()  # a setting in the config has a new value

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self._shows: list[Callable[[], None]] = []  # one per setting: puts its value in its widget
        self._showing = False  # a change comes from the config, not from the user
        self.setWindowTitle(f"{APP_NAME} settings")
        layout = QVBoxLayout(self)
        layout.addWidget(self._content_group())
        layout.addWidget(self._place_group())
        layout.addWidget(self._look_group())
        layout.addWidget(self._alarm_group())
        layout.addWidget(self._program_group())
        layout.addLayout(self._buttons())
        self._fill_monitors()  # here too: the width of the window must leave room for their names

    def showEvent(self, event: QShowEvent) -> None:
        """The monitors may have changed since the last time."""
        self._fill_monitors()
        super().showEvent(event)

    def _content_group(self) -> QGroupBox:
        group = QGroupBox("What is shown")
        form = QFormLayout(group)
        form.addRow(self._check("show_ram", "RAM"))
        form.addRow(self._check("show_commit", "Commit memory"))
        form.addRow(self._check("show_top", "Top programs"), self._number("top_count", 1, 8))
        form.addRow("Program numbers", self._choice("program_memory", _PROGRAM_MEMORY))
        form.addRow(self._check("show_watch", "Always show this group"))
        form.addRow("Name of the group", self._text("watch_label"))
        form.addRow("Its programs", self._names("watch_programs"))
        return group

    def _place_group(self) -> QGroupBox:
        group = QGroupBox("Position")
        form = QFormLayout(group)
        self._monitors = QComboBox(objectName="screen")
        self._monitors.currentIndexChanged.connect(self._monitor_changed)
        form.addRow("Monitor", self._monitors)
        form.addRow("Corner", self._choice("corner", _CORNERS))
        form.addRow("Distance from the side", self._number("margin_x", 0, 4000, " px"))
        form.addRow("Distance from the top or bottom", self._number("margin_y", 0, 4000, " px"))
        return group

    def _look_group(self) -> QGroupBox:
        group = QGroupBox("Look")
        form = QFormLayout(group)
        form.addRow("Text size", self._number("font_size", 6, 48, " pt"))
        form.addRow("Text color", self._color("text_color"))
        form.addRow("Background color", self._color("background_color"))
        form.addRow("Background opacity", self._number("background_opacity", 0, 100, " %"))
        return group

    def _alarm_group(self) -> QGroupBox:
        group = QGroupBox("Colors of RAM and commit memory")
        form = QFormLayout(group)
        form.addRow("Warning from", self._number("warning_percent", 1, 100, " %"))
        form.addRow("Warning color", self._color("warning_color"))
        form.addRow("Alarm from", self._number("alarm_percent", 1, 100, " %"))
        form.addRow("Alarm color", self._color("alarm_color"))
        return group

    def _program_group(self) -> QGroupBox:
        group = QGroupBox("Program")
        form = QFormLayout(group)
        form.addRow("Update every", self._number("interval_ms", 250, 10000, " ms"))
        self._autostart = QCheckBox("Start with Windows", objectName="autostart")
        self._autostart.setChecked(autostart.is_on())
        self._autostart.toggled.connect(self._set_autostart)
        form.addRow(self._autostart)
        return group

    def _buttons(self) -> QHBoxLayout:
        defaults = QPushButton("Defaults", objectName="defaults")
        defaults.clicked.connect(self._defaults)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        layout = QHBoxLayout()
        layout.addWidget(defaults)
        layout.addStretch()
        layout.addWidget(close)
        return layout

    def _check(self, name: str, text: str) -> QCheckBox:
        box = QCheckBox(text, objectName=name)
        self._bind(name, box.setChecked, box.toggled)
        return box

    def _number(self, name: str, low: int, high: int, suffix: str = "") -> QSpinBox:
        box = QSpinBox(objectName=name)
        box.setRange(low, high)
        box.setSuffix(suffix)
        self._bind(name, box.setValue, box.valueChanged)
        return box

    def _text(self, name: str) -> QLineEdit:
        edit = QLineEdit(objectName=name)
        self._bind(name, edit.setText, edit.textEdited)
        return edit

    def _names(self, name: str) -> QLineEdit:
        """A list of program names, as text with commas."""
        edit = QLineEdit(objectName=name)
        edit.setPlaceholderText("Names without .exe, with commas between them")

        def show(names: list[str]) -> None:
            edit.setText(", ".join(names))

        def read(text: str) -> list[str]:
            return [part.strip() for part in text.split(",") if part.strip()]

        self._bind(name, show, edit.textEdited, read)
        return edit

    def _color(self, name: str) -> ColorButton:
        button = ColorButton()
        button.setObjectName(name)
        self._bind(name, button.set_color, button.picked)
        return button

    def _choice(self, name: str, items: list[tuple[str, str]]) -> QComboBox:
        box = QComboBox(objectName=name)
        for text, value in items:
            box.addItem(text, value)

        def show(value: str) -> None:
            box.setCurrentIndex(max(box.findData(value), 0))

        self._bind(name, show, box.currentIndexChanged, box.itemData)
        return box

    def _bind(self, name: str, show: Callable[[Any], None], signal: SignalInstance, read: Callable | None = None) -> None:
        """Keeps one setting and one widget together. ``show`` puts a value in the widget, ``signal``
        tells of a change by the user, and ``read`` turns what it tells into a value of the setting."""

        def show_setting() -> None:
            show(getattr(self.config, name))

        def changed(value: Any) -> None:
            if not self._showing:
                setattr(self.config, name, read(value) if read else value)
                self.changed.emit()

        signal.connect(changed)
        self._shows.append(show_setting)
        self._show_all()

    def _show_all(self) -> None:
        self._showing = True
        for show in self._shows:
            show()
        self._showing = False

    def _fill_monitors(self) -> None:
        self._showing = True
        self._monitors.clear()
        self._monitors.addItem("Main monitor", "")
        for screen in QGuiApplication.screens():
            size = screen.size()
            self._monitors.addItem(f"{screen.name()} ({size.width()} × {size.height()})", screen.name())
        self._monitors.setCurrentIndex(max(self._monitors.findData(self.config.screen), 0))
        self._showing = False

    def _monitor_changed(self, index: int) -> None:
        if not self._showing:
            self.config.screen = self._monitors.itemData(index)
            self.changed.emit()

    def _defaults(self) -> None:
        """Back to the defaults, in the same config: the overlay holds it too."""
        for item in fields(Config):
            setattr(self.config, item.name, getattr(Config(), item.name))
        self._show_all()
        self._fill_monitors()
        self.changed.emit()

    def _set_autostart(self, on: bool) -> None:
        try:
            if on:
                autostart.turn_on()
            else:
                autostart.turn_off()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, APP_NAME, f"Windows did not take the change: {error}")
