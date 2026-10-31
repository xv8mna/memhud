from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QPushButton, QSpinBox

from display_overlay.config import Config
from display_overlay.settings_window import ColorButton, SettingsWindow


def settings(qtbot, **values) -> SettingsWindow:
    window = SettingsWindow(Config(**values))
    qtbot.addWidget(window)
    return window


def test_it_opens_with_the_values_of_the_config(qtbot):
    window = settings(qtbot, show_ram=False, font_size=20, corner="bottom-left", watch_programs=["a", "b"])
    assert not window.findChild(QCheckBox, "show_ram").isChecked()
    assert window.findChild(QSpinBox, "font_size").value() == 20
    assert window.findChild(QComboBox, "corner").currentData() == "bottom-left"
    assert window.findChild(QLineEdit, "watch_programs").text() == "a, b"


def test_a_change_goes_to_the_config_and_tells_the_program(qtbot):
    window = settings(qtbot)
    with qtbot.waitSignal(window.changed):
        window.findChild(QCheckBox, "show_ram").click()
    assert window.config.show_ram is False
    with qtbot.waitSignal(window.changed):
        window.findChild(QSpinBox, "font_size").setValue(30)
    assert window.config.font_size == 30
    with qtbot.waitSignal(window.changed):
        window.findChild(QComboBox, "corner").setCurrentIndex(3)
    assert window.config.corner == "bottom-right"
    with qtbot.waitSignal(window.changed):
        window.findChild(QComboBox, "program_memory").setCurrentIndex(1)
    assert window.config.program_memory == "commit"


def test_program_names_become_a_list(qtbot):
    window = settings(qtbot)
    window.findChild(QLineEdit, "watch_programs").textEdited.emit(" editor , node,, ")
    assert window.config.watch_programs == ["editor", "node"]


def test_a_picked_color_goes_to_the_config(qtbot):
    window = settings(qtbot)
    window.findChild(ColorButton, "text_color").picked.emit("#123456")
    assert window.config.text_color == "#123456"


def test_the_monitor_list_has_the_main_monitor_first(qtbot):
    window = settings(qtbot)
    window.show()
    box = window.findChild(QComboBox, "screen")
    assert box.itemData(0) == ""
    assert box.count() >= 2


def test_the_window_leaves_room_for_the_monitor_names(qtbot):
    box = settings(qtbot).findChild(QComboBox, "screen")  # not shown yet: the layout needs the names before that
    assert box.count() >= 2
    assert box.sizeHint().width() > box.fontMetrics().horizontalAdvance(box.itemText(0))


def test_defaults_bring_back_all_settings_and_the_widgets(qtbot):
    window = settings(qtbot, font_size=30, show_ram=False, corner="bottom-left")
    with qtbot.waitSignal(window.changed):
        window.findChild(QPushButton, "defaults").click()
    assert window.config == Config()
    assert window.findChild(QSpinBox, "font_size").value() == Config().font_size
    assert window.findChild(QCheckBox, "show_ram").isChecked()
