from datetime import date


# --------------------------------------------------
# Puzzlescape achievements
# --------------------------------------------------
# This file is the whole achievement system:
#
#   1. THE LIST      - every achievement (title, text, icon, goal), built
#                      by _build_definitions() below. Most of them are
#                      GENERATED from what setup() is told the game
#                      contains (one per category, size tiers, and so on)
#                      rather than typed out by hand - see each section's
#                      comment for how to add another one of that kind.
#   2. THE EVENTS    - small functions main.py calls when something
#                      happens (a level is finished, a theme is picked).
#                      Each one returns the achievements that JUST
#                      unlocked, so main.py can pop up a "trophy" banner.
#   3. THE READERS   - progress() / is_unlocked() / counts, used by the
#                      Achievements page (and the title screen's "you
#                      just earned..." line) to draw the cards.
#
# Nothing in here touches pygame. Everything is stored inside the same
# `save_data` dict that save_manager reads/writes, in three places:
#
#   save_data["achievements"]  key -> current progress number
#   save_data["unlocked"]      key -> date it was unlocked ("2026-09-24")
#   save_data["stats"]         small running totals the achievements need
#
# An unlock is PERMANENT: once a key is in save_data["unlocked"] it stays
# there, even if the numbers behind it later change.
#
# ----- Adding a one-off achievement -----
#   1. Add one dict to the relevant list in _build_definitions() (copy a
#      neighbour).
#   2. Say how its number is worked out:
#        - a "counter" is a number that goes up by one each time
#          something happens - call record(data, "your_key") from
#          main.py at that moment;
#        - anything worked out from data that already exists (like
#          "levels completed") goes in _derived_value().
#   3. That's it - the page and the pop-up pick it up by themselves.


# A puzzle counts as a "speed" run if it's finished faster than this.
SPEED_LIMIT_SECONDS = 60
# ...and a single "speed demon" puzzle has to beat this instead.
FAST_SINGLE_SECONDS = 30

# The total-completed milestones below the "finish everything" ladder,
# checked against every REGULAR puzzle (the 9 categories, not the hidden
# finale). Add a number here for another rung on the ladder.
COMPLETION_MILESTONES = [1, 10, 25, 50, 75]

# Any single completed puzzle at least this big earns its size tier.
SIZE_MILESTONES = [50, 100, 150]

# How many pieces placed (see on_level_completed) earns each tier.
PIECE_MILESTONES = [500, 2500, 10000]

# The two counters below (speed_solver, no_hints) each get a second,
# harder tier that just reads the same running counter at a higher goal
# - add a number here for another rung on either ladder.
SPEED_TIER_GOALS = [5, 20]
NO_HINTS_TIER_GOALS = [10, 50]
DAILY_STREAK_GOALS = [7, 30]

# Set by setup(), once, when the game starts.
_categories = []              # [{"key", "label", "levels": [name, ...]}, ...]
_regular_level_names = []     # every category puzzle, no hidden finale
_all_level_names = []         # regular puzzles + the hidden finale
_journey_level_names = []
_theme_keys = []
_level_piece_counts = {}      # level name -> columns * rows
_definitions = []


def setup(categories, all_level_names, journey_level_names, theme_keys, level_piece_counts):
    """Tell the system what the game currently contains, so the whole
    achievement list - one per category, every milestone rung, and so
    on - follows automatically as levels, categories or themes are
    added:

        categories          [{"key", "label", "levels": [name, ...]}, ...]
                             - the 9 (or however many) themed categories,
                             each with its own puzzle names, in order.
        all_level_names      every regular puzzle name PLUS the hidden
                             finale - used only for "finish literally
                             everything".
        journey_level_names  the Journey tower's rungs, in climbing order.
        theme_keys           every colour theme the player can choose.
        level_piece_counts   {level name -> columns * rows}, regular
                             puzzles only - used for the "biggest puzzle
                             solved" size tiers.
    """
    global _categories, _regular_level_names, _all_level_names
    global _journey_level_names, _theme_keys, _level_piece_counts, _definitions

    _categories = [dict(c) for c in categories]
    _regular_level_names = [name for c in _categories for name in c["levels"]]
    _all_level_names = list(all_level_names)
    _journey_level_names = list(journey_level_names or [])
    _theme_keys = list(theme_keys)
    _level_piece_counts = dict(level_piece_counts or {})
    _definitions = _build_definitions()


def _build_definitions():
    definitions = []

    # ---- One per category: complete all 10 of its puzzles ----
    for category in _categories:
        definitions.append({
            "key": f"category_{category['key']}",
            "title": f"{category['label'].upper()} MASTER",
            "text": f"Complete every {category['label']} puzzle",
            "icon": "trophy",
            "goal": max(1, len(category["levels"])),
            "coming_soon": False,
        })

    # ---- Total-puzzles-completed ladder, then the "everything" finale ----
    milestone_labels = {
        1: "FIRST STEPS",
        10: "GETTING HOOKED",
        25: "PUZZLE ENTHUSIAST",
        50: "PUZZLE FANATIC",
        75: "ALMOST THERE",
    }
    for goal in COMPLETION_MILESTONES:
        label = milestone_labels.get(goal, f"{goal} PUZZLES")
        definitions.append({
            "key": f"milestone_{goal}",
            "title": label,
            "text": "Complete your first puzzle" if goal == 1 else f"Complete {goal} puzzles",
            "icon": "medal",
            "goal": goal,
            "coming_soon": False,
        })

    definitions.append({
        "key": "master_puzzler",
        "title": "MASTER PUZZLER",
        "text": "Complete every level, secret finale included",
        "icon": "medal",
        "goal": max(1, len(_all_level_names)),
        "coming_soon": False,
    })

    # ---- Size tiers: the biggest single puzzle ever finished ----
    size_labels = {50: "GROWING BOLDER", 100: "CENTURY SOLVER", 150: "GRAND MASTER"}
    for goal in SIZE_MILESTONES:
        definitions.append({
            "key": f"size_{goal}",
            "title": size_labels.get(goal, f"{goal}-PIECE SOLVER"),
            "text": f"Complete a puzzle with {goal}+ pieces",
            "icon": "puzzle",
            "goal": 1,
            "coming_soon": False,
        })

    # ---- Lifetime pieces placed ----
    piece_labels = {500: "PIECE COLLECTOR", 2500: "PIECE HOARDER", 10000: "PIECE MASTER"}
    for goal in PIECE_MILESTONES:
        definitions.append({
            "key": f"pieces_{goal}",
            "title": piece_labels.get(goal, f"{goal} PIECES PLACED"),
            "text": f"Place {goal:,} puzzle pieces in total",
            "icon": "gem",
            "goal": goal,
            "coming_soon": False,
        })

    # ---- Journey ----
    definitions.append({
        "key": "tower_climber",
        "title": "TOWER CLIMBER",
        "text": "Reach the top of the Journey",
        "icon": "mountain",
        "goal": max(1, len(_journey_level_names)),
        "coming_soon": False,
    })
    halfway_goal = max(1, len(_journey_level_names) // 2)
    definitions.append({
        "key": "journey_halfway",
        "title": "HALFWAY UP",
        "text": f"Reach rung {halfway_goal} of the Journey",
        "icon": "mountain",
        "goal": halfway_goal,
        "coming_soon": False,
    })

    # ---- Speed, two tiers of the same running counter ----
    speed_labels = {5: "SPEED SOLVER", 20: "SPEED DEMON"}
    for goal in SPEED_TIER_GOALS:
        definitions.append({
            "key": f"speed_{goal}",
            "title": speed_labels.get(goal, f"SPEED x{goal}"),
            "text": f"Finish {goal} puzzles in under 1 min each",
            "icon": "stopwatch",
            "goal": goal,
            "coming_soon": False,
        })
    definitions.append({
        "key": "fast_finish",
        "title": "LIGHTNING FAST",
        "text": f"Finish a puzzle in under {FAST_SINGLE_SECONDS} seconds",
        "icon": "stopwatch",
        "goal": 1,
        "coming_soon": False,
    })

    # ---- No hints, two tiers of the same running counter ----
    hint_labels = {10: "NO HINTS", 50: "PURIST"}
    for goal in NO_HINTS_TIER_GOALS:
        definitions.append({
            "key": f"no_hints_{goal}",
            "title": hint_labels.get(goal, f"NO HINTS x{goal}"),
            "text": f"Finish {goal} puzzles without any hints",
            "icon": "bulb",
            "goal": goal,
            "coming_soon": False,
        })

    # ---- Daily streak, two tiers of the same running best ----
    streak_labels = {7: "DAILY STREAK", 30: "DEDICATED"}
    for goal in DAILY_STREAK_GOALS:
        definitions.append({
            "key": f"daily_streak_{goal}",
            "title": streak_labels.get(goal, f"{goal}-DAY STREAK"),
            "text": f"Finish the daily puzzle {goal} days in a row",
            "icon": "calendar",
            "goal": goal,
            "coming_soon": False,
        })

    # ---- Themes ----
    definitions.append({
        "key": "color_explorer",
        "title": "COLOR EXPLORER",
        "text": "Try every color theme",
        "icon": "palette",
        "goal": max(1, len(_theme_keys)),
        "coming_soon": False,
    })

    # ---- Not built yet ----
    definitions.append({
        # There's no share button yet. While "coming_soon" is True the
        # card shows COMING SOON and can't unlock. When sharing exists:
        # set coming_soon to False and call record(data, "social_sharer")
        # each time the player shares.
        "key": "social_sharer",
        "title": "SOCIAL SHARER",
        "text": "Share a puzzle",
        "icon": "share",
        "goal": 1,
        "coming_soon": True,
    })

    return definitions


def definitions():
    """Every achievement, in the order the page shows them."""
    return _definitions


# --------------------------------------------------
# How each number is worked out
# --------------------------------------------------

def _counter(data, key):
    value = data["achievements"].get(key, 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _completed_count(data, level_names):
    return sum(1 for name in level_names if data["levels"].get(name, {}).get("completed"))


def _max_completed_pieces(data):
    """The size (in pieces) of the biggest regular puzzle finished so
    far - 0 if nothing's been completed yet."""
    best = 0
    for name, count in _level_piece_counts.items():
        if count > best and data["levels"].get(name, {}).get("completed"):
            best = count
    return best


def _fastest_completed_seconds(data):
    """The quickest best_time across every completed puzzle (any kind),
    or None if nothing has a recorded time yet."""
    times = [
        entry["best_time"] for entry in data["levels"].values()
        if entry.get("completed") and entry.get("best_time") is not None
    ]
    return min(times) if times else None


def _derived_value(data, key):
    """The achievements whose number comes from other saved data rather
    than from its own counter. Returns None for a plain counter."""
    if key.startswith("category_"):
        category_key = key[len("category_"):]
        category = next((c for c in _categories if c["key"] == category_key), None)
        return _completed_count(data, category["levels"]) if category else None

    if key.startswith("milestone_"):
        return _completed_count(data, _regular_level_names)

    if key == "master_puzzler":
        return _completed_count(data, _all_level_names)

    if key.startswith("size_"):
        goal = int(key[len("size_"):])
        return 1 if _max_completed_pieces(data) >= goal else 0

    if key.startswith("pieces_"):
        return data["stats"]["lifetime_pieces_placed"]

    if key == "tower_climber" or key == "journey_halfway":
        return _completed_count(data, _journey_level_names)

    if key.startswith("speed_"):
        return _counter(data, "speed_solver")

    if key == "fast_finish":
        fastest = _fastest_completed_seconds(data)
        return 1 if fastest is not None and fastest < FAST_SINGLE_SECONDS else 0

    if key.startswith("no_hints_"):
        return _counter(data, "no_hints")

    if key.startswith("daily_streak_"):
        # The best run ever, not today's - one good week (or month)
        # unlocks it for good, and a broken streak afterwards can't take
        # it back.
        return data["daily"]["best"]

    if key == "color_explorer":
        tried = set(data["stats"]["themes_tried"])
        return len(tried & set(_theme_keys))

    return None


# --------------------------------------------------
# The engine
# --------------------------------------------------

def refresh(data):
    """Recomputes every achievement's number, unlocks whatever has
    reached its goal, and returns the list of achievements that JUST
    unlocked (an empty list most of the time). Every event function below
    ends by calling this, and main.py calls it once at startup so saves
    from before this system existed unlocks whatever it has already
    earned.
    """
    newly_unlocked = []

    for definition in _definitions:
        key = definition["key"]

        derived = _derived_value(data, key)
        if derived is not None:
            data["achievements"][key] = derived

        if definition["coming_soon"] or key in data["unlocked"]:
            continue

        if _counter(data, key) >= definition["goal"]:
            data["unlocked"][key] = date.today().isoformat()
            newly_unlocked.append(definition)

    return newly_unlocked


# --------------------------------------------------
# Events - call these from main.py when something happens
# --------------------------------------------------

def on_level_completed(data, seconds, used_hint, piece_count=0):
    """A puzzle was just finished. Call this AFTER the level has been
    marked completed and the daily streak (if any) has been recorded in
    `data`. `seconds` is the time it took; `used_hint` is whether the
    hint button was pressed at any point during this attempt;
    `piece_count` is how many pieces that puzzle had (0 for "don't know",
    e.g. an old call site that hasn't been updated)."""
    if seconds < SPEED_LIMIT_SECONDS:
        record(data, "speed_solver", refresh_now=False)

    if not used_hint:
        record(data, "no_hints", refresh_now=False)

    if piece_count > 0:
        data["stats"]["lifetime_pieces_placed"] += piece_count

    return refresh(data)


def on_theme_selected(data, theme_key):
    """The player picked (or started the game with) a color theme."""
    tried = data["stats"]["themes_tried"]
    if theme_key in _theme_keys and theme_key not in tried:
        tried.append(theme_key)

    return refresh(data)


def record(data, key, amount=1, refresh_now=True):
    """Adds to a plain counter achievement. Handy for anything new:
    record(save_data, "social_sharer") when the player shares."""
    data["achievements"][key] = _counter(data, key) + amount

    if refresh_now:
        return refresh(data)
    return []


# --------------------------------------------------
# Readers - used by the Achievements page
# --------------------------------------------------

def is_unlocked(data, key):
    return key in data["unlocked"]


def progress(data, definition):
    """The number to show on a card, never above the goal. An unlocked
    achievement always shows as full."""
    if is_unlocked(data, definition["key"]):
        return definition["goal"]

    return min(definition["goal"], _counter(data, definition["key"]))


def unlocked_count(data):
    return sum(1 for d in _definitions if is_unlocked(data, d["key"]))


def most_recent_unlock(data):
    """The single most recently unlocked achievement's definition, or
    None if nothing's unlocked yet - for a "you just earned..." line on
    the title screen."""
    unlocked = data["unlocked"]
    if not unlocked:
        return None

    latest_key = max(unlocked, key=lambda key: unlocked[key])
    for definition in _definitions:
        if definition["key"] == latest_key:
            return definition
    return None


def available_count():
    """How many achievements can be earned right now (the COMING SOON
    ones aren't counted)."""
    return sum(1 for d in _definitions if not d["coming_soon"])