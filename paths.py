import os
import sys


# --------------------------------------------------
# Puzzlescape paths
# --------------------------------------------------
# Every relative path in the game ("assets/fonts/InterVariable.ttf", and
# so on) is written assuming the current working directory IS the game's
# own folder. That's true when you run `python main.py` from inside the
# project - but nothing guarantees it once the game is packaged into an
# .exe: Windows sets the working directory based on how the .exe was
# launched (a desktop shortcut, a taskbar pin, and a double-click in
# Explorer can all behave differently), so a relative path can silently
# point at the wrong folder, e.g. FileNotFoundError on
# assets/fonts/InterVariable.ttf even though that file is right there
# next to the .exe.
#
# enter_bundle_dir() fixes this once, at startup, by making the working
# directory the game's own folder no matter which of these is true:
#   - running from source (`python main.py`)
#   - a PyInstaller --onedir build (assets sit next to the .exe)
#   - a PyInstaller --onefile build (PyInstaller unpacks everything the
#     .spec bundled into a temporary folder at startup and hands us its
#     path as sys._MEIPASS - that's where bundled assets live in this
#     case, NOT next to the .exe)
# After it runs, every "assets/..." path elsewhere in the game works
# unchanged, in all three cases.
#
# This is deliberately separate from save_manager.app_dir(): that one
# answers "where do save.json and settings.json belong" (always next to
# the real .exe, so they survive and are easy to find), which is a
# different question from "where are the bundled read-only assets" (the
# temporary --onefile extraction folder is fine for those, but would be
# the wrong, wiped-on-exit place to keep a save file).


def bundle_dir():
    """The folder holding the game's bundled assets (fonts, images) in
    whichever way the game is currently running."""
    if hasattr(sys, "_MEIPASS"):            # PyInstaller --onefile
        return sys._MEIPASS
    if getattr(sys, "frozen", False):        # PyInstaller --onedir
        return os.path.dirname(sys.executable)

    # `python main.py`. main.py/paths.py don't necessarily sit right next
    # to assets/ - here that's true (a src/ folder holds the code, with
    # assets/ one level up, next to src/ itself) - so walk upward from
    # paths.py's own folder until one actually containing "assets" is
    # found, instead of assuming a fixed layout that breaks the moment
    # the project gets reorganised again.
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = here

    for _ in range(6):   # plenty for any reasonable project; keeps this from wandering off toward the filesystem root
        if os.path.isdir(os.path.join(candidate, "assets")):
            return candidate

        parent = os.path.dirname(candidate)
        if parent == candidate:   # reached the filesystem root
            break
        candidate = parent

    return here   # nothing found - enter_bundle_dir() below reports this clearly rather than failing silently


def enter_bundle_dir():
    """Call once, at startup, before any font/image is loaded."""
    target = bundle_dir()

    try:
        os.chdir(target)
    except OSError:
        # Nothing sensible to do if even this fails - let whichever
        # asset load happens first raise its own clear error.
        return

    if not os.path.isdir(os.path.join(target, "assets")):
        # Fails fast with a message that says exactly what's missing,
        # instead of a much more confusing FileNotFoundError the moment
        # the first font loads.
        sys.exit(
            "Puzzlescape can't find its 'assets' folder next to "
            f"{'the .exe' if getattr(sys, 'frozen', False) else 'main.py'} "
            f"(looked in {target}).\n"
            "If this is a packaged build, the assets folder needs to be "
            "bundled - see BUILDING.md."
        )
