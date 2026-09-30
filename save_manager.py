import json
import math
import os
import sys
from datetime import date, timedelta


# --------------------------------------------------
# Puzzlescape save file
# --------------------------------------------------
# Everything about *progress* (as opposed to preferences, which live in
# settings.json / main.py's load_settings) lives in one save.json file:
#   - which levels are finished, and each one's best time
#   - the level currently in progress (which pieces are already snapped,
#     how much time had already run on the clock, and whether a hint was
#     used), so quitting mid puzzle and coming back - even after closing
#     the app - picks up right where you left off
#   - the Daily Challenge streak
#   - achievement progress, which achievements are unlocked (and when),
#     and the few running stats they need (see achievements.py)
#
# Nothing in here ever touches pygame - this module only reads/writes
# plain JSON, so it can be tested or reused without a display.

SAVE_VERSION = 5   # 2 added "hint_used" and "grid" to every level entry;
                   # 3 added "unlocked" and "stats"; 4 added "player_name",
                   # "rewards_unlocked" (see rewards.py) and
                   # "stats.lifetime_pieces_placed"; 5 added "coins". Older
                   # files still load fine - anything missing just gets
                   # its default.


def app_dir():
    """The folder the game lives in. Saves go here no matter which folder
    the game was started from - and, once the game is packaged into an
    .exe, next to the .exe instead of inside its temporary unpack folder
    (which would be wiped on every launch)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def app_path(filename):
    return os.path.join(app_dir(), filename)


SAVE_FILE = app_path("save.json")


# --------------------------------------------------
# Small validation helpers (for reading untrusted JSON)
# --------------------------------------------------

def _is_int(value):
    # bool is a subclass of int in Python - True must not pass as 1.
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


# --------------------------------------------------
# Defaults
# --------------------------------------------------

def _default_level_entry():
    return {
        "completed": False,
        "best_time": None,      # seconds, or None if never finished
        "pieces_placed": 0,     # snapped pieces in the current attempt
        "snapped_cells": [],    # [(col, row), ...] already-placed pieces
        "elapsed": 0.0,         # seconds already on the clock
        "hint_used": False,     # was the hint used in the current attempt
        "grid": None,           # [columns, rows] the saved pieces belong to
        "best_stars": 0,        # 0-3, the best star rating ever earned here
                                 # (see main.py's star_rating) - never goes down,
                                 # even on a slower replay
    }


def _default_save():
    return {
        "version": SAVE_VERSION,
        "player_name": None,          # None until the welcome screen is completed
        "profile_picture": None,      # optional local image path for the greeting screen
        "coins": 0,                    # in-game currency, spendable (see add_coins) -
                                        # not a lifetime stat, unlike stats below
        "shop": {
            "owned": {},             # theme keys bought in the Shop mode
        },
        "levels": {},                # level name -> entry (see above)
        "last_level": None,          # which level "RESUME" should open
        "daily": {
            "streak": 0,
            "best": 0,
            "completed": 0,
            "last_date": None,       # ISO date string, for streak maths
        },
        "achievements": {},          # achievement key -> progress value
        "unlocked": {},              # achievement key -> ISO date unlocked
        "rewards_unlocked": {},      # reward key -> ISO date unlocked (see rewards.py)
        "rewards_claimed": {},       # reward key -> ISO date claimed by player
        "stats": {
            "themes_tried": [],          # color themes the player has selected
            "lifetime_pieces_placed": 0,  # every piece ever snapped into a
                                           # completed puzzle, running total
        },
    }


def _clean_level_entry(raw):
    """Rebuilds one level's entry from untrusted JSON, dropping anything
    that doesn't look right instead of trusting it blindly."""
    entry = _default_level_entry()

    if not isinstance(raw, dict):
        return entry

    if isinstance(raw.get("completed"), bool):
        entry["completed"] = raw["completed"]

    if _is_number(raw.get("best_time")):
        entry["best_time"] = max(0.0, float(raw["best_time"]))

    if _is_int(raw.get("pieces_placed")):
        entry["pieces_placed"] = max(0, raw["pieces_placed"])

    if isinstance(raw.get("snapped_cells"), list):
        cells = []
        for cell in raw["snapped_cells"]:
            if (
                isinstance(cell, list)
                and len(cell) == 2
                and all(_is_int(v) for v in cell)
            ):
                cells.append((cell[0], cell[1]))
        entry["snapped_cells"] = cells

    if _is_number(raw.get("elapsed")):
        entry["elapsed"] = max(0.0, float(raw["elapsed"]))

    if _is_int(raw.get("best_stars")):
        entry["best_stars"] = max(0, min(3, raw["best_stars"]))

    if isinstance(raw.get("hint_used"), bool):
        entry["hint_used"] = raw["hint_used"]

    grid = raw.get("grid")
    if (
        isinstance(grid, list)
        and len(grid) == 2
        and all(_is_int(v) and v > 0 for v in grid)
    ):
        entry["grid"] = [grid[0], grid[1]]

    return entry


def migrate_level_names(data, aliases):
    """Rename level save keys, merging progress if both names exist.

    Aliases maps old visible level titles to their new titles. Names not
    listed remain untouched, allowing removed categories to stay archived.
    """
    levels = data.get("levels")
    if not isinstance(levels, dict):
        return False

    changed = False
    attempt_fields = ("pieces_placed", "snapped_cells", "elapsed", "hint_used", "grid")

    for old_name, new_name in aliases.items():
        old_entry = levels.pop(old_name, None)
        if old_entry is None:
            continue

        current_entry = levels.get(new_name)
        if current_entry is None:
            levels[new_name] = old_entry
        else:
            old_completed = bool(old_entry.get("completed"))
            current_completed = bool(current_entry.get("completed"))
            current_entry["completed"] = old_completed or current_completed

            best_times = [
                value for value in (old_entry.get("best_time"), current_entry.get("best_time"))
                if _is_number(value)
            ]
            current_entry["best_time"] = min(best_times) if best_times else None
            current_entry["best_stars"] = max(
                old_entry.get("best_stars", 0), current_entry.get("best_stars", 0)
            )

            if (
                not old_completed
                and not current_completed
                and old_entry.get("pieces_placed", 0) > current_entry.get("pieces_placed", 0)
            ):
                for field in attempt_fields:
                    current_entry[field] = old_entry.get(field)

        changed = True

    old_last_level = data.get("last_level")
    if old_last_level in aliases:
        data["last_level"] = aliases[old_last_level]
        changed = True

    return changed


# --------------------------------------------------
# Load / save
# --------------------------------------------------

def load():
    """Reads save.json (if it exists) and returns a fully-defaulted save
    dict, so callers never have to guard against missing keys. A missing
    or corrupt file just means "nothing saved yet" - never a crash.
    """
    data = _default_save()

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as file:
            raw = json.load(file)
    except (OSError, ValueError):
        return data

    if not isinstance(raw, dict):
        return data

    if isinstance(raw.get("player_name"), str) and raw["player_name"].strip():
        data["player_name"] = raw["player_name"].strip()[:24]

    if isinstance(raw.get("profile_picture"), str) and raw["profile_picture"].strip():
        data["profile_picture"] = raw["profile_picture"].strip()

    if _is_int(raw.get("coins")):
        data["coins"] = max(0, raw["coins"])

    raw_shop = raw.get("shop")
    if isinstance(raw_shop, dict):
        owned = raw_shop.get("owned")
        if isinstance(owned, dict):
            data["shop"]["owned"] = {
                key: bool(value)
                for key, value in owned.items()
                if isinstance(key, str)
            }

    if isinstance(raw.get("levels"), dict):
        for name, entry in raw["levels"].items():
            if isinstance(name, str):
                data["levels"][name] = _clean_level_entry(entry)

    if isinstance(raw.get("last_level"), str):
        data["last_level"] = raw["last_level"]

    raw_daily = raw.get("daily")
    if isinstance(raw_daily, dict):
        for key in ("streak", "best", "completed"):
            if _is_int(raw_daily.get(key)):
                data["daily"][key] = max(0, raw_daily[key])
        if isinstance(raw_daily.get("last_date"), str):
            data["daily"]["last_date"] = raw_daily["last_date"]

    raw_achievements = raw.get("achievements")
    if isinstance(raw_achievements, dict):
        for key, value in raw_achievements.items():
            if isinstance(key, str) and _is_number(value):
                data["achievements"][key] = value

    raw_unlocked = raw.get("unlocked")
    if isinstance(raw_unlocked, dict):
        for key, when in raw_unlocked.items():
            if isinstance(key, str) and isinstance(when, str):
                data["unlocked"][key] = when

    raw_rewards_unlocked = raw.get("rewards_unlocked")
    if isinstance(raw_rewards_unlocked, dict):
        for key, when in raw_rewards_unlocked.items():
            if isinstance(key, str) and isinstance(when, str):
                data["rewards_unlocked"][key] = when

    raw_rewards_claimed = raw.get("rewards_claimed")
    if isinstance(raw_rewards_claimed, dict):
        for key, when in raw_rewards_claimed.items():
            if isinstance(key, str) and isinstance(when, str):
                data["rewards_claimed"][key] = when
    else:
        data["rewards_claimed"] = dict(data["rewards_unlocked"])

    raw_stats = raw.get("stats")
    if isinstance(raw_stats, dict):
        if isinstance(raw_stats.get("themes_tried"), list):
            data["stats"]["themes_tried"] = list(dict.fromkeys(
                name for name in raw_stats["themes_tried"] if isinstance(name, str)
            ))
        if _is_int(raw_stats.get("lifetime_pieces_placed")):
            data["stats"]["lifetime_pieces_placed"] = max(0, raw_stats["lifetime_pieces_placed"])

    return data


def save(data):
    """Writes the save dict to disk atomically - to a temp file first,
    then swapped into place - so a crash or power loss mid-write can't
    leave save.json half-written and unreadable next launch.
    Returns True if it was written, False if it couldn't be (a failed
    save never crashes the game).
    """
    tmp_path = SAVE_FILE + ".tmp"

    try:
        serialisable = {
            "version": SAVE_VERSION,
            "player_name": data["player_name"],
            "profile_picture": data.get("profile_picture"),
            "coins": data["coins"],
            "shop": {
                "owned": dict(data["shop"].get("owned", {})),
            },
            "levels": {
                name: {
                    "completed": entry["completed"],
                    "best_time": entry["best_time"],
                    "pieces_placed": entry["pieces_placed"],
                    "snapped_cells": [list(cell) for cell in entry["snapped_cells"]],
                    "elapsed": entry["elapsed"],
                    "hint_used": entry["hint_used"],
                    "best_stars": entry["best_stars"],
                    "grid": entry["grid"],
                }
                for name, entry in data["levels"].items()
            },
            "last_level": data["last_level"],
            "daily": data["daily"],
            "achievements": data["achievements"],
            "unlocked": data["unlocked"],
            "rewards_unlocked": data["rewards_unlocked"],
            "rewards_claimed": data.get("rewards_claimed", {}),
            "stats": data["stats"],
        }

        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(serialisable, file, indent=2)
        os.replace(tmp_path, SAVE_FILE)
        return True
    except (OSError, TypeError, ValueError):
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


# --------------------------------------------------
# Player name (set once, on the welcome screen)
# --------------------------------------------------

def set_player_name(data, name):
    """Trims and stores the player's name; a blank name is treated as
    "not set" so the welcome screen would be shown again."""
    cleaned = name.strip()[:24]
    data["player_name"] = cleaned or None
    return data["player_name"]


# --------------------------------------------------
# Coins
# --------------------------------------------------

def add_coins(data, amount):
    """Adds `amount` (can be negative, once something actually spends
    coins) to the balance, never letting it go below zero. One choke
    point for every place that changes it, rather than every caller
    poking data["coins"] directly."""
    data["coins"] = max(0, data["coins"] + amount)
    return data["coins"]


# --------------------------------------------------
# Levels
# --------------------------------------------------

def level_entry(data, level_name):
    """The save entry for one level, creating a fresh (untouched) one the
    first time that level is asked about."""
    return data["levels"].setdefault(level_name, _default_level_entry())


def clear_progress(entry):
    """Wipes the unfinished attempt on one level (placed pieces, clock,
    hint flag) but keeps whether it was ever completed and its best time.
    Used by RESTART LEVEL."""
    entry["pieces_placed"] = 0
    entry["snapped_cells"] = []
    entry["elapsed"] = 0.0
    entry["hint_used"] = False


def sync_grid(data, level_name, columns, rows):
    """Call once per level at startup, with the level's CURRENT grid size.

    If the level was resized since its progress was saved (say 12x8 became
    16x12), the saved piece positions no longer mean anything, so that
    attempt is cleared instead of restoring pieces into the wrong places.
    Also throws away any saved piece that falls outside the grid, and
    makes the placed-pieces count match what's really saved."""
    entry = level_entry(data, level_name)
    grid = [columns, rows]

    if entry["grid"] is not None and entry["grid"] != grid:
        clear_progress(entry)

    in_range = [
        (col, row) for (col, row) in entry["snapped_cells"]
        if 0 <= col < columns and 0 <= row < rows
    ]
    entry["snapped_cells"] = list(dict.fromkeys(in_range))   # no duplicates

    if not entry["completed"]:
        entry["pieces_placed"] = len(entry["snapped_cells"])

    entry["grid"] = grid


# --------------------------------------------------
# Daily Challenge
# --------------------------------------------------

def current_streak(data):
    """The streak to SHOW. The stored number only changes when a daily
    puzzle is finished, so after a few days away it would still read as
    alive - this returns 0 once the last completed day is older than
    yesterday (the streak is broken, even though nothing has been played
    yet to record that)."""
    daily = data["daily"]

    if not daily["last_date"]:
        return 0

    try:
        last_day = date.fromisoformat(daily["last_date"])
    except ValueError:
        return 0

    if (date.today() - last_day).days > 1:
        return 0

    return daily["streak"]


def record_daily_completion(data):
    """Call once, right when the player finishes today's Daily Challenge.
    Extends the streak if yesterday was the last completed day, starts a
    new streak otherwise, and does nothing if today was already recorded
    (so replaying today's puzzle can't inflate the streak).
    """
    daily = data["daily"]
    today = date.today().isoformat()

    if daily["last_date"] == today:
        return

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    daily["streak"] = daily["streak"] + 1 if daily["last_date"] == yesterday else 1
    daily["best"] = max(daily["best"], daily["streak"])
    daily["completed"] += 1
    daily["last_date"] = today


# --------------------------------------------------
# Reset
# --------------------------------------------------

def reset(data):
    """Wipes every level, the daily streak, achievement progress,
    achievement/reward unlocks, claimed features, shop purchases and
    stats back to a brand new save, in place (same dict, same reference)
    - but keeps the player's name, since that's an identity, not
    progress. Rewards reset along with the level completions they're
    computed from - keeping one unlocked after its levels are wiped
    would leave it permanently out of sync with what refresh() computes."""
    fresh = _default_save()
    data["coins"] = fresh["coins"]
    data["levels"] = fresh["levels"]
    data["last_level"] = fresh["last_level"]
    data["daily"] = fresh["daily"]
    data["shop"] = fresh["shop"]
    data["achievements"] = fresh["achievements"]
    data["unlocked"] = fresh["unlocked"]
    data["rewards_unlocked"] = fresh["rewards_unlocked"]
    data["rewards_claimed"] = fresh["rewards_claimed"]
    data["stats"] = fresh["stats"]