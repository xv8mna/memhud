from display_overlay.config import Config
from display_overlay.memory import Memory
from display_overlay.rows import ALARM, NORMAL, WARNING, Row, build_rows

GB = 1024**3
MEMORY = Memory(ram_used=8 * GB, ram_total=32 * GB, commit_used=16 * GB, commit_limit=64 * GB)


def test_all_rows_top_to_bottom():
    rows = build_rows(MEMORY, {"game": 20 * GB, "editor": 6 * GB}, Config())
    assert rows == [
        Row("RAM", "8.0 / 32.0 GB  25%"),
        Row("COMMIT", "16.0 / 64.0 GB  25%"),
        Row("game", "20.0 GB"),
        Row("editor", "6.0 GB"),
    ]


def test_settings_turn_rows_off():
    config = Config(show_ram=False, show_commit=False, show_top=False, show_watch=False)
    assert build_rows(MEMORY, {"game": 20 * GB}, config) == []


def test_the_group_row_stays_without_the_top_list():
    config = Config(show_ram=False, show_commit=False, show_top=False, watch_label="Tools", watch_programs=["editor"])
    rows = build_rows(MEMORY, {"game": 20 * GB, "editor": 6 * GB}, config)
    assert [row.label for row in rows] == ["Tools"]


def test_a_row_changes_its_level_at_the_limits():
    config = Config(warning_percent=80, alarm_percent=90)
    levels = [build_rows(Memory(used, 1000, 0, 1000), {}, config)[0].level for used in (799, 800, 899, 900, 1000)]
    assert levels == [NORMAL, WARNING, WARNING, ALARM, ALARM]


def test_each_row_has_its_own_level():
    ram, commit = build_rows(Memory(1 * GB, 32 * GB, 95 * GB, 100 * GB), {}, Config())
    assert (ram.level, commit.level) == (NORMAL, ALARM)


def test_a_long_program_name_is_cut():
    label = build_rows(MEMORY, {"a_very_long_name_of_a_program": GB}, Config(show_ram=False, show_commit=False))[0].label
    assert len(label) == 18
    assert label.endswith("…")


def test_no_commit_limit_gives_no_error():
    assert build_rows(Memory(0, 0, 0, 0), {}, Config())[0].level == NORMAL
