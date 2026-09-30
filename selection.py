"""Puzzlescape selection tool.

Hold the left mouse button on empty space and drag: a box appears, and every
loose piece it touches gets selected - pieces sitting in the tray and pieces
already out on the table alike. Grab any selected piece and the WHOLE
selection comes with it, to wherever you drop it.

  - Pieces that came out of the tray are dealt into a tidy block around the
    cursor (dropping them all on one spot would just make a heap).
  - Pieces already on the table keep their places relative to each other.
  - Pieces that are joined together (see Puzzle._try_join) always move as
    one, and selecting one of them selects the rest.
  - Dropped over the tray, the loose pieces go back into it. Anywhere else,
    each piece is checked against the board and its neighbours exactly like
    a normal drop.
  - Hold SHIFT while boxing to ADD to the current selection instead of
    replacing it. Clicking empty space clears it.

HOW IT IS WIRED IN
------------------
This file deliberately leaves puzzle.py alone. install() wraps a handful of
methods on puzzle.Piece / puzzle.Puzzle at runtime (each wrapper only
changes behaviour while a selection is actually being dragged, and calls the
original untouched otherwise), and each hook is skipped if that method
doesn't exist in your version of puzzle.py. main.py only needs three small
calls - selection.press / selection.motion / selection.release - which
apply_selection_patch.py adds for you.
"""

import math

import pygame

import puzzle as _puzzle

# A box smaller than this (both sides) counts as a plain click, not a drag.
CLICK_SLOP = 4

# Fallback highlight colour if ui.py can't be asked for the theme's accent.
_FALLBACK_ACCENT = (120, 190, 255)


# --------------------------------------------------------------------------
# Per-puzzle state, stored on the Puzzle object itself so it disappears with
# it (restarting or leaving a puzzle builds a new Puzzle = a clean slate).
# --------------------------------------------------------------------------

def _state(puzzle):
    state = getattr(puzzle, "_selection_state", None)
    if state is None:
        state = {"selected": [], "marquee": None, "preview": []}
        puzzle._selection_state = state
    return state


def selected_pieces(puzzle):
    """The pieces currently selected (a copy; safe to loop over)."""
    if puzzle is None:
        return []
    return list(_state(puzzle)["selected"])


def clear(puzzle):
    if puzzle is None:
        return
    state = _state(puzzle)
    state["selected"] = []
    state["preview"] = []
    state["marquee"] = None


# --------------------------------------------------------------------------
# Geometry: where a piece really is on screen
# --------------------------------------------------------------------------

def _tight(piece, kind, image):
    """The box of a piece image's actually-visible pixels (the bitmap is
    padded for tabs). Cached per image, since scanning pixels every mouse
    move would be wasteful."""
    cache = piece.__dict__.setdefault("_sel_tight", {})
    key = (kind, id(image))
    box = cache.get(key)
    if box is None:
        box = image.get_bounding_rect()
        if box.width <= 0 or box.height <= 0:
            box = pygame.Rect(0, 0, image.get_width(), image.get_height())
        cache[key] = box
    return box


def _visible_rect(piece):
    if piece.in_tray:
        image = piece.tray_image
        ox, oy = piece.tray_pos
        box = _tight(piece, "tray", image)
    else:
        image = piece.image
        ox, oy = piece.position
        box = _tight(piece, "free", image)
    return pygame.Rect(round(ox + box.x), round(oy + box.y), box.width, box.height)


def _box(a, b):
    left, right = sorted((a[0], b[0]))
    top, bottom = sorted((a[1], b[1]))
    return pygame.Rect(left, top, right - left, bottom - top)


def _expand_groups(pieces):
    """Joined pieces travel together, so selecting any one selects all."""
    seen = set()
    out = []
    for p in pieces:
        for member in getattr(p, "group", None) or [p]:
            if id(member) not in seen:
                seen.add(id(member))
                out.append(member)
    return out


def _pieces_in_box(puzzle, box):
    carousel = getattr(puzzle, "tray_style", "pile") == "carousel"
    hits = []
    for p in puzzle.pieces:
        if p.is_snapped:
            continue
        rect = _visible_rect(p)
        if not rect.colliderect(box):
            continue
        if p.in_tray and carousel:
            # The carousel hides whatever has scrolled past the tray's
            # edge - only pieces actually visible can be boxed.
            shown = rect.clip(puzzle.piece_area)
            if shown.width <= 0 or shown.height <= 0 or not shown.colliderect(box):
                continue
        hits.append(p)

    hits = _expand_groups(hits)
    order = {id(p): i for i, p in enumerate(puzzle.pieces)}
    hits.sort(key=lambda p: order.get(id(p), 0))
    return [p for p in hits if not p.is_snapped]


# --------------------------------------------------------------------------
# The three calls main.py makes
# --------------------------------------------------------------------------

def press(puzzle, pos):
    """Left button went down on the puzzle screen (and not on any button).

    Returns:
      a Piece  - the click landed on a selected piece: the whole selection
                 has been picked up; the caller should treat that piece as
                 the one being dragged (selected_piece = it).
      True     - the click started a selection box; nothing else to do.
      None     - not ours; carry on with normal handling.
    """
    if puzzle is None:
        return None

    state = _state(puzzle)
    hit = puzzle.piece_at(pos)

    if hit is not None:
        if len(state["selected"]) > 1 and hit in state["selected"]:
            _begin_drag(puzzle, hit, pos, state["selected"])
            return hit
        # Picking up some other piece the normal way drops the selection.
        state["selected"] = []
        return None

    # Empty carousel tray space scrolls the carousel - leave that alone.
    if (
        getattr(puzzle, "tray_style", "pile") == "carousel"
        and puzzle.piece_area.collidepoint(pos)
    ):
        return None

    additive = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
    state["marquee"] = {
        "start": tuple(pos),
        "cur": tuple(pos),
        "base": list(state["selected"]) if additive else [],
    }
    if not additive:
        state["selected"] = []
    state["preview"] = []
    return True


def motion(puzzle, pos):
    """Mouse moved. True while a selection box is being dragged."""
    if puzzle is None:
        return False
    state = _state(puzzle)
    marquee = state["marquee"]
    if marquee is None:
        return False

    marquee["cur"] = tuple(pos)
    box = _box(marquee["start"], pos)
    if box.width >= CLICK_SLOP or box.height >= CLICK_SLOP:
        state["preview"] = _pieces_in_box(puzzle, box)
    else:
        state["preview"] = []
    return True


def release(puzzle, pos):
    """Left button came up. Finishes a selection box if one is open."""
    if puzzle is None:
        return
    state = _state(puzzle)
    marquee = state["marquee"]
    if marquee is None:
        return

    state["marquee"] = None
    state["preview"] = []
    box = _box(marquee["start"], pos)
    if box.width < CLICK_SLOP and box.height < CLICK_SLOP:
        return  # just a click on empty space: selection already cleared

    chosen = _pieces_in_box(puzzle, box)
    if marquee["base"]:
        chosen = _expand_groups(marquee["base"] + chosen)
        order = {id(p): i for i, p in enumerate(puzzle.pieces)}
        chosen.sort(key=lambda p: order.get(id(p), 0))
        chosen = [p for p in chosen if not p.is_snapped]
    state["selected"] = chosen


# --------------------------------------------------------------------------
# Picking the whole selection up
# --------------------------------------------------------------------------

def _begin_drag(puzzle, primary, pos, selected):
    carry = _expand_groups(selected)
    carry_ids = {id(p) for p in carry}

    # Bring everything to the front, keeping its stacking order.
    moving = [p for p in puzzle.pieces if id(p) in carry_ids]
    for p in moving:
        puzzle.pieces.remove(p)
    puzzle.pieces.extend(moving)

    from_tray = [p for p in carry if p.in_tray and p is not primary]
    primary_was_in_tray = primary.in_tray

    # Pick the grabbed piece up the normal way (this is what makes it grow
    # and straighten under the cursor if it came out of the tray).
    primary.start_drag(pos)
    anchor = primary.center()

    # Deal the tray pieces out into a block around the cursor.
    if from_tray:
        sizes = [_tight(p, "free", p.image) for p in from_tray]
        cell_w = max(6, 0.62 * sum(s.width for s in sizes) / len(sizes))
        cell_h = max(6, 0.62 * sum(s.height for s in sizes) / len(sizes))
        slots = len(from_tray) + 1  # slot 0 is the grabbed piece's own spot
        cols = max(1, math.ceil(math.sqrt(slots)))
        rows = max(1, math.ceil(slots / cols))
        points = []
        for r in range(rows):
            for c in range(cols):
                points.append((
                    (c - (cols - 1) / 2) * cell_w,
                    (r - (rows - 1) / 2) * cell_h,
                ))
        points.sort(key=lambda pt: pt[0] ** 2 + pt[1] ** 2)
        origin = points[0]
        offsets = [(x - origin[0], y - origin[1]) for x, y in points[1:]]

        for piece, (dx, dy) in zip(from_tray, offsets):
            piece.in_tray = False
            piece.angle = 0.0
            piece.scale = 1.0
            piece.dragging = False
            piece._set_center(pygame.Vector2(anchor) + pygame.Vector2(dx, dy))

    # Wire up the carry: drag_to (wrapped below) moves everything in
    # primary.carry_others by however far the grabbed piece moves.
    own = {id(m) for m in (getattr(primary, "group", None) or [primary])}
    for p in carry:
        p.carry = carry
        p.carry_others = ()
    primary.carry_others = [p for p in carry if id(p) not in own]

    _state(puzzle)["selected"] = carry
    return primary_was_in_tray


# --------------------------------------------------------------------------
# Dropping it
# --------------------------------------------------------------------------

def _clamp_units(bounds, pieces):
    """Keep the whole carried set inside `bounds` as one rigid block, the
    same way Puzzle._clamp_group keeps a joined cluster together: work out
    the one nudge the worst-placed piece needs, apply it to everyone."""
    dx = dy = 0.0
    for p in pieces:
        cx, cy = p.center()
        scale = getattr(p, "scale", 1.0)
        half_w = p.image.get_width() / 2
        half_h = p.image.get_height() / 2
        min_x = min(bounds.left + getattr(p, "extent_left", half_w) * scale, bounds.centerx)
        max_x = max(bounds.right - getattr(p, "extent_right", half_w) * scale, bounds.centerx)
        min_y = min(bounds.top + getattr(p, "extent_top", half_h) * scale, bounds.centery)
        max_y = max(bounds.bottom - getattr(p, "extent_bottom", half_h) * scale, bounds.centery)

        if cx < min_x:
            dx = max(dx, min_x - cx)
        elif cx > max_x:
            dx = min(dx, max_x - cx)
        if cy < min_y:
            dy = max(dy, min_y - cy)
        elif cy > max_y:
            dy = min(dy, max_y - cy)

    if dx or dy:
        for p in pieces:
            p.position += pygame.Vector2(dx, dy)


def _finish_drag(puzzle, primary, mouse_pos, carry):
    primary.end_drag(mouse_pos)  # upright, full size, drag_to carries the rest
    bounds = getattr(puzzle, "bounds", None)
    if bounds is not None:
        _clamp_units(bounds, carry)

    for p in carry:
        p.carry = None
        p.carry_others = ()

    over_tray = puzzle.piece_area.collidepoint(mouse_pos)
    still_out = []

    for p in carry:
        if over_tray and len(getattr(p, "group", None) or [p]) == 1:
            _send_to_tray(puzzle, p, mouse_pos, primary)
        else:
            still_out.append(p)

    # Same checks a normal drop gets, piece by piece: does it sit on its
    # slot on the board, or against a correct neighbour?
    for p in still_out:
        if p.is_snapped:
            continue
        p.check_snap()
        if p.is_snapped:
            puzzle._snap_group(p)
        else:
            puzzle._try_join(p)

    state = _state(puzzle)
    state["selected"] = [
        p for p in carry if not p.is_snapped and not p.in_tray
    ]


def _send_to_tray(puzzle, piece, mouse_pos, primary):
    style = getattr(puzzle, "tray_style", "pile")
    if style == "wheel":
        puzzle._return_to_wheel(piece)
    elif style == "carousel":
        puzzle._return_to_carousel(piece)
    else:
        # Keep the pieces' spread relative to the one under the cursor,
        # scaled down to tray size, so a big drop doesn't land as one dot.
        shrink = getattr(piece, "tray_scale", 0.5)
        offset = (piece.center() - primary.center()) * shrink
        target = pygame.Vector2(mouse_pos) + offset
        piece.grab_local = pygame.Vector2(0, 0)
        piece.dragging = False
        puzzle._return_to_pile(piece, target)


# --------------------------------------------------------------------------
# Drawing: highlight + the box itself
# --------------------------------------------------------------------------

def _accent():
    try:
        import ui
        color = ui.GRADIENT_PRIMARY[0]
        return (int(color[0]), int(color[1]), int(color[2]))
    except Exception:
        return _FALLBACK_ACCENT


def _tint(piece, kind, image, color):
    """A see-through copy of a piece's silhouette in the accent colour,
    cached per piece so highlighting many pieces costs one blit each."""
    cache = piece.__dict__.setdefault("_sel_tint", {})
    key = (kind, id(image), color)
    overlay = cache.get(key)
    if overlay is None:
        overlay = image.copy()
        overlay.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        overlay.fill((color[0], color[1], color[2], 0), special_flags=pygame.BLEND_RGBA_ADD)
        overlay.fill((255, 255, 255, 105), special_flags=pygame.BLEND_RGBA_MULT)
        if len(cache) > 6:
            cache.clear()
        cache[key] = overlay
    return overlay


def draw(puzzle, surface):
    """Called after the puzzle draws itself: highlight every selected (or
    about-to-be-selected) piece and draw the selection box on top."""
    state = _state(puzzle)
    marquee = state["marquee"]
    if not state["selected"] and marquee is None:
        return

    color = _accent()
    carousel = getattr(puzzle, "tray_style", "pile") == "carousel"

    shown = list(state["selected"])
    if marquee is not None:
        have = {id(p) for p in shown}
        shown += [p for p in state["preview"] if id(p) not in have]

    for p in shown:
        if p.is_snapped:
            continue
        if p.in_tray:
            image = p.tray_image
            x, y = p.tray_pos
            if carousel:
                surface.set_clip(puzzle.piece_area)
                surface.blit(_tint(p, "tray", image, color), (x, y))
                surface.set_clip(None)
            else:
                surface.blit(_tint(p, "tray", image, color), (x, y))
        else:
            image = p.image
            x, y = round(p.position.x), round(p.position.y)
            surface.blit(_tint(p, "free", image, color), (x, y))

    if marquee is not None:
        box = _box(marquee["start"], marquee["cur"])
        if box.width >= 2 and box.height >= 2:
            fill = pygame.Surface(box.size, pygame.SRCALPHA)
            fill.fill((color[0], color[1], color[2], 40))
            surface.blit(fill, box.topleft)
            pygame.draw.rect(surface, color, box, width=2, border_radius=4)


# --------------------------------------------------------------------------
# install(): the runtime hooks into puzzle.py
# --------------------------------------------------------------------------

_installed = False


def install():
    """Wrap the few puzzle.py methods the selection drag needs. Safe to call
    more than once; every wrapper hands straight through to the original
    method unless a selection is actually being dragged."""
    global _installed
    if _installed:
        return
    _installed = True

    Piece = getattr(_puzzle, "Piece", None)
    Puzzle = getattr(_puzzle, "Puzzle", None)
    if Piece is None or Puzzle is None:
        return

    # ---- Piece.drag_to: carry the rest of the selection along ----
    original_drag_to = getattr(Piece, "drag_to", None)
    if original_drag_to is not None:
        def drag_to(self, mouse_pos):
            others = getattr(self, "carry_others", None)
            if not others:
                return original_drag_to(self, mouse_pos)
            before = self.center()
            original_drag_to(self, mouse_pos)  # also moves self's own joined group
            delta = self.center() - before
            if delta:
                for member in others:
                    member.position += delta
        Piece.drag_to = drag_to

    # ---- Piece.clamp_to: the selection is clamped as ONE block instead ----
    original_clamp_to = getattr(Piece, "clamp_to", None)
    if original_clamp_to is not None:
        def clamp_to(self, bounds):
            if getattr(self, "carry", None):
                return None
            return original_clamp_to(self, bounds)
        Piece.clamp_to = clamp_to

    # ---- Piece.update: no shrink-toward-the-tray preview for a selection ----
    original_piece_update = getattr(Piece, "update", None)
    if original_piece_update is not None:
        def piece_update(self, dt, mouse_pos, to_tray=False):
            if getattr(self, "carry", None):
                to_tray = False
            return original_piece_update(self, dt, mouse_pos, to_tray)
        Piece.update = piece_update

    # ---- Puzzle._clamp_group: a joined cluster inside the selection is
    # clamped together with the rest of it ----
    original_clamp_group = getattr(Puzzle, "_clamp_group", None)
    if original_clamp_group is not None:
        def clamp_group(self, group):
            for member in group:
                carry = getattr(member, "carry", None)
                if carry:
                    return original_clamp_group(self, carry)
            return original_clamp_group(self, group)
        Puzzle._clamp_group = clamp_group

    # ---- Puzzle.update: keep the dragged selection inside the window ----
    original_update = getattr(Puzzle, "update", None)
    if original_update is not None:
        def update(self, dt, mouse_pos):
            result = original_update(self, dt, mouse_pos)
            bounds = getattr(self, "bounds", None)
            if bounds is not None:
                for p in self.pieces:
                    carry = getattr(p, "carry", None)
                    if carry and p.dragging:
                        _clamp_units(bounds, carry)
                        break
            return result
        Puzzle.update = update

    # ---- Puzzle.release_piece: dropping a selection ----
    original_release = getattr(Puzzle, "release_piece", None)
    if original_release is not None:
        def release_piece(self, piece, mouse_pos):
            carry = getattr(piece, "carry", None)
            if not carry:
                return original_release(self, piece, mouse_pos)
            return _finish_drag(self, piece, mouse_pos, carry)
        Puzzle.release_piece = release_piece

    # ---- Puzzle.draw_active: the highlight + the box, on top of it all ----
    original_draw_active = getattr(Puzzle, "draw_active", None)
    if original_draw_active is not None:
        def draw_active(self, surface):
            result = original_draw_active(self, surface)
            draw(self, surface)
            return result
        Puzzle.draw_active = draw_active
