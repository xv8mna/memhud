"""Build the Windows download and check it: dist\\MemHUD (MemHUD.exe, the libraries and their
licenses) and dist\\MemHUD-<version>-windows.zip.

Build in a fresh virtual environment with Python 3.14, so that only what the program needs goes in:

    py -3.14 -m venv .venv-build
    .venv-build\\Scripts\\python -m pip install .[build]
    .venv-build\\Scripts\\python tools\\build.py

The download is built from committed files only: the build stops when files in src, packaging or
tools have changes that are not committed, unless --dirty is given (for trying things out).
"""

from __future__ import annotations

import argparse
import ast
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from importlib import metadata
from pathlib import Path, PurePath

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
APP = DIST / "MemHUD"
WORK = ROOT / "build"
QT_NOTICES = ROOT / "packaging" / "licenses" / "Qt-third-party.txt"
PYTHON_NOTICES = ROOT / "packaging" / "licenses" / "Python" / "ACKNOWLEDGEMENTS.txt"

# Tools for building, not part of the download. PyInstaller is not one of them: its start-up code
# and run-time hooks are in the program.
BUILD_TOOLS = {"pip", "pyinstaller-hooks-contrib", "setuptools", "altgraph", "pefile", "pywin32-ctypes", "packaging",
               "memhud"}  # fmt: skip
ICON_SIZES = (16, 32, 48, 256)
# Notes for libraries whose license files don't cover all their code
LICENSE_NOTES = {
    "shiboken6": "Shiboken6 includes code from Python under the PSF License Agreement: see ..\\Python\\LICENSE.txt.\n",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Windows download and check it.")
    parser.add_argument("--dirty", action="store_true", help="build with changes that are not committed (to try things out)")
    if not parser.parse_args().dirty:
        _committed()
    from memhud import __version__

    versions = _versions()
    _check_python_notices()
    shutil.rmtree(DIST, ignore_errors=True)
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir()
    _write_icon(WORK / "app.ico")
    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller", "memhud.spec", "--noconfirm", "--log-level", "WARN",
            "--distpath", str(DIST), "--workpath", str(WORK),
        ],  # fmt: skip
        cwd=ROOT / "packaging",
        check=True,
    )
    _check_sources()
    _check_qt_notices()
    _add_files(__version__, versions)
    _check()
    archive = _zip(__version__)
    size = sum(file.stat().st_size for file in APP.rglob("*") if file.is_file())
    print(f"\n{APP}: {size / 2**20:.0f} MB\n{archive}: {archive.stat().st_size / 2**20:.0f} MB")


def _git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, encoding="utf-8", check=True).stdout


def _committed() -> None:
    """The download is what is committed: a local folder may hold other changes."""
    changes = _git("status", "--porcelain", "--untracked-files=all", "--", "src", "packaging", "tools")
    if changes:
        raise SystemExit(f"Not committed:\n{changes}\nCommit first, or build with --dirty to try things out.")


def _versions() -> dict[str, str]:
    """The versions for the README's licenses part: of PyInstaller, and of Qt, PySide6 and Shiboken6
    with the links to their source."""
    import PySide6
    import shiboken6
    from PySide6.QtCore import qVersion

    qt = qVersion()
    if not QT_NOTICES.read_text(encoding="utf-8").startswith(f"Qt {qt}:"):
        raise SystemExit(f"{QT_NOTICES.relative_to(ROOT)} is not for Qt {qt}: update it with tools\\qt_notices.py")
    return {
        "pyinstaller": metadata.version("pyinstaller"),
        "qt": qt,
        "pyside": PySide6.__version__,
        "shiboken": shiboken6.__version__,
        # The archive keeps every Qt version; Qt for Python keeps them in its releases folder
        "qt_source": f"https://download.qt.io/archive/qt/{qt.rsplit('.', 1)[0]}/{qt}/single/",
        "pyside_source": f"https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-{PySide6.__version__}-src/",
    }


def _write_icon(path: Path) -> None:
    """The icon of MemHUD.exe: the drawing of the tray icon, as PNG images in an .ico file."""
    from PySide6.QtCore import QBuffer
    from PySide6.QtGui import QGuiApplication

    from memhud.app import draw_icon

    _app = QGuiApplication.instance() or QGuiApplication([])
    images = []
    for size in ICON_SIZES:
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        draw_icon(size).save(buffer, "PNG")
        images.append((size, bytes(buffer.data())))
    offset = 6 + 16 * len(images)  # the header and one entry per image
    entries = b""
    for size, image in images:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(image), offset)
        offset += len(image)
    path.write_bytes(struct.pack("<HHH", 0, 1, len(images)) + entries + b"".join(image for _, image in images))


def _check_python_notices() -> None:
    """The notices for the code of other projects in Python are for the Python of the build. They
    change with Python's version (3.14, 3.15), seldom with its bug-fix releases (3.14.x)."""
    built_with, file = platform.python_version(), PYTHON_NOTICES.relative_to(ROOT)
    written_for = PYTHON_NOTICES.read_text(encoding="utf-8").split(":", 1)[0].removeprefix("Python ")
    if written_for.rsplit(".", 1)[0] != built_with.rsplit(".", 1)[0]:
        raise SystemExit(f"{file} is for Python {written_for}: update it with tools\\python_notices.py")
    if written_for != built_with:
        print(f"Note: {file} is for Python {written_for}, the build uses {built_with}")


def _check_qt_notices() -> None:
    """Qt-third-party.txt names the Qt DLLs it has the notices for: exactly the ones in the download."""
    header = QT_NOTICES.read_text(encoding="utf-8").split("\nContents\n", 1)[0]
    named = {name.rsplit("\\", 1)[-1] for name in re.findall(r"[\w\\]+\.dll", header)}
    qt = APP / "_internal" / "PySide6"
    shipped = {file.name for file in [*qt.glob("Qt6*.dll"), *(qt / "plugins").rglob("*.dll")]}
    if named != shipped:
        only_named, only_shipped = ", ".join(sorted(named - shipped)) or "-", ", ".join(sorted(shipped - named)) or "-"
        raise SystemExit(
            f"{QT_NOTICES.relative_to(ROOT)} is not for the Qt DLLs of the download (not in the download: {only_named}; "
            f"not in the file: {only_shipped}): update it with tools\\qt_notices.py"
        )


def _check_sources() -> None:
    """Everything in the download comes from Python, the build environment, the source or the build
    itself, and nothing from other programs on the build machine's PATH."""
    (entries,) = ast.literal_eval((WORK / "memhud" / "COLLECT-00.toc").read_text(encoding="utf-8"))
    allowed = [Path(folder).resolve() for folder in (sys.base_prefix, sys.prefix, ROOT / "src", WORK)]
    foreign = [
        f"  {destination}  from  {source}"
        for destination, source, _ in entries
        if source and not any(Path(source).resolve().is_relative_to(folder) for folder in allowed)
    ]
    if foreign:
        raise SystemExit("Files from outside Python, the build environment and src:\n" + "\n".join(foreign))


def _add_files(version: str, versions: dict[str, str]) -> None:
    """The README, and the licenses of the program and of everything included."""
    text = (ROOT / "packaging" / "README.txt").read_text(encoding="utf-8")
    for key, value in {"version": version, **versions}.items():
        text = text.replace(f"{{{key}}}", value)
    title, _, rest = text.split("\n", 2)
    text = f"{title}\n{'=' * len(title)}\n{rest}"  # the underline as long as the title with its version
    (APP / "README.txt").write_text(text, encoding="utf-8", newline="\r\n")
    shutil.copyfile(ROOT / "LICENSE", APP / "LICENSE.txt")
    licenses = APP / "licenses"
    licenses.mkdir()
    for notice in (ROOT / "packaging" / "licenses").glob("*.txt"):  # the LGPL, the GPL, Qt's third-party notices
        shutil.copyfile(notice, licenses / notice.name)
    python = Path(sys.base_prefix) / "LICENSE.txt"
    if not python.is_file():
        raise SystemExit(f"Python's license is not in {python}")
    (licenses / "Python").mkdir()
    shutil.copyfile(python, licenses / "Python" / "LICENSE.txt")
    shutil.copyfile(PYTHON_NOTICES, licenses / "Python" / PYTHON_NOTICES.name)
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        if name.lower() in BUILD_TOOLS:
            continue
        target = licenses / f"{name}-{dist.version}"
        copied = 0
        for file in dist.files or ():
            source = Path(dist.locate_file(file))
            if _is_license(file.name) and source.is_file():
                (target / _license_path(file)).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target / _license_path(file))
                copied += 1
        if not copied:
            terms = dist.metadata.get("License-Expression") or dist.metadata.get("License") or "see the project"
            text = f"{name} {dist.version}: {terms}\n"
            if "LGPL-3.0" in terms:
                text += "This download includes it under the LGPL-3.0: see ..\\LGPL-3.0.txt and ..\\GPL-3.0.txt.\n"
            target.mkdir(parents=True)
            (target / "LICENSE.txt").write_text(text, encoding="utf-8", newline="\r\n")
        if note := LICENSE_NOTES.get(name.lower()):
            (target / "NOTE.txt").write_text(note, encoding="utf-8", newline="\r\n")


def _is_license(name: str) -> bool:
    """A license file, but not Qt's commercial license (PySide6 and Shiboken6 ship only that one,
    while the download uses them under the LGPL)."""
    name = name.lower()
    commercial = name.startswith("licenseref-qt-commercial")
    return not commercial and any(word in name for word in ("license", "copying", "notice"))


def _license_path(file: PurePath) -> PurePath:
    """Where a license file goes in the library's folder: e.g. LICENSE from
    <name>.dist-info\\licenses\\LICENSE, and the license of a part with its folders. A file
    installed outside site-packages (..\\..\\share\\... or a full path) only with its name."""
    parts = file.parts
    if ".." in parts or file.anchor:
        return PurePath(file.name)
    if parts[0].endswith(".dist-info"):
        parts = parts[2:] if parts[1:2] == ("licenses",) else parts[1:]
    return PurePath(*parts)


def _check() -> None:
    """The program starts, updates the overlay and ends without an error: in a temporary folder,
    without the settings of the build machine and without DLLs from other programs."""
    from memhud.app import STARTUP_CHECK

    windows = os.environ.get("SystemRoot", r"C:\Windows")
    with tempfile.TemporaryDirectory() as folder:
        environment = {key: value for key, value in os.environ.items() if not key.startswith(("PYTHON", "QT_"))}
        environment |= {
            "APPDATA": str(Path(folder) / "Roaming"),
            "LOCALAPPDATA": str(Path(folder) / "Local"),
            "PATH": f"{windows}\\System32;{windows}",
            "QT_QPA_PLATFORM": "offscreen",
            STARTUP_CHECK: "1",
        }
        code = subprocess.run([APP / "MemHUD.exe"], env=environment, timeout=60).returncode
    if code:
        raise SystemExit(f"MemHUD.exe ended with exit code {code}")
    print("checked: MemHUD.exe started, updated the overlay and ended without an error")


def _zip(version: str) -> Path:
    archive = DIST / f"MemHUD-{version}-windows.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for file in sorted(APP.rglob("*")):
            if file.is_file():
                out.write(file, Path("MemHUD") / file.relative_to(APP))
    return archive


if __name__ == "__main__":
    main()
