# Puzzlescape.spec
#
# Builds the Windows .exe. Run with:
#     pyinstaller Puzzlescape.spec
# from anywhere - every path below is built from SPECPATH (the folder
# this .spec file itself sits in), not from wherever you happen to run
# the command from, so it doesn't matter which folder is "current."
#
# Matches the project layout: this file and main.py live in src/, and
# assets/ sits one level up, next to src/ itself:
#     Puzzlescape/
#       assets/
#       src/
#         main.py
#         Puzzlescape.spec   <- this file
#         ...
#
# The one thing a plain `pyinstaller main.py` misses is that PyInstaller
# only bundles the Python CODE it can trace through imports - it has no
# way to know assets/ (fonts, images) needs to go in too, so it's left
# out unless a spec file (or --add-data) says to include it. That's the
# whole cause of the InterVariable.ttf error: the .exe was never given a
# copy of the assets folder to look for in the first place.
#
# See BUILDING.md for the full walkthrough (including WHERE the finished
# .exe ends up and why build/ isn't it).

import os

project_root = os.path.dirname(SPECPATH)   # Puzzlescape/, one level above src/

a = Analysis(
    [os.path.join(SPECPATH, 'main.py')],
    pathex=[],
    binaries=[],
    # (source, destination-inside-the-build) - 'assets' on the right
    # means "call it assets inside the build", matching the plain
    # "assets/..." paths used throughout the code. PyInstaller walks the
    # source folder recursively, so fonts/, images/ and everything under
    # them all come along without listing each file individually.
    datas=[(os.path.join(project_root, 'assets'), 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Puzzlescape',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # no console window behind the game
    icon=None,       # put an .ico path here once you have one, e.g. os.path.join(project_root, 'assets', 'icon.ico')
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Puzzlescape',
)
