DisplayOverlay {version} for Windows
====================================

DisplayOverlay is a small always-on-top overlay. It shows how much memory your computer has
left, in a corner of the screen, also above a game. It takes no clicks and no focus, and it does
not touch the game.
Documentation, source code and issues: https://github.com/xv8mna/display-overlay

Start
-----
Unzip the download into a folder of your choice, e.g. into C:\Tools (which gives
C:\Tools\DisplayOverlay) or into your user folder. Keep the folder DisplayOverlay together (the
program needs the files next to it), and start DisplayOverlay.exe.

The overlay appears, and its icon appears in the notification area of the taskbar. Click the
icon to open the settings. Right-click it to hide the overlay or to quit.

The program is not signed. When Windows shows "Windows protected your PC", click "More info",
then "Run anyway". Your organization's settings may not allow programs from the internet at
all: then ask your IT department.

Games
-----
The overlay is a normal window of its own. Windows gives a game in exclusive fullscreen the
whole screen, so the overlay may not show there. If that happens, set the game to borderless or
windowed fullscreen, or put the overlay on a second monitor.

Settings, log and removing DisplayOverlay
-----------------------------------------
- Settings: %APPDATA%\DisplayOverlay\settings.json
- Log: %LOCALAPPDATA%\DisplayOverlay\display-overlay.log
- "Start with Windows" adds one value to the Run key of your user account. If you move the
  folder DisplayOverlay, turn it off and on again.

To remove DisplayOverlay, turn off "Start with Windows", quit the program and delete the folder
DisplayOverlay. Delete the folders %APPDATA%\DisplayOverlay and %LOCALAPPDATA%\DisplayOverlay
too, if you like.

Licenses
--------
DisplayOverlay is under the MIT license (LICENSE.txt). The libraries it includes are under their
own licenses: see the folder licenses. Python's license is in licenses\Python, with the notices
for the code of other projects that Python includes (ACKNOWLEDGEMENTS.txt). The start-up code of
DisplayOverlay.exe is from PyInstaller {pyinstaller}, under the GPL-2.0 with an exception that
allows this use and, for its run-time hooks, the Apache-2.0
(licenses\pyinstaller-{pyinstaller}\COPYING.txt).

Qt {qt} and PySide6 {pyside} with Shiboken6 {shiboken} (Qt for Python) are under the LGPL-3.0:
their DLLs in _internal\PySide6 and _internal\shiboken6 can be replaced by other builds of the
same versions. The LGPL and the GPL it builds on are in licenses\LGPL-3.0.txt and
licenses\GPL-3.0.txt. licenses\Qt-third-party.txt has the notices for the code of other
projects that is built into the Qt DLLs. The source code of these versions:

  Qt                     {qt_source}
  PySide6 and Shiboken6  {pyside_source}
