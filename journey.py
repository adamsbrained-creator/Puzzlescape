import math

import save_manager


# --------------------------------------------------
# Puzzlescape Journey
# --------------------------------------------------
# A second, separate way to play, next to the category system in
# main.py: one single "tower" of puzzles that get harder one after
# another - 12, 24, 48, 96, 192 and 384 pieces - plus one hidden 7th
# rung (768 pieces) that only appears once all six are finished. Unlike
# a category, a Journey level is gated in order: level 4 doesn't even
# open until level 3 is done.
#
# This file owns three things:
#
#   1. THE LADDER     - JOURNEY_LEVELS / JOURNEY_HIDDEN_LEVEL /
#                        JOURNEY_ALL, each level a plain dict shaped
#                        exactly like one from main.py's LEVELS, so
#                        open_level()/start_level() run one unchanged.
#   2. THE LOCKS      - is_unlocked() / is_finale_unlocked() / status(),
#                        read straight from the same save_manager data
#                        every other level already uses. A level's own
#                        completion is main.py's job to record (via
#                        save_manager.level_entry(...)["completed"]) -
#                        this file only ever reads that back.
#   3. THE MAP SHAPE  - cells() and hop_points(): where each node sits on
#                        the map grid, and the curve that joins one node
#                        to the next. All plain maths - main.py turns
#                        them into pixels and draws them.
#
# Nothing in here touches pygame - same rule as achievements.py and
# save_manager.py - so the ladder, the locking and the layout can all be
# read (and tested) without a display.
#
# ----- Pictures -----
# Each level looks for its own picture first:
#     assets/images/levels/journey/journey1.jpg ... journey7.jpg
# Until that file exists, the level uses the first picture of its theme
# instead (world1.jpg for the Photography rung, and so on), so the map
# is never full of blank placeholders. main.py does that swap at startup
# - see resolve_journey_pictures().


# (columns, rows, theme label, theme folder) for each regular rung, in
# climbing order. The theme is only flavour - the piece count is what
# makes each rung harder.
JOURNEY_STEPS = [
    (4, 3, "Photography", "world"),                    # 12 pieces
    (6, 4, "Nature", "nature"),                        # 24
    (8, 6, "Architecture", "architecture"),            # 48
    (12, 8, "Animals", "animals"),                     # 96
    (16, 12, "Movies & Shows", "movies_and_shows"),    # 192
    (24, 16, "World", "world"),                        # 384
]


def _build_levels():
    built = []
    for number, (columns, rows, theme, folder) in enumerate(JOURNEY_STEPS, start=1):
        built.append({
            "name": f"Journey {number}",
            "category_label": "Journey",
            "theme_label": theme,
            "journey_index": number,
            "image": f"assets/images/levels/journey/journey{number}.jpg",
            "fallback_image": f"assets/images/levels/{folder}/{folder}1.jpg",
            "columns": columns,
            "rows": rows,
        })
    return built


# The six regular rungs, in climbing order.
JOURNEY_LEVELS = _build_levels()

# The secret finale: one giant 768-piece puzzle, out of reach until the
# whole tower above has been climbed.
JOURNEY_HIDDEN_LEVEL = {
    "name": f"Journey {len(JOURNEY_LEVELS) + 1}",
    "category_label": "Journey",
    "theme_label": "???",
    "journey_index": len(JOURNEY_LEVELS) + 1,
    "image": f"assets/images/levels/journey/journey{len(JOURNEY_LEVELS) + 1}.jpg",
    "fallback_image": "assets/images/levels/ultimate/ultimate1.jpg",
    "columns": 32,
    "rows": 24,   # 768 pieces
    "hidden": True,
}

# The flat list used everywhere else - main.py's grid-sync and
# missing-picture checks, the achievements system, and the map screen all
# just walk this one list.
JOURNEY_ALL = JOURNEY_LEVELS + [JOURNEY_HIDDEN_LEVEL]


def piece_count(level):
    return level["columns"] * level["rows"]


def heading(level, revealed=True):
    """The line above a node shows its rung number and piece count only."""
    if not revealed:
        return f"LEVEL {level['journey_index']} - ???"
    return f"LEVEL {level['journey_index']} - {piece_count(level)} PIECES"


# --------------------------------------------------
# Locks
# --------------------------------------------------

def _completed(data, level):
    return save_manager.level_entry(data, level["name"])["completed"]


def is_unlocked(data, level):
    """Is this particular Journey level open to play right now?"""
    if level.get("hidden"):
        return is_finale_unlocked(data)

    index = level["journey_index"]
    if index <= 1:
        return True

    return _completed(data, JOURNEY_LEVELS[index - 2])


def is_finale_unlocked(data):
    """The hidden 7th rung - only once the whole regular tower is
    climbed."""
    return all(_completed(data, level) for level in JOURNEY_LEVELS)


def is_complete(data):
    """The whole Journey, finale included."""
    return all(_completed(data, level) for level in JOURNEY_ALL)


def status(data, level):
    """One of "completed", "current" or "locked" - everything the map
    needs to decide how to draw a node. "current" is a level that's
    unlocked but not yet finished - since levels unlock strictly in
    order, that's exactly one node at a time: the one that gets the glow
    and the PLAY chip."""
    if _completed(data, level):
        return "completed"

    if is_unlocked(data, level):
        return "current"

    return "locked"


def progress(data):
    """(completed, total) across the whole tower, finale included."""
    completed = sum(1 for level in JOURNEY_ALL if _completed(data, level))
    return completed, len(JOURNEY_ALL)


def current_level(data):
    """The single node the map should treat as "next up" - the first
    one that isn't completed yet, finale included. None only once the
    whole Journey is done."""
    for level in JOURNEY_ALL:
        if not _completed(data, level):
            return level
    return None


def previous_level(level):
    """The rung just before this one, or None for the first."""
    index = level["journey_index"]
    if index <= 1:
        return None
    return JOURNEY_ALL[index - 2]


# --------------------------------------------------
# Map shape
# --------------------------------------------------
# Nodes run left to right along a row; a short last row is pushed to the
# right, so with 7 nodes the map is four across the top and three below,
# tucked under the last three. One winding path joins them in order: at
# the end of a row it carries on past the last node, U-turns down,
# sweeps back across to the left, U-turns down again and runs into the
# first node of the next row (hop_points draws that curve).

COLUMNS = 4


def cells(count, columns=COLUMNS):
    """(column, row) grid cell for each of `count` nodes, in climbing
    order."""
    result = []
    for i in range(count):
        row = i // columns
        in_row = min(columns, count - row * columns)
        offset = columns - in_row if row > 0 else 0
        result.append((offset + i % columns, row))
    return result


def hop_points(a, b, overshoot=60, arc_steps=14):
    """The path from node centre `a` to node centre `b`, as a list of
    (x, y) points ready to draw as a thick line.

    Same row: a straight line. Different rows: the S-shaped connector
    described above - out `overshoot` pixels past `a`, a half-circle
    down, a straight run back to the left of `b`, a second half-circle
    down, and in to `b`."""
    ax, ay = a
    bx, by = b

    if abs(by - ay) < 1:
        return [a, b]

    gap = by - ay
    radius = gap / 4
    turn_right_x = ax + overshoot
    turn_left_x = bx - overshoot
    middle_y = ay + gap / 2

    points = [a, (turn_right_x, ay)]

    # First half-circle: centre (turn_right_x, ay + radius), from the
    # top (-90 degrees) round through the right-hand side to the bottom.
    for step in range(1, arc_steps):
        angle = -math.pi / 2 + math.pi * step / arc_steps
        points.append((
            turn_right_x + radius * math.cos(angle),
            ay + radius + radius * math.sin(angle),
        ))
    points.append((turn_right_x, middle_y))

    # The straight sweep back to the left.
    points.append((turn_left_x, middle_y))

    # Second half-circle: centre (turn_left_x, middle_y + radius), from
    # the top round through the LEFT-hand side to the bottom.
    for step in range(1, arc_steps):
        angle = -math.pi / 2 - math.pi * step / arc_steps
        points.append((
            turn_left_x + radius * math.cos(angle),
            middle_y + radius + radius * math.sin(angle),
        ))
    points.append((turn_left_x, by))

    points.append(b)
    return points