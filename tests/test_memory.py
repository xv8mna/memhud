import sys
from pathlib import Path

from display_overlay.memory import Program, read_memory, read_programs, top_programs

GB = 1024**3


def test_read_memory_gives_believable_numbers():
    memory = read_memory()
    assert 0 < memory.ram_used < memory.ram_total
    assert 0 < memory.commit_used < memory.commit_limit
    assert memory.ram_total <= memory.commit_limit + GB  # the commit limit is RAM plus page file


def test_read_programs_adds_up_by_name_without_exe():
    programs = read_programs()
    assert programs[Path(sys.executable).stem] > 0
    assert not any(key.lower().endswith(".exe") for key in programs)


def test_read_programs_sees_the_services_of_windows():
    assert read_programs()["svchost"] > 0


def test_the_compressed_memory_of_windows_is_no_program():
    assert "Memory Compression" not in read_programs()


def test_read_programs_counts_ram_or_commit():
    ram, commit = read_programs("ram"), read_programs("commit")
    assert 0 < sum(ram.values()) < read_memory().ram_total
    assert sum(commit.values()) > sum(ram.values())  # what a program holds in RAM, it has also reserved


def test_top_programs_are_largest_first_and_cut_at_count():
    programs = {"small": 1 * GB, "large": 9 * GB, "middle": 5 * GB}
    assert top_programs(programs, 2, "", []) == [Program("large", 9 * GB), Program("middle", 5 * GB)]


def test_the_group_counts_as_one_program():
    programs = {"game": 5 * GB, "editor": 2 * GB, "node": 4 * GB}
    assert top_programs(programs, 1, "Tools", ["editor", "node"]) == [Program("Tools", 6 * GB)]


def test_the_group_stays_last_when_it_is_too_small_for_the_top():
    programs = {"game": 9 * GB, "browser": 5 * GB, "editor": 1 * GB}
    assert top_programs(programs, 2, "Tools", ["editor"]) == [
        Program("game", 9 * GB),
        Program("browser", 5 * GB),
        Program("Tools", 1 * GB),
    ]


def test_the_group_alone_with_no_top_list():
    assert top_programs({"game": 9 * GB, "editor": 1 * GB}, 0, "Tools", ["editor"]) == [Program("Tools", 1 * GB)]


def test_a_group_that_does_not_run_has_no_line():
    assert top_programs({"game": 9 * GB}, 3, "Tools", ["editor"]) == [Program("game", 9 * GB)]


def test_group_names_ignore_upper_and_lower_case():
    assert top_programs({"Editor": 1 * GB}, 3, "Tools", ["editor"]) == [Program("Tools", 1 * GB)]
