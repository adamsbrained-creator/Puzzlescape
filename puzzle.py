import math
import pygame
import random


class Piece:
    def __init__(self, image, correct_position, initial_position, col, row, shadow=None):
        self.image = image
        self.correct_position = pygame.Vector2(correct_position)

        # How far this piece's actually-visible (non-transparent) pixels
        # reach past its own centre, in each of the 4 directions - used
        # by clamp_to() below. `image` is padded equally on every side to
        # leave room for a protruding tab (see Puzzle.create_pieces), but
        # a lot of pieces don't have a tab on every side - an edge piece
        # has none on its outer side at all - so most of that padding is
        # empty on most pieces. Measuring the real opaque extent, once,
        # here, rather than just using the padded image's own full half
        # width/height, keeps the drag clamp as tight as it can be
        # without ever clipping a piece's actual visible corner.
        content = image.get_bounding_rect()
        image_w, image_h = image.get_size()
        self.extent_left = image_w / 2 - content.left
        self.extent_right = content.right - image_w / 2
        self.extent_top = image_h / 2 - content.top
        self.extent_bottom = content.bottom - image_h / 2

        # `position` is always the top-left of the FULL-SIZE, upright image
        # (that's what snapping compares against the board).
        self.position = pygame.Vector2(initial_position)

        # A soft drop shadow shaped like this exact piece (tabs, blanks
        # and all) - see Puzzle._build_piece_shadow. `shadow` is the
        # blurred silhouette surface, `shadow_pad` is how far it extends
        # past the piece's own edges (so it lines up when blitted).
        self.shadow, self.shadow_pad = shadow if shadow else (None, 0)

        # ---- Pile ("in the tray") look ----
        # While a piece sits in the heap it is shown as a smaller,
        # randomly rotated copy of itself. These are built once in
        # Puzzle.create_pieces so drawing the pile costs nothing extra.
        self.in_tray = True
        self.tray_image = None
        self.tray_pos = (0, 0)          # top-left of tray_image on screen
        self.tray_shadow = None
        self.tray_shadow_pos = (0, 0)
        self.tray_center = pygame.Vector2(0, 0)
        self.tray_angle = 0.0
        self.tray_scale = 1.0

        # Current visual state while being picked up / carried. It eases
        # from the pile look (tray_angle / tray_scale) to upright + full
        # size (0 / 1). At rest it is always exactly (0, 1).
        self.angle = 0.0
        self.scale = 1.0
        self.grab_local = pygame.Vector2(0, 0)  # grabbed point, relative to piece centre, in full-size upright pixels

        self.col = col
        self.row = row
        self.dragging = False
        self.drag_offset = pygame.Vector2(0, 0)
        self.is_snapped = False
        self.snap_tolerance = 25

        # Other pieces this one is currently joined to (itself included) -
        # see Puzzle._try_join. A lone, unjoined piece is a group of one.
        # All members of a group share this exact same list object, so
        # joining/merging is just growing one list and repointing this
        # attribute on the pieces gained from the other side - see
        # Puzzle._try_join and Puzzle._snap_group.
        self.group = [self]

    # ---- geometry helpers ----

    def center(self):
        return self.position + pygame.Vector2(self.image.get_size()) / 2

    def _set_center(self, center):
        self.position = pygame.Vector2(center) - pygame.Vector2(self.image.get_size()) / 2

    # ---- dragging ----

    def start_drag(self, mouse_pos):
        """Pick the piece up. The exact spot under the cursor stays under
        the cursor while the piece grows and straightens itself."""
        mouse = pygame.Vector2(mouse_pos)

        if self.in_tray:
            self.angle = self.tray_angle
            self.scale = self.tray_scale
            offset = mouse - self.tray_center
            # invert the rotation/scale the pile applies for display
            self.grab_local = offset.rotate(self.angle) / self.scale
            self.in_tray = False
        else:
            self.angle = 0.0
            self.scale = 1.0
            self.grab_local = mouse - self.center()

        self.dragging = True
        self.drag_to(mouse)

    def drag_to(self, mouse_pos):
        # main.py calls this directly on every raw mouse-move event (for
        # immediate tracking), separately from Puzzle.update()'s own
        # once-per-frame call - so this, not that, is the one place a
        # dragged piece's position actually changes. Doing the group
        # carry-along here, right where the position itself changes,
        # means it can never miss an update from a call it doesn't know
        # about; doing it by comparing before/after around some OTHER
        # call site risks measuring only part of the movement (whatever
        # happened since the last time THAT particular call site ran),
        # leaving the rest of the group lagging and then jumping to
        # catch up - which is exactly what it was doing.
        before = self.center()
        shown_offset = self.grab_local.rotate(-self.angle) * self.scale
        self._set_center(pygame.Vector2(mouse_pos) - shown_offset)

        if len(self.group) > 1:
            delta = self.center() - before
            if delta:
                for member in self.group:
                    if member is not self:
                        member.position += delta

    def end_drag(self, mouse_pos):
        # Finish any pick-up animation instantly so the piece is upright
        # and full size before it is checked against the board.
        self.angle = 0.0
        self.scale = 1.0
        self.drag_to(mouse_pos)
        self.dragging = False

    def update(self, dt, mouse_pos, to_tray=False):
        """Ease toward the pile look while hovering over the tray
        (`to_tray`), or toward upright + full size everywhere else."""
        if to_tray:
            target_angle, target_scale = self.tray_angle, self.tray_scale
        else:
            target_angle, target_scale = 0.0, 1.0

        if self.angle != target_angle or self.scale != target_scale:
            k = 1 - math.exp(-dt * 24)
            self.angle += (target_angle - self.angle) * k
            self.scale += (target_scale - self.scale) * k

            if abs(self.angle - target_angle) < 0.4 and abs(self.scale - target_scale) < 0.01:
                self.angle = target_angle
                self.scale = target_scale

        if self.dragging:
            self.drag_to(mouse_pos)

    def check_snap(self):
        if self.position.distance_to(self.correct_position) < self.snap_tolerance:
            self.position = pygame.Vector2(self.correct_position)
            self.is_snapped = True
        else:
            self.is_snapped = False

    def clamp_to(self, bounds):
        """Keeps a dragged piece from being pushed out to (or past) the
        edge of the window - and nothing more than that: a corner piece
        has to be draggable all the way into a corner cell, however
        close that cell sits to the window's own edge, or the puzzle
        isn't solvable.

        Clamps against each side's own real extent (see __init__) rather
        than the piece's padded image size, since most pieces don't have
        a protruding tab on every side - using the full padded size on
        every side left a piece unable to get anywhere near the window's
        edge even on the sides where it had nothing sticking out.

        This also assumes the piece is upright (angle 0), true while
        it's actually being dragged across the board - the only time it
        ever tilts is easing toward the pile look while hovering over
        the tray (see Puzzle.update). A piece tilted right at the
        window's edge could in principle clip a pixel or two at its
        rotated corner; far smaller a problem than the puzzle being
        impossible to finish.
        """
        scale = self.scale
        min_x = min(bounds.left + self.extent_left * scale, bounds.centerx)
        max_x = max(bounds.right - self.extent_right * scale, bounds.centerx)
        min_y = min(bounds.top + self.extent_top * scale, bounds.centery)
        max_y = max(bounds.bottom - self.extent_bottom * scale, bounds.centery)

        cx, cy = self.center()
        cx = min(max(cx, min_x), max_x)
        cy = min(max(cy, min_y), max_y)
        self._set_center((cx, cy))

    def draw(self, surface, cast_shadow=False, offset=(0, 0)):
        ox, oy = offset

        # ---- Sitting in the pile ----
        if self.in_tray:
            if cast_shadow and self.tray_shadow is not None:
                sx, sy = self.tray_shadow_pos
                surface.blit(self.tray_shadow, (sx - ox, sy - oy))
            tx, ty = self.tray_pos
            surface.blit(self.tray_image, (tx - ox, ty - oy))
            return

        # ---- Mid pick-up animation: rotate/scale on the fly (only ever
        # one piece at a time, so this is cheap) ----
        if self.angle != 0.0 or self.scale != 1.0:
            cx, cy = self.center()
            if cast_shadow and self.shadow is not None:
                sh = pygame.transform.rotozoom(self.shadow, self.angle, self.scale)
                sh_rect = sh.get_rect(center=(round(cx + 4 * self.scale - ox), round(cy + 7 * self.scale - oy)))
                surface.blit(sh, sh_rect)
            img = pygame.transform.rotozoom(self.image, self.angle, self.scale)
            surface.blit(img, img.get_rect(center=(round(cx - ox), round(cy - oy))))
            return

        # Round to whole pixels - blitting at fractional coordinates makes
        # neighbouring "solved" pieces land on slightly different pixel
        # rows/columns, which shows up as a faint seam between them.
        x, y = round(self.position.x) - ox, round(self.position.y) - oy

        if cast_shadow and self.shadow is not None:
            surface.blit(self.shadow, (x - self.shadow_pad + 4, y - self.shadow_pad + 7))

        surface.blit(self.image, (x, y))


class Puzzle:
    # Corner radius of the rounded board card (see draw_board)
    BOARD_RADIUS = 22

    # How close a released piece has to land to where its correct
    # neighbour actually sits for the two to join - see _try_join. A
    # little looser than snap_tolerance above: lining a piece up against
    # a whole board is easier (the board doesn't move) than against
    # another loose piece the player just placed by eye.
    JOIN_TOLERANCE = 32

    def __init__(self, image, columns, rows, board_rect, piece_area, tray_style="pile", progress=None, bounds=None):
        self.image = image
        self.columns = columns
        self.rows = rows
        self.board_rect = board_rect
        self.piece_area = piece_area
        self.pieces = []

        # The "physical" edges of the play area - a piece being dragged
        # can never be pushed past this rect (see Piece.clamp_to). Falls
        # back to a generous box around the board/tray themselves if the
        # caller doesn't pass one, so this never breaks old code that
        # constructs a Puzzle without it.
        if bounds is not None:
            self.bounds = bounds
        else:
            self.bounds = board_rect.unionall([piece_area]).inflate(400, 400)

        # "pile" (the default) dumps every piece into one scattered heap;
        # "wheel" arranges them evenly around a spinning dial instead -
        # see _layout_wheel / rotate_wheel_by. "carousel" lines them up
        # in a single upright row, scrollable sideways - see
        # _layout_carousel / scroll_carousel_by. Everything else
        # (dragging, snapping, the tray_image/tray_center/tray_angle a
        # piece is drawn with while at rest) is shared between all three.
        self.tray_style = tray_style

        # Optional: called with 0.0 .. 1.0 while the pieces are being cut
        # out (main.py uses it for the loading bar on big puzzles).
        self.progress = progress

        self.wheel_rotation = 0.0
        self.carousel_scroll = 0.0
        self._nominal_piece_w = 0
        self._tray_scale = 1.0

        # Two cached board backdrops, built once: a faint, mostly-
        # transparent one shown by default (just enough colour to feel
        # alive, not enough to solve by or to read as a smeared blur),
        # and a clearer one shown only while the hint button is held.
        # See draw_board(hint=...).
        self.blurred_backdrop = self._build_backdrop(self.image, alpha=24, blur=6)
        self.hint_backdrop = self._build_backdrop(self.image, alpha=190, blur=None)

        self.create_pieces()

    @staticmethod
    def _build_backdrop(image, alpha, blur=None):
        surface = image.copy()

        if blur:
            small = pygame.transform.smoothscale(
                surface,
                (max(1, surface.get_width() // blur), max(1, surface.get_height() // blur))
            )
            surface = pygame.transform.smoothscale(small, image.get_size())

        surface.set_alpha(alpha)
        return surface

    # ----------------------------------------------------------------
    # Piece / tab geometry
    #
    # Every tab and blank is built from the same two shapes - a narrow
    # rectangular "neck" plus a round "bulb" - so a tab (added, opaque)
    # and its matching blank (cut, transparent) are geometrically
    # identical, just mirrored across the shared edge. That's what makes
    # them interlock exactly instead of the mismatched, neck-less blobs
    # this used to produce.
    # ----------------------------------------------------------------

    @staticmethod
    def _stamp_edge_feature(mask, axis, edge, value, mid, edge_coord, tab_size, scale, bleed):
        if value == 0:
            return

        protrusion = tab_size * 0.85
        bulb_radius = tab_size * 0.42
        neck_width = tab_size * 0.68

        # `bleed` big-pixels of deliberate overlap, so the neck always
        # fuses cleanly with the bulb after downscaling AND - this is
        # the part that was missing - so a BLANK's cut reaches at
        # least as far outward as create_pieces' body_rect bleed goes.
        # The two used to be separate, unrelated numbers (this was a
        # fixed 3, body_rect's bleed was 6); whenever the cut fell
        # short of the bleed it was supposed to remove, a thin sliver
        # of "cut" edge stayed opaque - exactly the leftover pixels
        # that showed up as a seam once two pieces were snapped
        # together. Tying both to the same value makes that
        # impossible instead of just unlikely.
        overlap = bleed

        is_tab = value == 1
        fill = (255, 255, 255, 255) if is_tab else (255, 255, 255, 0)

        # A second, separate bit of deliberate overlap - this one across
        # the seam (the neck's width, and the bulb's radius) rather than
        # along it. Two adjacent pieces each rasterize their own tab/
        # blank independently (their own supersampled canvas, their own
        # downscale), so even though the geometry lines up exactly on
        # paper, the two can still disagree by a pixel right at that
        # boundary - most visibly along the bulb's curve, which is
        # exactly the "puzzle-shaped line" that was still showing up on
        # already-solved pieces. Only the TAB bleeds here, never the
        # BLANK: the tab overshoots a hair on every side so it always
        # wins that disagreement, while the blank stays at its exact
        # size as a second, redundant line of defence underneath it.
        perp_bleed = overlap if is_tab else 0

        # For a TAB the bulb sits outside the body (away from it). For a
        # BLANK the bulb sits inside the body (cut into it). Which raw
        # direction that means depends on which edge we're on.
        outward = is_tab
        going_negative = (edge in ("top", "left")) == outward
        sign = -1 if going_negative else 1

        bulb_c = edge_coord + sign * (protrusion - bulb_radius)

        if axis == "h":
            y0, y1 = sorted([edge_coord, bulb_c])
            rect = pygame.Rect(
                int((mid - neck_width / 2) * scale) - perp_bleed,
                int(y0 * scale) - overlap,
                max(1, int(neck_width * scale)) + perp_bleed * 2,
                int((y1 - y0) * scale) + overlap * 2
            )
            pygame.draw.rect(mask, fill, rect)
            pygame.draw.circle(
                mask, fill,
                (int(mid * scale), int(bulb_c * scale)),
                int(bulb_radius * scale) + perp_bleed
            )
        else:
            x0, x1 = sorted([edge_coord, bulb_c])
            rect = pygame.Rect(
                int(x0 * scale) - overlap,
                int((mid - neck_width / 2) * scale) - perp_bleed,
                int((x1 - x0) * scale) + overlap * 2,
                max(1, int(neck_width * scale)) + perp_bleed * 2
            )
            pygame.draw.rect(mask, fill, rect)
            pygame.draw.circle(
                mask, fill,
                (int(bulb_c * scale), int(mid * scale)),
                int(bulb_radius * scale) + perp_bleed
            )

    # ----------------------------------------------------------------
    # Piece shadow
    #
    # A drop shadow shaped like the piece's own silhouette (tabs and
    # blanks included) instead of a generic rounded rect, so loose
    # pieces in the tray - and whatever is currently being dragged -
    # read as small physical objects floating above the background.
    # Built once per piece at creation time and cached on it, using the
    # same downscale/upscale blur as ui.draw_blurred_shadow and the same
    # masked-blit tricks already used above for cutting tabs/blanks.
    # ----------------------------------------------------------------

    @staticmethod
    def _build_piece_shadow(piece_image, blur=6, alpha=110, color=(30, 32, 46)):
        pad = blur * 2
        w, h = piece_image.get_size()
        canvas = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        canvas.blit(piece_image, (pad, pad))

        # Recolour every opaque-ish pixel to a flat dark tone while
        # keeping the piece's own alpha (and its anti-aliased tab/blank
        # edges) intact.
        solid = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        solid.fill((*color, 255))
        canvas.blit(solid, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        # Scale the whole silhouette down to the target translucency.
        fade = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        fade.fill((255, 255, 255, alpha))
        canvas.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        small = pygame.transform.smoothscale(
            canvas,
            (max(1, canvas.get_width() // blur), max(1, canvas.get_height() // blur))
        )
        blurred = pygame.transform.smoothscale(small, canvas.get_size())

        return blurred, pad

    def create_pieces(self):
        image_w, image_h = self.image.get_size()
        bw = image_w / self.columns
        bh = image_h / self.rows

        tab_size = min(bw, bh) * 0.36
        pad = round(tab_size)  # integer margin, used everywhere below so
                                # the crop and the draw position can never
                                # drift apart by a fraction of a pixel

        v_edges = [[random.choice([-1, 1]) for _ in range(self.rows)] for _ in range(self.columns - 1)]
        h_edges = [[random.choice([-1, 1]) for _ in range(self.rows - 1)] for _ in range(self.columns)]

        padded_image = pygame.Surface(
            (image_w + 2 * pad, image_h + 2 * pad),
            pygame.SRCALPHA
        )
        padded_image.blit(self.image, (pad, pad))
        padded_bounds = padded_image.get_rect()

        # Shared integer column/row boundaries so adjacent pieces always
        # meet at EXACTLY the same source pixel. Each piece's true body
        # size is the gap between consecutive boundaries - varying by at
        # most 1px across the grid, same as any pixel-grid tiling. The
        # previous version rounded the crop position but not the draw
        # position (and used a plain int() truncation for `pad` instead
        # of a proper round()), so the two could disagree by a pixel at
        # some boundaries - that mismatch is what was showing up as a
        # thin white seam between two correctly-snapped pieces.
        col_bounds = [round(c * bw) for c in range(self.columns + 1)]
        row_bounds = [round(r * bh) for r in range(self.rows + 1)]

        # Nominal (average) piece size - used only for the tray's slot
        # spacing, which doesn't need to be pixel-exact.
        nominal_piece_w = round(bw) + 2 * pad
        nominal_piece_h = round(bh) + 2 * pad
        self._nominal_piece_w = nominal_piece_w

        # ---- Pile layout ----
        # Every piece is shown in the tray as a smaller, randomly rotated
        # copy, all dumped into one heap in the middle (like tipping a box
        # out). The scale is chosen so a piece is about two-thirds of the
        # tray's height, and never bigger than real size.
        #
        # The carousel is a thin, minimalist strip rather than a deep
        # dish, so it fills a much bigger share of its (much shorter)
        # tray height - the pieces should look like they just fit,
        # not like they're floating in a mostly-empty bar.
        fill_fraction = 0.86 if self.tray_style == "carousel" else 0.66
        tray_scale = min(1.0, (self.piece_area.height * fill_fraction) / nominal_piece_h)
        tray_max_h = self.piece_area.height - 16
        self._tray_scale = tray_scale

        scale = 4  # supersample for anti-aliased curves, then shrink

        for c in range(self.columns):
            if self.progress is not None:
                self.progress(c / self.columns)

            for r in range(self.rows):
                top_tab = -h_edges[c][r - 1] if r > 0 else 0
                bottom_tab = h_edges[c][r] if r < self.rows - 1 else 0
                left_tab = -v_edges[c - 1][r] if c > 0 else 0
                right_tab = v_edges[c][r] if c < self.columns - 1 else 0

                true_bw = col_bounds[c + 1] - col_bounds[c]
                true_bh = row_bounds[r + 1] - row_bounds[r]
                pw, ph = true_bw + 2 * pad, true_bh + 2 * pad
                big_pw, big_ph = pw * scale, ph * scale

                # Tabs and blanks are built on their OWN layers - a
                # transparent one for tabs (added), an opaque one for
                # blanks (cut) - each supersampled and downscaled in
                # isolation so their curves stay smooth. The body
                # rectangle is drawn separately, directly at final
                # resolution with a hard, non-antialiased edge, then the
                # two feature layers are composited onto it.
                #
                # The previous approach (bleeding the body outward a few
                # px to paper over the seam) could only ever get partway
                # there: antialiasing the straight edges means each piece
                # still fades out before its real border, and blending two
                # independently-faded copies of the same photo doesn't sum
                # back to full opacity - roughly a quarter of the
                # background still shows through, which is exactly the
                # thin puzzle-shaped line that kept surviving. A hard body
                # edge has no partial alpha to blend in the first place,
                # so neighbouring pieces meet at one crisp, fully-opaque
                # line; only the tab/blank curves (which actually need
                # softening) still get any blur.
                edge_bleed = 8

                tab_layer = pygame.Surface((big_pw, big_ph), pygame.SRCALPHA)
                tab_layer.fill((255, 255, 255, 0))

                blank_layer = pygame.Surface((big_pw, big_ph), pygame.SRCALPHA)
                blank_layer.fill((255, 255, 255, 255))

                mid_x = pad + true_bw / 2
                mid_y = pad + true_bh / 2

                for axis, edge, value, mid, edge_coord in (
                    ("h", "top", top_tab, mid_x, pad),
                    ("h", "bottom", bottom_tab, mid_x, pad + true_bh),
                    ("v", "left", left_tab, mid_y, pad),
                    ("v", "right", right_tab, mid_y, pad + true_bw)
                ):
                    target = tab_layer if value == 1 else blank_layer
                    self._stamp_edge_feature(target, axis, edge, value, mid, edge_coord, tab_size, scale, edge_bleed)

                tab_layer = pygame.transform.smoothscale(tab_layer, (pw, ph))
                blank_layer = pygame.transform.smoothscale(blank_layer, (pw, ph))

                mask = pygame.Surface((pw, ph), pygame.SRCALPHA)
                mask.fill((255, 255, 255, 0))
                pygame.draw.rect(mask, (255, 255, 255, 255), (pad, pad, true_bw, true_bh))

                # Union in the (smooth) tabs, then cut out the (smooth) blanks.
                mask.blit(tab_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)
                mask.blit(blank_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

                piece_rect = pygame.Rect(col_bounds[c], row_bounds[r], pw, ph)

                # Clip against the padded canvas before taking a subsurface -
                # the outer rows/columns' rects extend into the padding, and
                # occasionally by 1px more than the canvas actually has.
                clipped_rect = piece_rect.clip(padded_bounds)

                piece_img = pygame.Surface((pw, ph), pygame.SRCALPHA)
                if clipped_rect.width > 0 and clipped_rect.height > 0:
                    offset = (
                        clipped_rect.left - piece_rect.left,
                        clipped_rect.top - piece_rect.top
                    )
                    piece_img.blit(padded_image.subsurface(clipped_rect), offset)

                piece_img.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

                correct_x = self.board_rect.left + col_bounds[c] - pad
                correct_y = self.board_rect.top + row_bounds[r] - pad

                shadow = self._build_piece_shadow(piece_img)

                # Pile: random rotation, but only angles whose rotated
                # bounding box still fits inside the tray. Wheel and
                # carousel: upright, just scaled down - any "spin" comes
                # from position (angle around the dial / offset along the
                # row), not from tumbling like the pile does.
                if self.tray_style in ("wheel", "carousel"):
                    angle = 0.0
                    tray_img = pygame.transform.rotozoom(piece_img, 0.0, tray_scale)
                else:
                    angle, tray_img = self._make_pile_variant(piece_img, tray_scale, tray_max_h)
                tray_shadow = self._build_piece_shadow(tray_img, blur=4, alpha=120)

                piece = Piece(piece_img, (correct_x, correct_y), (0, 0), c, r, shadow=shadow)
                piece.tray_image = tray_img
                piece.tray_shadow = tray_shadow[0]
                piece.tray_shadow_pad = tray_shadow[1]
                piece.tray_angle = angle
                piece.tray_scale = tray_scale
                piece.wheel_base_angle = 0.0  # assigned for real in _assign_wheel_angles
                self.pieces.append(piece)

        if self.tray_style == "wheel":
            self._assign_wheel_angles()
            self._layout_wheel()
        elif self.tray_style == "carousel":
            self._layout_carousel()
        else:
            self._scatter_pile()

        # The list order is the stacking order of the pile - shuffle it so
        # which piece ends up on top is random, not column by column.
        random.shuffle(self.pieces)

        # (col, row) -> its one piece, for _try_join's neighbour lookups.
        self.grid = {(piece.col, piece.row): piece for piece in self.pieces}

    # ----------------------------------------------------------------
    # The heap
    # ----------------------------------------------------------------

    @staticmethod
    def _make_pile_variant(piece_img, scale, max_h):
        for _ in range(14):
            angle = random.uniform(-180, 180)
            img = pygame.transform.rotozoom(piece_img, angle, scale)
            if img.get_height() <= max_h:
                return angle, img

        # Very wide pieces (the low-piece-count levels) can't spin freely
        # inside a shallow tray - keep them near flat, either way up.
        angle = random.choice([0, 180]) + random.uniform(-8, 8)
        return angle, pygame.transform.rotozoom(piece_img, angle, scale)

    def _scatter_pile(self, pieces=None):
        """Drop every piece into one heap in the middle of the tray.

        - x follows a triangular distribution, so the heap is densest in
          the middle and thins out toward the edges (like a real pile);
        - the heap widens with the piece count, so 12 pieces make a small
          heap and 384 fill most of the tray;
        - each piece tries a few random spots and takes the one furthest
          from its neighbours, so pieces overlap a lot but almost none
          gets buried completely under another.
        """
        area = self.piece_area
        margin = 10
        pieces = self.pieces if pieces is None else pieces
        if not pieces:
            return

        usable_h = max(1, area.height - 2 * margin)
        total_area = sum(p.tray_image.get_width() * p.tray_image.get_height() for p in pieces)
        max_w = max(p.tray_image.get_width() for p in pieces)

        # Keep the heap clear of the round tray corners and of the hint
        # button that floats over the tray's top-right.
        max_half_width = area.width / 2 - 90 - max_w / 2
        wanted_half_width = total_area / (2 * usable_h * 1.6)
        half_width = max(140, min(wanted_half_width, max_half_width))

        placed = []
        for p in pieces:
            w, h = p.tray_image.get_size()
            y_range = max(0, usable_h / 2 - h / 2)

            best = None
            best_score = -1
            for _ in range(4):
                x = area.centerx + (random.random() + random.random() - 1) * half_width
                y = area.centery + (random.random() + random.random() - 1) * y_range
                score = min(((x - px) ** 2 + (y - py) ** 2 for px, py in placed), default=1e9)
                if score > best_score:
                    best, best_score = (x, y), score

            x, y = best
            placed.append((x, y))

            p.tray_center = pygame.Vector2(x, y)
            p.tray_pos = (round(x - w / 2), round(y - h / 2))
            pad = p.tray_shadow_pad
            p.tray_shadow_pos = (p.tray_pos[0] - pad + 2, p.tray_pos[1] - pad + 4)
            p._set_center(p.tray_center)

    def shuffle_tray(self):
        """The Shuffle power-up: re-mixes only the loose pieces still in
        the tray (placed pieces and anything being dragged are left
        alone). Returns False if there was nothing to shuffle."""
        loose = [p for p in self.pieces if p.in_tray and not p.is_snapped]
        if len(loose) < 2:
            return False

        slots = [i for i, p in enumerate(self.pieces) if p.in_tray and not p.is_snapped]
        mixed = loose[:]
        random.shuffle(mixed)
        for slot, piece in zip(slots, mixed):
            self.pieces[slot] = piece

        if self.tray_style == "wheel":
            angles = [p.wheel_base_angle for p in loose]
            random.shuffle(angles)
            for piece, angle in zip(loose, angles):
                piece.wheel_base_angle = angle
            self._layout_wheel()
        elif self.tray_style == "carousel":
            self.carousel_scroll = 0.0
            self._layout_carousel()
        else:
            self._scatter_pile(mixed)

        return True

    # ----------------------------------------------------------------
    # The wheel
    #
    # A circular alternative to the pile: pieces sit upright, evenly
    # spaced around a dial, and spinning it (mouse wheel, in main.py)
    # brings different ones to hand. Unlike the pile it's a proper
    # circle rather than something that fills the whole tray width -
    # it only widens into an ellipse once there are more pieces than
    # comfortably fit around a circle that size.
    # ----------------------------------------------------------------

    def _wheel_geometry(self):
        area = self.piece_area
        count = max(1, len(self.pieces))

        base_radius = max(40, area.height / 2 - 20)
        max_radius_x = max(base_radius, area.width / 2 - 90)

        spacing = self._nominal_piece_w * 0.6 + 14
        wanted_radius_x = (count * spacing) / (2 * math.pi)

        radius_x = max(base_radius, min(wanted_radius_x, max_radius_x))
        radius_y = base_radius
        return pygame.Vector2(area.centerx, area.centery), radius_x, radius_y

    def _assign_wheel_angles(self):
        count = len(self.pieces)
        for i, p in enumerate(self.pieces):
            p.wheel_base_angle = 2 * math.pi * i / count if count else 0.0

    def _place_wheel_piece(self, piece):
        center, radius_x, radius_y = self._wheel_geometry()
        angle = piece.wheel_base_angle + self.wheel_rotation
        x = center.x + radius_x * math.cos(angle)
        y = center.y + radius_y * math.sin(angle)

        w, h = piece.tray_image.get_size()
        piece.tray_center = pygame.Vector2(x, y)
        piece.tray_pos = (round(x - w / 2), round(y - h / 2))
        pad = piece.tray_shadow_pad
        piece.tray_shadow_pos = (piece.tray_pos[0] - pad + 2, piece.tray_pos[1] - pad + 4)
        piece._set_center(piece.tray_center)

    def _layout_wheel(self):
        for p in self.pieces:
            if p.in_tray:
                self._place_wheel_piece(p)

    def rotate_wheel_by(self, delta_radians):
        self.wheel_rotation = (self.wheel_rotation + delta_radians) % (2 * math.pi)
        self._layout_wheel()

    def _return_to_wheel(self, piece):
        piece.angle = 0.0
        piece.scale = piece.tray_scale
        piece.is_snapped = False
        piece.in_tray = True
        self._place_wheel_piece(piece)
        self.bring_to_front(piece)

    # ----------------------------------------------------------------
    # The carousel
    #
    # A third alternative to the pile and the wheel: every remaining
    # piece upright, in a single tightly-packed row with no overlap,
    # scrolled sideways with the mouse wheel or by dragging the empty
    # tray space (both in main.py) whenever there isn't room to show
    # them all at once. Positions are recomputed every frame (see
    # update() below) from `carousel_scroll` and the current in-tray
    # order, so the row always stays contiguous - closing the gap
    # immediately as pieces are picked up, solved, or dropped back in,
    # rather than leaving a hole where one used to sit.
    # ----------------------------------------------------------------

    def _carousel_spacing(self):
        return self._nominal_piece_w * self._tray_scale + 22

    def _carousel_order(self):
        return [p for p in self.pieces if p.in_tray and not p.is_snapped]

    def _carousel_view_rect(self):
        import ui

        return ui.get_carousel_piece_view_rect(self.piece_area)

    def _carousel_max_scroll(self):
        order = self._carousel_order()
        content_w = len(order) * self._carousel_spacing()
        return max(0.0, content_w - self._carousel_view_rect().width)

    def scroll_carousel_by(self, delta_px):
        self.carousel_scroll = max(0.0, min(self.carousel_scroll + delta_px, self._carousel_max_scroll()))

    def _layout_carousel(self):
        order = self._carousel_order()
        if not order:
            return

        # Re-clamp here too: pieces leaving the tray (solved, or picked
        # up) shortens the row, which can leave a stale scroll position
        # past the new (shorter) end.
        self.carousel_scroll = max(0.0, min(self.carousel_scroll, self._carousel_max_scroll()))

        area = self.piece_area
        view = self._carousel_view_rect()
        spacing = self._carousel_spacing()
        start_x = view.left + spacing / 2 - self.carousel_scroll

        for i, p in enumerate(order):
            x = start_x + i * spacing
            y = area.centery
            w, h = p.tray_image.get_size()
            p.tray_center = pygame.Vector2(x, y)
            p.tray_pos = (round(x - w / 2), round(y - h / 2))
            pad = p.tray_shadow_pad
            p.tray_shadow_pos = (p.tray_pos[0] - pad + 2, p.tray_pos[1] - pad + 4)
            p._set_center(p.tray_center)

    def _return_to_carousel(self, piece):
        piece.angle = 0.0
        piece.scale = piece.tray_scale
        piece.is_snapped = False
        piece.in_tray = True
        self.bring_to_front(piece)
        self._layout_carousel()


    # ----------------------------------------------------------------
    # Per-frame update (pick-up animation)
    # ----------------------------------------------------------------

    def update(self, dt, mouse_pos):
        if self.tray_style == "carousel":
            self._layout_carousel()

        over_tray = self.piece_area.collidepoint(mouse_pos)
        for p in self.pieces:
            if p.is_snapped or p.in_tray:
                continue

            grouped = len(p.group) > 1
            # A joined cluster never actually goes back to the tray (see
            # release_piece), so it never needs the "easing toward the
            # pile look" preview either.
            p.update(dt, mouse_pos, to_tray=over_tray and p.dragging and not grouped)

            if p.dragging:
                if grouped:
                    self._clamp_group(p.group)
                else:
                    p.clamp_to(self.bounds)

    def _clamp_group(self, group):
        """Keeps a whole joined cluster inside self.bounds as one rigid
        unit, instead of clamping each piece separately - clamping them
        one at a time would let the boundary hold back only the member
        nearest the edge and pull the cluster apart.

        Works out the single (dx, dy) nudge the worst-placed member
        needs, per axis, and applies that same nudge to every member -
        so nothing moves at all unless some member actually needs it.
        """
        dx = dy = 0.0

        for member in group:
            cx, cy = member.center()
            scale = member.scale
            min_x = min(self.bounds.left + member.extent_left * scale, self.bounds.centerx)
            max_x = max(self.bounds.right - member.extent_right * scale, self.bounds.centerx)
            min_y = min(self.bounds.top + member.extent_top * scale, self.bounds.centery)
            max_y = max(self.bounds.bottom - member.extent_bottom * scale, self.bounds.centery)

            if cx < min_x:
                dx = max(dx, min_x - cx)
            elif cx > max_x:
                dx = min(dx, max_x - cx)

            if cy < min_y:
                dy = max(dy, min_y - cy)
            elif cy > max_y:
                dy = min(dy, max_y - cy)

        if dx or dy:
            for member in group:
                member._set_center(member.center() + (dx, dy))

    def release_piece(self, piece, mouse_pos):
        """Called when the player lets go of a piece. Over the tray, it
        goes back to wherever it belongs for the current tray style - the
        pile (small and tilted, on top of the heap) or its own slot on
        the wheel; anywhere else it lands upright and is checked against
        the board and against its neighbours.

        A piece that's joined to others (len(piece.group) > 1) never
        goes back to the tray, even if it's dropped right over it -
        breaking up an assembled cluster because it clipped the tray on
        its way to the board would be far more annoying than useful.
        """
        if len(piece.group) == 1 and self.piece_area.collidepoint(mouse_pos):
            if self.tray_style == "wheel":
                self._return_to_wheel(piece)
            elif self.tray_style == "carousel":
                self._return_to_carousel(piece)
            else:
                self._return_to_pile(piece, mouse_pos)
            return

        piece.end_drag(mouse_pos)

        if len(piece.group) > 1:
            self._clamp_group(piece.group)
        else:
            piece.clamp_to(self.bounds)

        piece.check_snap()

        if piece.is_snapped:
            self._snap_group(piece)
        else:
            self._try_join(piece)

    def _snap_group(self, piece):
        """Once one member of a joined cluster is confirmed to be sitting
        exactly on its correct board slot, every other member is too -
        they were carried into place together, rigidly - so lock the
        whole cluster in at once instead of making the player nudge each
        piece the last few pixels individually. Also settles each
        member's position to exactly its own correct_position, clearing
        any tiny drift a chain of earlier joins may have added up."""
        for member in piece.group:
            member.position = pygame.Vector2(member.correct_position)
            member.is_snapped = True

    def _try_join(self, piece):
        """Checks the (up to) 4 real grid-neighbours of a just-released
        piece: for each one close enough, in exactly the spot correctly
        joining onto it would put `piece`, snaps the two precisely into
        that alignment and merges their groups, so the pair (and
        whatever each was already joined to) now drags as one unit. If a
        neighbour joined this way already sits on the board, `piece`'s
        whole (former) group is now exactly on the board too, by the
        same construction - see _snap_group.
        """
        for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            neighbor = self.grid.get((piece.col + dc, piece.row + dr))
            if neighbor is None or neighbor.in_tray or neighbor.group is piece.group:
                continue

            expected = neighbor.position + (piece.correct_position - neighbor.correct_position)
            if piece.position.distance_to(expected) >= self.JOIN_TOLERANCE:
                continue

            correction = expected - piece.position
            group = piece.group
            for member in group:
                member.position += correction

            merged = group + neighbor.group
            for member in merged:
                member.group = merged

            if neighbor.is_snapped:
                self._snap_group(piece)

    def _return_to_pile(self, piece, mouse_pos):
        # Settle in the pile look, wherever the cursor put it...
        piece.angle = piece.tray_angle
        piece.scale = piece.tray_scale
        piece.drag_to(mouse_pos)
        piece.dragging = False

        # ...then keep it fully inside the tray's inner well.
        area = self.piece_area
        margin = 14
        w, h = piece.tray_image.get_size()
        cx, cy = piece.center()
        cx = min(max(cx, area.left + margin + w / 2), area.right - margin - w / 2)
        cy = min(max(cy, area.top + margin + h / 2), area.bottom - margin - h / 2)

        piece.tray_center = pygame.Vector2(cx, cy)
        piece.tray_pos = (round(cx - w / 2), round(cy - h / 2))
        pad = piece.tray_shadow_pad
        piece.tray_shadow_pos = (piece.tray_pos[0] - pad + 2, piece.tray_pos[1] - pad + 4)
        piece._set_center(piece.tray_center)

        piece.angle = 0.0
        piece.scale = 1.0
        piece.is_snapped = False
        piece.in_tray = True

        # Last in the list = drawn on top of the pile and picked first.
        self.bring_to_front(piece)

    # ----------------------------------------------------------------
    # Draw
    #
    # Split into three passes so main.py can sandwich its own tray-card
    # background between the board and the pieces sitting on top of it:
    # draw_board() -> (tray card drawn by main.py) -> draw_tray() ->
    # draw_active(). `draw()` below just runs all three back-to-back,
    # for anywhere the split doesn't matter.
    # ----------------------------------------------------------------

    def _draw_grid(self, card):
        """A faint line along every piece boundary, drawn onto the
        board card behind the pieces - covered up wherever a piece is
        already snapped, so it only ever hints at what's still unsolved.
        """
        if self.columns <= 1 and self.rows <= 1:
            return

        import ui

        color = (*ui.BOARD_BORDER, 72 if not ui.IS_DARK else 150)
        w, h = card.get_size()

        for c in range(1, self.columns):
            x = round(c * w / self.columns)
            pygame.draw.line(card, color, (x, 0), (x, h), 1)

        for r in range(1, self.rows):
            y = round(r * h / self.rows)
            pygame.draw.line(card, color, (0, y), (w, y), 1)

    def draw_board(self, surface, hint=False):
        """The rounded photo card: a hint of the full image (heavily
        blurred by default, sharper while `hint` is held), the
        piece-boundary grid, and every already-placed piece - clipped
        to the board's rounded corners so solved pieces along the edge
        don't poke past them with square corners of their own.
        """
        # Imported here rather than at the top of the file: ui.py may
        # import Puzzle from this module (for type hints, isinstance
        # checks, etc.), and importing it up front would create a
        # circular import that fails before either module finishes
        # loading. By the time this method actually runs, both modules
        # are already fully loaded, so this is free after the first call.
        import ui

        rect = self.board_rect
        card = pygame.Surface(rect.size, pygame.SRCALPHA)
        board_color = tuple(max(0, channel - 8) for channel in ui.CARD_BACKGROUND) if ui.IS_DARK else ui.CARD_BACKGROUND
        card.fill((*board_color, 255))

        backdrop = self.hint_backdrop if hint else self.blurred_backdrop
        card.blit(backdrop, (0, 0))

        self._draw_grid(card)

        origin = rect.topleft
        for p in self.pieces:
            if p.is_snapped:
                local = (round(p.position.x - origin[0]), round(p.position.y - origin[1]))
                card.blit(p.image, local)

        mask = ui.get_rounded_mask(rect.size, self.BOARD_RADIUS)
        card.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        ui.draw_blurred_shadow(
            surface, rect, border_radius=self.BOARD_RADIUS, blur=16, alpha=26,
            color=ui.CARD_SHADOW, offset=(0, 8)
        )
        surface.blit(card, rect.topleft)
        ui.draw_smooth_rect(
            surface, rect, (*ui.CARD_BORDER, 230),
            radius=self.BOARD_RADIUS, width=1
        )

    def draw_tray(self, surface):
        """The loose pieces still in the tray, in stacking order (later
        in the list = on top), each casting a soft shadow onto whatever
        is underneath it.

        The carousel additionally clips to the tray's own rounded shape -
        unlike the pile or wheel, it deliberately lays pieces out wider
        than the visible strip and relies on that clip to hide whatever's
        currently scrolled out of view. It's drawn on a separate layer
        and masked to the exact same rounded rect as the card underneath
        it (see ui.draw_tray_card / ui.PUZZLE_TRAY_RADIUS), rather than a
        plain rectangular clip, so a piece scrolling past either end is
        cropped clean by the tray's curve instead of poking past it at
        the corners.
        """
        if self.tray_style == "carousel":
            import ui

            area = self.piece_area
            layer = pygame.Surface(area.size, pygame.SRCALPHA)
            for p in self.pieces:
                if not p.is_snapped and p.in_tray:
                    p.draw(layer, cast_shadow=True, offset=area.topleft)

            mask = ui.get_rounded_mask(area.size, ui.PUZZLE_TRAY_RADIUS).copy()
            view = self._carousel_view_rect()
            view_left = view.left - area.left
            view_right = view.right - area.left
            pygame.draw.rect(mask, (255, 255, 255, 0), (0, 0, view_left, area.height))
            pygame.draw.rect(
                mask, (255, 255, 255, 0),
                (view_right, 0, area.width - view_right, area.height)
            )
            layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(layer, area.topleft)
            return

        for p in self.pieces:
            if not p.is_snapped and p.in_tray:
                p.draw(surface, cast_shadow=True)

    def draw_active(self, surface):
        """Whatever's currently being dragged (or was dropped without
        snapping) - drawn last, unclipped, on top of everything else so
        it can freely cross the board/tray boundary.
        """
        for p in self.pieces:
            if not p.is_snapped and not p.in_tray:
                p.draw(surface, cast_shadow=True)

    def draw(self, surface, hint=False):
        self.draw_board(surface, hint=hint)
        self.draw_tray(surface)
        self.draw_active(surface)

    def piece_at(self, pos):
        for piece in reversed([p for p in self.pieces if not p.is_snapped]):
            if piece.in_tray:
                image = piece.tray_image
                origin_x, origin_y = piece.tray_pos
            else:
                image = piece.image
                origin_x, origin_y = piece.position

            local_x = int(pos[0] - origin_x)
            local_y = int(pos[1] - origin_y)
            if 0 <= local_x < image.get_width() and 0 <= local_y < image.get_height():
                if image.get_at((local_x, local_y)).a > 128:
                    return piece
        return None

    def bring_to_front(self, piece):
        for member in piece.group:
            if member in self.pieces:
                self.pieces.remove(member)
                self.pieces.append(member)

    def is_complete(self):
        return all(p.is_snapped for p in self.pieces)

    def completed_count(self):
        return sum(1 for p in self.pieces if p.is_snapped)