import json

from memhud.config import VERSION, Config, load, save


def test_no_file_gives_the_defaults(tmp_path):
    assert load(tmp_path / "settings.json") == Config()


def test_save_and_load_give_the_same_settings(tmp_path):
    file = tmp_path / "folder" / "settings.json"
    config = Config(
        corner="bottom-left",
        font_size=20,
        text_color="#123456",
        watch_programs=["a", "b"],
        show_ram=False,
        program_memory="commit",
    )
    save(config, file)
    assert load(file) == config
    assert json.loads(file.read_text(encoding="utf-8"))["version"] == VERSION
    assert [path.name for path in file.parent.iterdir()] == ["settings.json"]


def test_a_damaged_file_gives_the_defaults(tmp_path):
    file = tmp_path / "settings.json"
    file.write_text("{ this is no json", encoding="utf-8")
    assert load(file) == Config()
    file.write_text("[1, 2, 3]", encoding="utf-8")
    assert load(file) == Config()


def test_a_wrong_setting_keeps_its_default_and_the_others_stay(tmp_path):
    file = tmp_path / "settings.json"
    saved = {
        "font_size": "large",
        "corner": "middle",
        "program_memory": "disk",
        "text_color": "red",
        "show_ram": 1,
        "top_count": True,
        "watch_programs": [1, 2],
        "margin_x": 40,
        "not_a_setting": 1,
    }
    file.write_text(json.dumps(saved), encoding="utf-8")
    assert load(file) == Config(margin_x=40)


def test_a_number_out_of_range_moves_to_the_end_of_the_range(tmp_path):
    file = tmp_path / "settings.json"
    file.write_text(json.dumps({"font_size": 500, "interval_ms": 1, "background_opacity": -5}), encoding="utf-8")
    assert load(file) == Config(font_size=48, interval_ms=250, background_opacity=0)
