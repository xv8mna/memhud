import pytest
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QCheckBox, QSystemTrayIcon

from memhud import app as program
from memhud.config import Config, load, settings_file


@pytest.fixture
def tray(qtbot, monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    running = program.Tray(QApplication.instance(), Config())
    qtbot.addWidget(running.overlay)
    running.update()
    yield running
    running.timer.stop()
    running._saver.stop()
    running.icon.hide()
    if running.settings:
        running.settings.close()


def test_an_update_fills_the_overlay_and_the_tooltip(tray):
    assert [row.label for row in tray.overlay.rows][:2] == ["RAM", "COMMIT"]
    assert tray.icon.toolTip().startswith("RAM ")


def test_an_update_reads_what_the_settings_ask_for(tray, monkeypatch):
    asked = []
    monkeypatch.setattr(program, "read_programs", lambda measure: asked.append(measure) or {})
    tray.update()
    tray.config.program_memory = "commit"
    tray.update()
    assert asked == ["ram", "commit"]


def test_the_timer_keeps_the_overlay_up_to_date(tray, qtbot):
    tray.overlay.rows = []
    tray.timer.setInterval(10)
    tray.timer.start()
    qtbot.waitUntil(lambda: len(tray.overlay.rows) > 0, timeout=2000)


def test_a_click_on_the_icon_opens_one_settings_window(tray, qtbot):
    tray._icon_clicked(QSystemTrayIcon.ActivationReason.Trigger)
    window = tray.settings
    qtbot.addWidget(window)
    assert window.isVisible()
    tray._icon_clicked(QSystemTrayIcon.ActivationReason.Trigger)
    assert tray.settings is window


def test_a_right_click_opens_no_settings_window(tray):
    tray._icon_clicked(QSystemTrayIcon.ActivationReason.Context)
    assert tray.settings is None


def test_a_change_in_the_settings_reaches_the_overlay_the_timer_and_the_file(tray, qtbot):
    tray.config.show_ram = False
    tray.config.interval_ms = 2000
    tray._settings_changed()
    assert tray.overlay.rows[0].label == "COMMIT"
    assert tray.timer.interval() == 2000
    qtbot.waitUntil(settings_file().exists, timeout=2000)
    assert load().interval_ms == 2000


def test_the_menu_hides_and_shows_the_overlay(tray):
    tray.start()
    tray._shown.setChecked(False)
    assert not tray.overlay.isVisible()
    tray._shown.setChecked(True)
    assert tray.overlay.isVisible()


def test_a_check_box_that_is_not_ticked_does_not_look_ticked(qtbot):
    application = QApplication.instance()
    blue = QPalette(application.palette())
    blue.setColor(QPalette.ColorRole.Base, QColor("#0078D7"))
    application.setPalette(blue, "QCheckBox")  # what Windows does in dark mode
    box = QCheckBox()
    qtbot.addWidget(box)
    assert QApplication.palette(box).color(QPalette.ColorRole.Base) == QColor("#0078D7")
    program._set_look(application)
    assert QApplication.palette(box).color(QPalette.ColorRole.Base) == application.palette().color(QPalette.ColorRole.Base)


def test_the_icon_has_the_asked_size(qtbot):
    assert program.draw_icon(256).width() == 256


def test_a_second_copy_knows_of_the_first():
    program._already_runs()
    assert program._already_runs()
