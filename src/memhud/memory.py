"""The numbers the overlay shows: the memory of this computer, and who has it. No Qt here.

Windows has two limits, and they fail in different ways:

- RAM is the memory that programs use now. When it is full, Windows moves data to the page file,
  and the computer gets very slow.
- Commit memory is what programs have reserved. RAM and the page file together must be able to
  hold it, and their sum is the commit limit. At this limit a program gets no more memory, even
  when RAM is still free. Games reserve much more than they use, so this limit can come first.
"""

from __future__ import annotations

import ctypes
from collections.abc import Iterable
from dataclasses import dataclass

_PROCESS_LIST = 5  # SystemProcessInformation
_TOO_SMALL = 0xC0000004  # STATUS_INFO_LENGTH_MISMATCH: the list needs a larger buffer
_NOT_A_PROGRAM = "Memory Compression"  # Windows keeps compressed data of other programs there


@dataclass(frozen=True)
class Memory:
    """The memory of this computer now, in bytes."""

    ram_used: int
    ram_total: int
    commit_used: int
    commit_limit: int


@dataclass(frozen=True)
class Program:
    """A line of the list of programs."""

    name: str
    size: int  # bytes, as read_programs counts them


class _MemoryStatus(ctypes.Structure):  # MEMORYSTATUSEX
    _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
        (name, ctypes.c_ulonglong)
        for name in ("total", "free", "page_total", "page_free", "virtual_total", "virtual_free", "extended")
    ]


class _Process(ctypes.Structure):  # the start of SYSTEM_PROCESS_INFORMATION
    _fields_ = [
        ("next", ctypes.c_ulong),  # bytes to the next process, 0 for the last one
        ("threads", ctypes.c_ulong),
        ("ram", ctypes.c_longlong),  # WorkingSetPrivateSize: stable since Windows Vista, but not in Microsoft's header
        ("unused", ctypes.c_byte * 40),
        ("name_bytes", ctypes.c_ushort),
        ("name_room", ctypes.c_ushort),
        ("name", ctypes.c_void_p),
        ("priority", ctypes.c_long),
        ("process_id", ctypes.c_void_p),
        ("parent_id", ctypes.c_void_p),
        ("handles", ctypes.c_ulong),
        ("session", ctypes.c_ulong),
        ("key", ctypes.c_size_t),
        ("peak_virtual", ctypes.c_size_t),
        ("virtual", ctypes.c_size_t),
        ("page_faults", ctypes.c_ulong),
        ("peak_working_set", ctypes.c_size_t),
        ("working_set", ctypes.c_size_t),
        ("pools", ctypes.c_size_t * 4),
        ("commit", ctypes.c_size_t),  # PagefileUsage
    ]


def read_memory() -> Memory:
    """The memory now. Despite its name, ``page_total`` is the commit limit, not the page file."""
    status = _MemoryStatus()
    status.length = ctypes.sizeof(_MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError()
    return Memory(status.total - status.free, status.total, status.page_total - status.page_free, status.page_total)


def read_programs(measure: str = "ram") -> dict[str, int]:
    """The bytes of each program, by name: the processes of one program are added up.

    With ``measure`` "ram" these are the bytes in RAM that the program does not share, the column
    Memory of Task Manager: shared bytes would count once per process. With "commit" they are the
    bytes it has reserved, the column Commit size.

    One call gives all processes at once, as Task Manager gets them. To ask each process by itself
    takes much longer, and the overlay must stay light above a game. This way also needs no access
    to the processes, so the services of Windows are in the list too."""
    buffer = _process_list()
    programs: dict[str, int] = {}
    offset = 0
    while True:
        process = _Process.from_buffer(buffer, offset)
        if process.name_bytes:  # the idle process has no name
            name = ctypes.wstring_at(process.name, process.name_bytes // 2)
            name = name[:-4] if name.lower().endswith(".exe") else name
            if name != _NOT_A_PROGRAM:
                programs[name] = programs.get(name, 0) + getattr(process, measure)
        if not process.next:
            return programs
        offset += process.next


def _process_list() -> ctypes.Array:
    size = ctypes.c_ulong(1024**2)
    while True:
        buffer = ctypes.create_string_buffer(size.value)
        status = ctypes.windll.ntdll.NtQuerySystemInformation(_PROCESS_LIST, buffer, size, ctypes.byref(size))
        status &= 0xFFFFFFFF
        if status == 0:
            return buffer
        if status != _TOO_SMALL:
            raise OSError(f"Windows gave no list of processes (status {status:#x})")
        size.value += 64 * 1024  # room for processes that start before the next try


def top_programs(programs: dict[str, int], count: int, label: str, group: Iterable[str]) -> list[Program]:
    """The ``count`` largest programs, largest first. The programs in ``group`` count as one, called
    ``label``, which stays in the list while one of them runs: if it is too small for the top, it
    comes last."""
    names = {name.casefold() for name in group}
    together = sum(size for name, size in programs.items() if name.casefold() in names)
    ranked = [Program(name, size) for name, size in programs.items() if name.casefold() not in names]
    watched = Program(label, together) if together else None
    if watched:
        ranked.append(watched)
    ranked.sort(key=lambda program: program.size, reverse=True)
    top = ranked[:count]
    if watched and watched not in top:
        top.append(watched)
    return top
