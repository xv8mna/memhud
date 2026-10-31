import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication

from memhud.config import Config
from memhud.overlay import OverlayWindow
from memhud.rows import ALARM, Row

ROWS = [Row("RAM", "8.0 / 32.0 GB  25%"), Row("COMMIT", "60.0 / 64.0 GB  94%", ALARM)]


def overlay(qtbot, **settings) -> OverlayWindow:
    window = OverlayWindow(Config(**settings))
    qtbot.addWidget(window)
    window.set_rows(ROWS)
    return window


def test_it_takes_no_input_and_no_focus_and_stays_on_top(qtbot):
    flags = overlay(qtbot).windowFlags()
    assert flags & Qt.WindowType.WindowTransparentForInput
    assert flags & Qt.WindowType.WindowDoesNotAcceptFocus
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert flags & Qt.WindowType.Tool


def test_more_rows_and_larger_text_make_it_larger(qtbot):
    window = overlay(qtbot)
    height, width = window.height(), window.width()
    window.set_rows([*ROWS, Row("game", "20.0 GB")])
    assert window.height() > height
    window.config.font_size = 22
    window.apply_config()
    assert window.width() > width


@pytest.mark.parametrize("corner", ["top-left", "top-right", "bottom-left", "bottom-right"])
def test_it_sits_in_its_corner(qtbot, corner):
    window = overlay(qtbot, corner=corner, margin_x=10, margin_y=20)
    area = QGuiApplication.primaryScreen().geometry()
    left = area.left() + 10 if corner.endswith("left") else area.left() + area.width() - 10 - window.width()
    top = area.top() + 20 if corner.startswith("top") else area.top() + area.height() - 20 - window.height()
    assert (window.x(), window.y()) == (left, top)


def test_a_monitor_that_is_gone_means_the_main_monitor(qtbot):
    window = overlay(qtbot, screen="not a monitor", corner="top-left", margin_x=0, margin_y=0)
    area = QGuiApplication.primaryScreen().geometry()
    assert (window.x(), window.y()) == (area.left(), area.top())


def colors_in(window) -> set[str]:
    image = window.grab().toImage()
    return {
        QColor(image.pixel(x, y)).name().upper() for x in range(image.width()) for y in range(image.height())
    }


def test_a_row_at_the_alarm_limit_has_the_alarm_color(qtbot):
    window = overlay(qtbot, alarm_color="#00FF00", background_opacity=0)
    assert "#00FF00" in colors_in(window)
    window.set_rows([Row("RAM", "1.0 / 32.0 GB   3%")])
    assert "#00FF00" not in colors_in(window)


def test_no_rows_draw_nothing(qtbot):
    window = overlay(qtbot)
    window.set_rows([])
    assert (window.width(), window.height()) == (1, 1)
