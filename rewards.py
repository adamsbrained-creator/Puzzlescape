from datetime import date


# --------------------------------------------------
# Puzzlescape rewards
# --------------------------------------------------
# Achievements (achievements.py) are a scoreboard - they track and show
# off progress, but nothing is ever locked behind them. This file is the
# opposite: every entry here GATES something real - a setting, a color
# theme, a whole game mode - so the game starts small and opens up as
# you play, instead of handing over every option on the very first
# screen.
#
# The shape of this file deliberately mirrors achievements.py:
#
#   1. THE LADDER    - every reward (what it unlocks, what it takes, its
#                      icon), in _build_definitions() below. To change a
#                      goal or add a new one, edit only that.
#   2. THE ENGINE    - refresh() recomputes every reward's progress from
#                      the save data and unlocks whatever has reached its
#                      goal, returning what JUST unlocked so main.py can
#                      pop up a banner exactly like an achievement does.
#   3. THE GATE      - has_feature() is the one function the rest of the
#                      game calls to ask "am I allowed to show/use this
#                      yet?". A feature nothing in the ladder mentions is
#                      always allowed - so a brand new feature defaults
#                      to unlocked until a reward is deliberately wired
#                      to gate it, rather than silently vanishing.
#
# Nothing in here touches pygame, and nothing in here invents its own
# counters: every reward's progress is read straight from the level
# completion data save_manager already tracks (the same
# save_data["levels"][name]["completed"] flags the category grid and
# achievements both use), plus one small dict of its own for which
# rewards have actually been unlocked:
#
#   save_data["rewards_unlocked"]   key -> date it was unlocked
#
# An unlock is PERMANENT, exactly like an achievement: once a key is in
# there it stays, even if the save data behind its condition later looks
# different (e.g. Reset Progress).
#
# ----- Adding a new reward -----
#   1. Add one dict to _build_definitions() (copy an existing one).
#   2. Give it a "feature" string - the flag the rest of the game will
#      check with has_feature(data, "your_flag").
#   3. Pick a "condition" (see _current_value() for the ones available,
#      or add a new branch there for a new kind of goal).
#   4. Wherever the feature is drawn or used in main.py, wrap it with
#      `if rewards.has_feature(save_data, "your_flag"):` (or show it
#      locked - see locked_hint() for the explanatory text to pair with
#      a lock icon).


# --------------------------------------------------
# The ladder
# --------------------------------------------------
# Set by setup(), once, when the game starts.
_category_groups = []       # [(category_key, [level_name, ...]), ...]
_all_puzzle_names = []      # every regular category level + every Journey level
_definitions = []


def setup(categories, journey_level_names):
    """Tell the system what the game currently contains: each category's
    key and the names of its levels, and the Journey ladder's level
    names (Journey levels count toward "puzzles completed" the same as
    any other level, but aren't part of any category group).

        categories             [{"key", "label", "levels": [name, ...]}, ...]
                                 - same shape main.py already builds for
                                 achievements.setup().
        journey_level_names    the Journey tower's rungs, in climbing order.

    Goals that depend on these (a whole category, "every category")
    follow automatically as levels or categories are added or removed."""
    global _category_groups, _all_puzzle_names, _definitions

    _category_groups = [(c["key"], list(c["levels"])) for c in categories]
    _all_puzzle_names = [
        name for _key, names in _category_groups for name in names
    ] + list(journey_level_names)
    _definitions = _build_definitions()


def _build_definitions():
    return [
        {
            "key": "dark_theme",
            "title": "Dark Theme",
            "text": "Finish your first puzzle",
            "icon": "moon",
            "feature": "dark_mode",
            "goal": 1,
            "condition": {"type": "puzzles_completed"},
        },
        {
            "key": "hint_button",
            "title": "Hint Button",
            "text": "Finish 3 puzzles",
            "icon": "bulb",
            "feature": "hint_button",
            "goal": 3,
            "condition": {"type": "puzzles_completed"},
        },
        {
            "key": "minimal_header",
            "title": "Minimal Header",
            "text": "Finish 5 puzzles",
            "icon": "medal",
            "feature": "minimal_header",
            "goal": 5,
            "condition": {"type": "puzzles_completed"},
        },
        {
            "key": "board_opacity",
            "title": "Board Opacity",
            "text": "Finish 3 puzzles",
            "icon": "palette",
            "feature": "board_opacity",
            "goal": 3,
            "condition": {"type": "puzzles_completed"},
        },
        {
            "key": "color_themes",
            "title": "Color Themes",
            "text": "Complete every puzzle in Photography",
            "icon": "palette",
            "feature": "color_themes",
            "goal": 1,
            "condition": {"type": "category_completed", "category": "photography"},
        },
        {
            "key": "wheel_tray",
            "title": "Wheel Tray",
            "text": "Fully complete 3 categories",
            "icon": "wheel",
            "feature": "tray_wheel",
            "goal": 3,
            "condition": {"type": "categories_completed_count"},
        },
        {
            "key": "carousel_tray",
            "title": "Carousel Tray",
            "text": "Fully complete 6 categories",
            "icon": "wheel",
            "feature": "tray_carousel",
            "goal": 6,
            "condition": {"type": "categories_completed_count"},
        },
        {
            "key": "journey_mode",
            "title": "Journey Mode",
            "text": "Complete every puzzle in every category",
            "icon": "mountain",
            "feature": "journey",
            "goal": 1,
            "condition": {"type": "all_categories_completed"},
        },
    ]


def definitions():
    """Every reward, in the order the page shows them (easiest first)."""
    return _definitions


# --------------------------------------------------
# How each reward's progress is worked out - always derived from
# save_data["levels"], never its own counter.
# --------------------------------------------------

def _group_names(category_key):
    for key, names in _category_groups:
        if key == category_key:
            return names
    return []


def _is_category_complete(data, category_key):
    names = _group_names(category_key)
    return bool(names) and all(
        data["levels"].get(name, {}).get("completed") for name in names
    )


def _categories_completed_count(data):
    return sum(1 for key, _names in _category_groups if _is_category_complete(data, key))


def _total_puzzles_completed(data):
    return sum(
        1 for name in _all_puzzle_names
        if data["levels"].get(name, {}).get("completed")
    )


def _current_value(data, condition):
    ctype = condition["type"]

    if ctype == "puzzles_completed":
        return _total_puzzles_completed(data)

    if ctype == "categories_completed_count":
        return _categories_completed_count(data)

    if ctype == "category_completed":
        return 1 if _is_category_complete(data, condition["category"]) else 0

    if ctype == "all_categories_completed":
        total = len(_category_groups)
        return 1 if total and _categories_completed_count(data) >= total else 0

    return 0


# --------------------------------------------------
# The engine
# --------------------------------------------------

def refresh(data):
    """Recomputes every reward's progress and unlocks whatever has just
    reached its goal, returning the list of rewards that JUST unlocked
    (usually empty). Call this any time completed-level data changes -
    after a level is marked completed, after Reset Progress, and once at
    startup so an existing save picks up everything it's already earned.
    """
    newly_unlocked = []

    for definition in _definitions:
        key = definition["key"]

        if key in data["rewards_unlocked"]:
            continue

        if _current_value(data, definition["condition"]) >= definition["goal"]:
            data["rewards_unlocked"][key] = date.today().isoformat()
            newly_unlocked.append(definition)

    return newly_unlocked


# --------------------------------------------------
# The gate - what the rest of the game actually calls
# --------------------------------------------------

def has_feature(data, feature):
    """Is `feature` available right now? A feature no reward mentions at
    all is always available - only a feature deliberately given to a
    reward's "feature" field can ever be locked."""
    owners = [d for d in _definitions if d["feature"] == feature]
    if not owners:
        return True

    return any(is_claimed(data, d["key"]) for d in owners)


def locked_hint(feature):
    """'Finish 3 puzzles', ready to show next to a locked control's lock
    icon - the text of the first reward that grants this feature, or
    None if the feature isn't gated by anything."""
    for definition in _definitions:
        if definition["feature"] == feature:
            return definition["text"]
    return None


# --------------------------------------------------
# Readers - used by is_unlocked/progress and any Rewards page
# --------------------------------------------------

def is_unlocked(data, key):
    return key in data["rewards_unlocked"]


def is_claimed(data, key):
    return key in data.get("rewards_claimed", {})


def claim(data, key):
    """Claim an unlocked reward once and return its definition."""
    if not is_unlocked(data, key) or is_claimed(data, key):
        return None
    definition = next((item for item in _definitions if item["key"] == key), None)
    if definition is None:
        return None
    data.setdefault("rewards_claimed", {})[key] = date.today().isoformat()
    return definition


def progress(data, definition):
    """The number to show on a card, never above the goal. An unlocked
    reward always shows as full."""
    if is_unlocked(data, definition["key"]):
        return definition["goal"]

    return min(definition["goal"], _current_value(data, definition["condition"]))


def unlocked_count(data):
    return sum(1 for d in _definitions if is_unlocked(data, d["key"]))


def most_recent_unlock(data):
    """The single most recently unlocked reward's definition, or None if
    nothing's unlocked yet."""
    unlocked = data["rewards_unlocked"]
    if not unlocked:
        return None

    latest_key = max(unlocked, key=lambda key: unlocked[key])
    for definition in _definitions:
        if definition["key"] == latest_key:
            return definition
    return None