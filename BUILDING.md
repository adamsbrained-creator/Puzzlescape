# Building the Puzzlescape .exe

## What actually went wrong

```
FileNotFoundError: No file 'assets/fonts/InterVariable.ttf' found in
working directory 'C:\Users\thead\Documents\Puzzlescape\build\Puzzlescape'
```

Two separate things caused this:

1. **The `assets` folder was never bundled.** PyInstaller only packages
   the Python *code* it can trace through your imports. It has no way
   to know your fonts and images are needed too, unless you tell it to
   — so a plain `pyinstaller main.py` leaves `assets/` out entirely.
   `Puzzlescape.spec` (added alongside this file) fixes that with one
   line: `datas=[('assets', 'assets')]`.

2. **`build\Puzzlescape` isn't the finished app.** PyInstaller writes
   to two different folders, and only one of them is meant to be run:

   - `build/Puzzlescape/` — scratch space PyInstaller uses *while*
     building (you can see this in your screenshot: `warn-*.txt`,
     `xref-*.html`, `PYZ-00.pyz`, `base_library.zip`, `localpycs/` —
     those are all internal working files, not your game). **Never run
     the .exe from here.**
   - `dist/Puzzlescape/` — the actual, finished, shareable app.

   Even with assets bundled correctly, running the .exe out of `build/`
   would still fail, since that folder never gets the bundled assets
   copied into it either.

I also made the code itself more forgiving: it now figures out its own
folder at startup (`paths.py`) instead of trusting the current working
directory, so this specific failure mode can't happen again even if
Windows launches the .exe from a different working directory than
expected (which does happen with shortcuts and pinned taskbar icons).
It also handles your `src/` + `assets/` split correctly - it searches
upward from wherever the code actually lives until it finds a folder
that has `assets/` in it, rather than assuming both sit side by side.

## Building it, step by step

Your project is laid out like this — the code (including the spec file)
sits in `src/`, and `assets/` is one level up, next to `src/` itself:
```
Puzzlescape/
  assets/
  src/
    main.py
    Puzzlescape.spec
    ...
```
`Puzzlescape.spec` already knows this (it finds things relative to its
own location), so every command below can be run from `src/`.

**1. Install PyInstaller** (once), from `src/`:
```
pip install pyinstaller
```

**2. Clean out any previous attempt.** Old `build/` and `dist/` folders
from a broken run can confuse the next one. Looking at your screenshot,
yours currently sit at the `Puzzlescape/` level (one up from `src/`), so
from `src/`:
```
rmdir /s /q ..\build
rmdir /s /q ..\dist
```

**3. Build**, from `src/`:
```
pyinstaller Puzzlescape.spec
```
This reads the `.spec` file instead of guessing what to bundle, so it
picks up `assets/` automatically - even though it lives outside `src/`.
You'll see PyInstaller print a lot of lines - that's normal - and it
finishes by writing `build/` (ignore this) and `dist/` (this is what you
want), both one level up in `Puzzlescape/`, next to `assets/`.

**4. Run it from the right place:**
```
..\dist\Puzzlescape\Puzzlescape.exe
```
`dist\Puzzlescape\` now contains `Puzzlescape.exe` sitting next to an
`assets` folder, plus a handful of `.dll`/support files it needs — all
of that has to stay together.

**5. Sharing it with someone else (or your girlfriend):** zip the
*whole* `dist\Puzzlescape` folder, not just the `.exe` — the exe alone
won't run without the files sitting next to it. They unzip it anywhere
and double-click `Puzzlescape.exe` inside.

## Rebuilding after changes

Any time you change a `.py` file *or* add/edit anything in `assets/`,
you need to rerun step 3 — the `dist` folder is a snapshot from when
you last built, not a live copy, so it won't pick up new files by
itself. Steps 1 and 2 (install / clean) are one-time and can usually be
skipped after the first build; a plain `rmdir` + rebuild is a good habit
any time something seems stale, though.

## A window icon, if you'd like one

There's no `.exe` icon set up yet, so it uses the default PyInstaller
icon in Explorer/taskbar (the game window itself now uses `logo.png` as
its icon, so this only affects the desktop file/shortcut, not the game
window). To add one: make a `.ico` file, drop it somewhere like
`assets/icon.ico`, and set `icon='assets/icon.ico'` in the `EXE(...)`
section of `Puzzlescape.spec`.

## If you ever want a single .exe instead

Right now this builds "one-folder" style (`dist/Puzzlescape/` — an .exe
plus its files, all in one folder, like now). PyInstaller can also build
"one-file" style (a single .exe with everything squeezed inside it) —
more convenient to send around, but it re-unpacks itself into a temp
folder every time it starts, so it opens noticeably slower. `paths.py`
already supports either mode without changes, so if you want to try
one-file later, it's just a different PyInstaller command
(`pyinstaller --onefile main.py --add-data "assets;assets"`) — ask and
I can walk through it or make a second spec file for it.
