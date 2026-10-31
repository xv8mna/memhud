"""Makes the picture for the README, with sample numbers and no window on the screen.

Run it with ``python tools/screenshot.py docs/overlay.png``.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter
from PySide6.QtWidgets import QApplication

from display_overlay.config import Config
from display_overlay.memory import Memory
from display_overlay.overlay import OverlayWindow
from display_overlay.rows import build_rows

GB = 1024**3
MEMORY = Memory(ram_used=26 * GB, ram_total=32 * GB, commit_used=56 * GB, commit_limit=60 * GB)
PROGRAMS = {"game": 14 * GB, "browser": 5 * GB, "editor": 3 * GB, "chat": 1 * GB}


def main(path: str) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = OverlayWindow(Config(font_size=14))
    window.set_rows(build_rows(MEMORY, PROGRAMS, window.config))
    overlay = window.grab().toImage()
    margin = 24
    picture = QImage(overlay.width() + 2 * margin + 240, overlay.height() + 2 * margin, QImage.Format.Format_RGB32)
    painter = QPainter(picture)
    sky = QLinearGradient(0, 0, picture.width(), picture.height())
    sky.setColorAt(0, QColor("#39506B"))
    sky.setColorAt(1, QColor("#7A6A55"))
    painter.fillRect(picture.rect(), sky)
    painter.drawImage(QPoint(picture.width() - overlay.width() - margin, margin), overlay)
    painter.end()
    picture.save(path)
    app.quit()


if __name__ == "__main__":
    main(sys.argv[1])
