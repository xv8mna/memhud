# PyInstaller: the Windows download, a folder with DisplayOverlay.exe. Built by tools\build.py, which
# also makes the icon, checks the result and zips it. A folder, not one packed file: the program
# starts faster, which matters with autostart, and the Qt DLLs stay files that can be replaced.

# Files that the program doesn't use: Qt's translations and networking, the Qt plugins for styles
# (it sets Fusion, which is built in), touch input, Direct2D and image formats (it draws its icon),
# and Qt's software OpenGL (a widgets app doesn't use it)
UNUSED_FOLDERS = (
    "pyside6/translations/",
    *(f"pyside6/plugins/{kind}/" for kind in ("tls", "networkinformation", "styles", "generic", "imageformats")),
)
UNUSED_FILES = {"qt6network.dll", "qtnetwork.pyd", "qdirect2d.dll", "opengl32sw.dll"}


def needed(entry):
    path = entry[0].replace("\\", "/").lower()
    name = path.rsplit("/", 1)[-1]
    return not (
        # Windows' own C runtime: Windows 10 and 11 have it, and a copy that another program put
        # on the build machine's PATH must not come along
        name.startswith("api-ms-win-")
        or name == "ucrtbase.dll"
        or path.startswith(UNUSED_FOLDERS)
        or name in UNUSED_FILES
    )


programs = Analysis(["app.py"], pathex=["../src"], excludes=["PySide6.QtNetwork", "tkinter", "_tkinter", "pytest"])
programs.binaries = [entry for entry in programs.binaries if needed(entry)]
programs.datas = [entry for entry in programs.datas if needed(entry)]
program = EXE(
    PYZ(programs.pure), programs.scripts, [], exclude_binaries=True, name="DisplayOverlay", icon="../build/app.ico",
    console=False, upx=False,
)  # fmt: skip
COLLECT(program, programs.binaries, programs.datas, name="DisplayOverlay", upx=False)
