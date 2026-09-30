import pygame
import math
import random

# --------------------------------------------------
# Puzzlescape UI (default theme)
# --------------------------------------------------

# ----- Background gradient (Mint -> Cyan) -----
BACKGROUND_TOP = (246, 249, 250)
BACKGROUND_BOTTOM = (255, 255, 255)

# ----- Text -----
TEXT = (38, 36, 40)
MUTED_TEXT = (118, 114, 122)

# ----- Sidebar -----
# The sidebar is a fixed icon dock - always visible, docked to either
# edge (settings["sidebar_position"]). SIDEBAR_BACKGROUND/BORDER are its
# glass tint; see the "Icon dock" section further down for the rest.

SIDEBAR_BACKGROUND = (255, 255, 255, 145)
SIDEBAR_BORDER = (255, 255, 255, 90)

NAV_ACTIVE_BACKGROUND = (255, 255, 255)
NAV_ACTIVE_SHADOW = (214, 205, 214)

# ----- Cards -----
BOARD_BACKGROUND = (255, 255, 252)
BOARD_BORDER = (225, 223, 216)

PIECE_AREA_BACKGROUND = (255, 255, 255, 255)
PIECE_AREA_BORDER = (255, 255, 255, 255)

WHITE = (255, 255, 255)
CARD_SHADOW = (150, 165, 195)

# ----- Content panel (the level-select window) -----
# A soft blue wash instead of flat white, so the panel reads as part of
# the same cool palette as the sidebar/background instead of a blank sheet.
CONTENT_TOP = (255, 255, 255)
CONTENT_BOTTOM = (246, 249, 250)

CARD_BACKGROUND = (247, 250, 253)
CARD_BORDER = (223, 232, 243)

TRACK_BACKGROUND = (246, 249, 250)

# A dedicated blue accent, pulled from the cyan end of the brand gradient,
# used for the logo and small highlight details.
ACCENT_BLUE = (94, 142, 214)

# ----- Accent gradients (Mint/Cyan) -----
YELLOW = (247, 207, 96)
PINK = (242, 154, 178)
BLUE = (139, 190, 230)
GREEN = (153, 205, 170)

GRADIENT_PRIMARY = ((178, 235, 222), (163, 209, 240))       # CTA buttons
NAV_GRADIENT = ((178, 235, 222), (163, 209, 240))           # Active Nav
GRADIENT_EASY = ((176, 224, 190), (128, 189, 156))
GRADIENT_MEDIUM = ((252, 221, 145), (245, 186, 94))
GRADIENT_HARD = ((248, 178, 194), (232, 128, 155))
GRADIENT_EXTREME = ((160, 200, 236), (121, 156, 219))


# --------------------------------------------------
# Screen
# --------------------------------------------------

WIDTH = 1600   # kept in sync with main.py's canvas - see its comment for why
HEIGHT = 900


# --------------------------------------------------
# Gradient helpers
# --------------------------------------------------

_gradient_cache = {}


def _lerp_color(
    color_a,
    color_b,
    t
):
    return tuple(
        int(
            color_a[channel]
            + (color_b[channel] - color_a[channel]) * t
        )
        for channel in range(3)
    )


def _build_diagonal_gradient(
    width,
    height,
    color_a,
    color_b,
    small_size=48
):
    small_size = max(
        2,
        small_size
    )

    small = pygame.Surface(
        (small_size, small_size)
    )

    max_sum = (small_size - 1) * 2

    for y in range(small_size):
        for x in range(small_size):
            t = (x + y) / max_sum
            small.set_at(
                (x, y),
                _lerp_color(
                    color_a,
                    color_b,
                    t
                )
            )

    return pygame.transform.smoothscale(
        small,
        (
            max(1, width),
            max(1, height)
        )
    )


_rounded_surface_cache = {}


def _rounded_rect_surface(
    size,
    color,
    radius,
    corners=(True, True, True, True),
    width=0
):
    """A filled or outlined rounded-rect surface, drawn at 4x scale and
    shrunk with smoothscale. pygame's own border_radius rects aren't
    anti-aliased, so up close (thumbnails, buttons, cards) their corners
    show visible jagged pixels; supersampling like this is what fixes it.
    corners = (top_left, top_right, bottom_right, bottom_left)
    """
    key = (size, color, radius, corners, width)
    surface = _rounded_surface_cache.get(key)

    if surface is None:
        scale = 4
        big_size = (max(1, size[0] * scale), max(1, size[1] * scale))
        big = pygame.Surface(big_size, pygame.SRCALPHA)

        # Prime the "empty" background to the shape's own colour at zero
        # alpha (instead of pygame's default transparent black). Otherwise
        # smoothscale blends opaque colour against black-at-alpha-0 at
        # every edge, dragging the RGB toward black as it fades out - a
        # dark fringe/halo on every rounded corner and border.
        big.fill((*color[:3], 0))

        top_left, top_right, bottom_right, bottom_left = corners

        pygame.draw.rect(
            big,
            color,
            big.get_rect(),
            width=width * scale,
            border_top_left_radius=radius * scale if top_left else 0,
            border_top_right_radius=radius * scale if top_right else 0,
            border_bottom_right_radius=radius * scale if bottom_right else 0,
            border_bottom_left_radius=radius * scale if bottom_left else 0,
        )

        surface = pygame.transform.smoothscale(big, size)
        _rounded_surface_cache[key] = surface

    return surface


def draw_smooth_rect(
    screen,
    rect,
    color,
    radius=24,
    corners=(True, True, True, True),
    width=0
):
    surface = _rounded_rect_surface(rect.size, color, radius, corners, width)
    screen.blit(surface, rect.topleft)


def draw_page_back_button(screen, rect, font):
    """The shared bottom-of-page Back control, themed like a sidebar tile."""
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    draw_blurred_shadow(
        screen, rect, border_radius=16, blur=8, alpha=30,
        color=CARD_SHADOW, offset=(0, 4)
    )
    fill = TRACK_BACKGROUND if hovered else WHITE
    draw_smooth_rect(screen, rect, (*fill, 255), radius=16)
    draw_smooth_rect(screen, rect, (*CARD_BORDER, 255), radius=16, width=1)
    draw_text(screen, "BACK", font, TEXT, rect.centerx, rect.centery)


def get_rounded_mask(size, radius):
    """A filled white rounded-rect alpha mask, ready for BLEND_RGBA_MULT
    (see draw_image_top_rounded / Puzzle.draw_board) - multiplying any
    image by this punches its corners round with the same supersampled
    anti-aliasing as every other rounded shape in this file.
    """
    return _rounded_rect_surface(size, (255, 255, 255, 255), radius)


_content_gradient_cache = {}


def draw_content_panel(
    screen,
    rect
):
    """Fills the main content area (the level-select 'window') with a soft
    white-to-blue wash instead of flat white, so it picks up the app's
    cool accent colour instead of sitting there as a blank sheet.

    When a background wallpaper is active, this is skipped in favour of a
    much lighter tint over the photo (already visible here, painted by
    draw_background) - just enough to keep cards and text readable
    without hiding the picture the player chose.
    """
    if _active_wallpaper_surface is not None:
        tint = pygame.Surface(rect.size, pygame.SRCALPHA)
        tint.fill((16, 18, 26, 70) if IS_DARK else (255, 255, 255, 60))
        screen.blit(tint, rect.topleft)
        return

    key = (rect.size, CONTENT_TOP, CONTENT_BOTTOM)
    gradient = _content_gradient_cache.get(key)

    if gradient is None:
        gradient = _build_diagonal_gradient(
            rect.width,
            rect.height,
            CONTENT_TOP,
            CONTENT_BOTTOM,
            small_size=64
        )
        _content_gradient_cache[key] = gradient

    screen.blit(gradient, rect.topleft)


def get_background_gradient():
    key = (
        "background",
        WIDTH,
        HEIGHT,
        BACKGROUND_TOP,
        BACKGROUND_BOTTOM
    )

    gradient = _gradient_cache.get(
        key
    )

    if gradient is None:
        gradient = _build_diagonal_gradient(
            WIDTH,
            HEIGHT,
            BACKGROUND_TOP,
            BACKGROUND_BOTTOM,
            small_size=64
        )
        _gradient_cache[key] = gradient

    return gradient


def draw_background(
    screen
):
    if _active_wallpaper_surface is not None:
        screen.blit(_active_wallpaper_surface, (0, 0))
        return

    screen.blit(
        get_background_gradient(),
        (0, 0)
    )


# --------------------------------------------------
# Background wallpaper
# --------------------------------------------------
# A player can pick one of their unlocked puzzle photos (from the
# Gallery) to use as the backdrop on menu-style pages, in place of the
# plain theme gradient above. main.py calls set_active_wallpaper() once
# a frame with either that photo's file path, or None on screens that
# should keep the plain look - draw_background() and draw_content_panel()
# just check this module's own state, so nothing calling either of them
# needs to change.

_wallpaper_cache = {}
_active_wallpaper_key = None
_active_wallpaper_surface = None


def set_active_wallpaper(image_path):
    """Call once per frame with the chosen photo's path, or None. Building
    the cropped-and-tinted surface is real work (load a full-size photo,
    rescale it), so it only happens once per unique picture - the result
    is cached and reused every other frame.

    The cache is keyed by (path, light/dark mode), not the path alone: the
    scrim baked into the surface is different in each mode, so switching
    Dark Mode in Settings has to pick up (or build) the matching one
    instead of keeping a light wash under light-coloured text."""
    global _active_wallpaper_key, _active_wallpaper_surface

    key = (image_path, IS_DARK) if image_path else None

    if key == _active_wallpaper_key:
        return

    _active_wallpaper_key = key

    if key is None:
        _active_wallpaper_surface = None
        return

    if key not in _wallpaper_cache:
        _wallpaper_cache[key] = _build_wallpaper_surface(image_path)

    _active_wallpaper_surface = _wallpaper_cache[key]


def _build_wallpaper_surface(image_path):
    """Loads a puzzle's photo, scales and crops it to fill the whole
    canvas exactly (like CSS "cover": scaled up until one axis overflows,
    the overflow cropped away - never letterboxed), and bakes in a soft
    scrim so text and cards on top stay readable. Returns None (so a
    missing or corrupt file quietly falls back to the plain gradient) if
    the photo can't be loaded."""
    try:
        raw = pygame.image.load(image_path).convert()
    except (pygame.error, FileNotFoundError):
        return None

    scale = max(WIDTH / raw.get_width(), HEIGHT / raw.get_height())
    scaled = pygame.transform.smoothscale(
        raw,
        (max(WIDTH, round(raw.get_width() * scale)), max(HEIGHT, round(raw.get_height() * scale)))
    )

    crop = pygame.Rect(0, 0, WIDTH, HEIGHT)
    crop.center = scaled.get_rect().center
    cropped = scaled.subsurface(crop).copy()

    scrim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    scrim.fill((10, 12, 18, 145) if IS_DARK else (255, 255, 255, 110))
    cropped.blit(scrim, (0, 0))

    return cropped


def has_active_wallpaper():
    return _active_wallpaper_surface is not None


# --------------------------------------------------
# Floating puzzle pieces (title / welcome screen backdrop)
# --------------------------------------------------
# A handful of soft, translucent puzzle-piece silhouettes drifting and
# slowly turning behind the title and welcome screens - rotation plus a
# gentle vertical bob is what gives a flat 2D scene that "2.5D" sense of
# depth, adapted from a reference sketch. Purely decorative - never hit-
# tested, and always drawn first so the real UI sits on top of it.

_floating_pieces = None
_floating_pieces_tick = None


def _build_floating_piece_shape(size, color, scale=3):
    """A small rounded-square puzzle-piece silhouette - one tab bump,
    one blank notch - filled with a single translucent colour. It isn't
    meant to interlock with anything; it just needs to read as "a puzzle
    piece" at a glance, the same masked-hole trick used for icons
    elsewhere in this file."""
    tab = size * 0.3
    canvas = size + int(tab * 2)
    big = pygame.Surface((canvas * scale, canvas * scale), pygame.SRCALPHA)

    body = pygame.Rect(
        int(tab * scale), int(tab * scale),
        int(size * scale), int(size * scale)
    )
    pygame.draw.rect(big, color, body, border_radius=int(size * scale * 0.14))

    bump_r = int(tab * 0.55 * scale)
    pygame.draw.circle(big, color, (body.right, body.centery), bump_r)

    hole = pygame.Surface(big.get_size(), pygame.SRCALPHA)
    hole.fill((255, 255, 255, 255))
    pygame.draw.circle(hole, (255, 255, 255, 0), (body.centerx, body.bottom), bump_r)
    big.blit(hole, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    return pygame.transform.smoothscale(big, (canvas, canvas))


def _build_floating_pieces():
    rng = random.Random(7)   # a fixed, pleasant arrangement rather than
                              # a brand new scatter every launch
    palette = [GRADIENT_PRIMARY[0], GRADIENT_PRIMARY[1], ACCENT_GLOW]
    pieces = []

    for _ in range(9):
        size = rng.randint(34, 64)
        color = (*rng.choice(palette), rng.randint(35, 60))
        pieces.append({
            "base_shape": _build_floating_piece_shape(size, color),
            "x": rng.randint(40, WIDTH - 40),
            "y": rng.randint(40, HEIGHT - 40),
            "angle": rng.uniform(0, 360),
            "rot_speed": rng.uniform(3, 10) * rng.choice([-1, 1]),
            "bob_speed": rng.uniform(0.4, 0.9),
            "bob_height": rng.randint(10, 22),
            "phase": rng.uniform(0, 6.28),
        })

    return pieces


def draw_floating_pieces(screen):
    """Call once per frame, before any foreground content, on a screen
    that wants this backdrop (title, welcome)."""
    global _floating_pieces, _floating_pieces_tick

    if _floating_pieces is None:
        _floating_pieces = _build_floating_pieces()

    now = pygame.time.get_ticks() / 1000
    dt = 0.016 if _floating_pieces_tick is None else min(0.05, now - _floating_pieces_tick)
    _floating_pieces_tick = now

    for piece in _floating_pieces:
        piece["angle"] = (piece["angle"] + piece["rot_speed"] * dt) % 360
        bob = math.sin(now * piece["bob_speed"] + piece["phase"]) * piece["bob_height"]

        rotated = pygame.transform.rotate(piece["base_shape"], piece["angle"])
        rect = rotated.get_rect(center=(piece["x"], piece["y"] + bob))
        screen.blit(rotated, rect)


def draw_gradient_rect(
    screen,
    rect,
    color_a,
    color_b,
    border_radius=24,
    corners=(True, True, True, True)
):
    key = (
        rect.size,
        color_a,
        color_b,
        border_radius,
        corners
    )

    gradient = _gradient_cache.get(
        key
    )

    if gradient is None:
        gradient = _build_diagonal_gradient(
            rect.width,
            rect.height,
            color_a,
            color_b
        )
        _gradient_cache[key] = gradient

    shape = _rounded_rect_surface(
        rect.size,
        (255, 255, 255, 255),
        border_radius,
        corners
    ).copy()

    shape.blit(
        gradient,
        (0, 0),
        special_flags=pygame.BLEND_RGB_MULT
    )

    screen.blit(
        shape,
        rect.topleft
    )


_shadow_cache = {}


def draw_blurred_shadow(
    screen,
    rect,
    border_radius=24,
    blur=10,
    alpha=60,
    color=(120, 130, 160),
    offset=(0, 8)
):
    """Soft, gradually-fading shadow (cheap gaussian-style blur via
    downscale + smoothscale-up) instead of a hard-edged duplicate rect.
    """
    pad = blur * 2
    width = rect.width + pad * 2
    height = rect.height + pad * 2

    key = (width, height, border_radius, blur, alpha, color)
    blurred = _shadow_cache.get(key)

    if blurred is None:
        shadow_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        # Same fix as _rounded_rect_surface: prime the background to the
        # shadow's own colour at alpha 0 so the blur fades smoothly to
        # nothing instead of smearing toward black at the edge, which is
        # what was making the shadow read as a hard, dark-edged square.
        shadow_surface.fill((*color, 0))
        pygame.draw.rect(
            shadow_surface,
            (*color, alpha),
            (pad, pad, rect.width, rect.height),
            border_radius=border_radius
        )
        small_size = (max(1, width // blur), max(1, height // blur))
        small = pygame.transform.smoothscale(shadow_surface, small_size)
        blurred = pygame.transform.smoothscale(small, (width, height))
        _shadow_cache[key] = blurred

    screen.blit(
        blurred,
        (rect.left - pad + offset[0], rect.top - pad + offset[1])
    )


_glow_cache = {}


def draw_glow(
    screen,
    center,
    radius,
    color,
    alpha=100
):
    """A soft round halo behind a logo/icon - same premultiplied-alpha-safe
    blur trick as draw_blurred_shadow, just circular and centred rather
    than tied to a rect.
    """
    key = (radius, color, alpha)
    glow = _glow_cache.get(key)

    if glow is None:
        size = radius * 2
        big = pygame.Surface((size, size), pygame.SRCALPHA)
        big.fill((*color, 0))
        pygame.draw.circle(big, (*color, alpha), (radius, radius), radius)

        small = pygame.transform.smoothscale(big, (max(1, size // 6), max(1, size // 6)))
        glow = pygame.transform.smoothscale(small, (size, size))
        _glow_cache[key] = glow

    rect = glow.get_rect(center=center)
    screen.blit(glow, rect)


def draw_translucent_rect(
    screen,
    rect,
    color_rgba,
    border_radius=24
):
    draw_smooth_rect(screen, rect, color_rgba, radius=border_radius)


# --------------------------------------------------
# Image thumbnails
# --------------------------------------------------

def scale_cover(
    image,
    width,
    height
):
    image_width, image_height = image.get_size()

    target_ratio = width / height
    image_ratio = image_width / image_height

    if image_ratio > target_ratio:
        scale_height = height
        scale_width = int(height * image_ratio)
    else:
        scale_width = width
        scale_height = int(width / image_ratio)

    scaled = pygame.transform.smoothscale(
        image,
        (
            max(1, scale_width),
            max(1, scale_height)
        )
    )

    crop_x = (scale_width - width) // 2
    crop_y = (scale_height - height) // 2

    cropped = pygame.Surface((width, height), pygame.SRCALPHA)
    cropped.fill((0, 0, 0, 0))

    cropped.blit(
        scaled,
        (0, 0),
        pygame.Rect(
            crop_x,
            crop_y,
            width,
            height
        )
    )

    return cropped


_rounded_image_cache = {}


def _rounded_image(image, size, radius, corners):
    """A cover-cropped, corner-rounded copy of `image`, built once per
    size and then reused. The pages redraw these every frame (and the
    sidebar animation changes their size in small steps), so rebuilding
    them each frame from a full-size photo was a big part of the lag."""
    key = (id(image), size, radius, corners)
    entry = _rounded_image_cache.get(key)

    if entry is None:
        cropped = scale_cover(image, size[0], size[1])

        result = pygame.Surface(size, pygame.SRCALPHA)
        result.blit(cropped, (0, 0))

        # Anti-aliased mask (supersampled) so the corners come out as a
        # smooth curve instead of a jagged pixel-stair edge.
        mask = _rounded_rect_surface(
            size,
            (255, 255, 255, 255),
            radius,
            corners=corners
        )
        result.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        if len(_rounded_image_cache) > 400:
            _rounded_image_cache.clear()

        # The image itself is kept in the entry so its id() can never be
        # recycled for a different picture while this cache entry lives.
        entry = (image, result)
        _rounded_image_cache[key] = entry

    return entry[1]


def draw_image_top_rounded(
    screen,
    image,
    rect,
    radius=24
):
    screen.blit(
        _rounded_image(image, rect.size, radius, (True, True, False, False)),
        rect.topleft
    )


def draw_image_left_rounded(
    screen,
    image,
    rect,
    radius=24
):
    """Same as draw_image_top_rounded, but the LEFT two corners rounded
    instead of the top two - for a photo panel that sits flush against a
    content panel to its right, so together they read as one card."""
    screen.blit(
        _rounded_image(image, rect.size, radius, (True, False, True, False)),
        rect.topleft
    )


def draw_image_rounded(
    screen,
    image,
    rect,
    radius=24
):
    """Same as draw_image_top_rounded, but all four corners rounded."""
    screen.blit(
        _rounded_image(image, rect.size, radius, (True, True, True, True)),
        rect.topleft
    )


def draw_text(
    screen,
    text,
    font,
    color,
    x,
    y,
    center=True
):
    surface = font.render(
        text,
        True,
        color
    )

    if center:
        rect = surface.get_rect(
            center=(x, y)
        )
    else:
        rect = surface.get_rect(
            topleft=(x, y)
        )

    screen.blit(
        surface,
        rect
    )


def draw_tracked_text(
    screen,
    text,
    font,
    color,
    center_x,
    center_y,
    tracking=4
):
    """Draws text letter-by-letter with extra spacing between characters -
    a plain font.render() sits too tight for a wordmark/hero title.
    """
    letters = [font.render(ch, True, color) for ch in text]
    total_width = sum(letter.get_width() for letter in letters)
    total_width += tracking * (len(letters) - 1)

    x = center_x - total_width // 2
    for letter in letters:
        rect = letter.get_rect(midleft=(x, center_y))
        screen.blit(letter, rect)
        x += letter.get_width() + tracking


# --------------------------------------------------
# Rounded card
# --------------------------------------------------

def draw_card(
    screen,
    rect,
    color,
    border_color=None,
    border_radius=24
):
    draw_blurred_shadow(
        screen,
        rect,
        border_radius=border_radius,
        blur=10,
        alpha=50,
        color=CARD_SHADOW,
        offset=(0, 8)
    )

    draw_smooth_rect(screen, rect, color, radius=border_radius)

    if border_color:
        draw_smooth_rect(screen, rect, border_color, radius=border_radius, width=1)


# --------------------------------------------------
# Puzzle piece icon
# --------------------------------------------------

_piece_icon_cache = {}


def draw_piece_icon(
    screen,
    center,
    size,
    color
):
    """A real interlocking jigsaw-piece silhouette: a rounded square body
    with a tab bump on top and a notch cut into the right edge, so it
    reads as an actual puzzle piece rather than a rounded blob.

    Rendered on its own transparent surface at 4x and downsampled, both
    for anti-aliased curves and so the notch is a true transparent hole
    (whatever sits behind it shows through cleanly, no more sampling the
    background colour and painting a hard-edged patch over it).
    """
    key = (size, color)
    icon = _piece_icon_cache.get(key)

    if icon is None:
        scale = 4
        tab = size * 0.34
        radius = tab * 0.62
        pad = int(tab * 1.4)
        canvas = (int(size) + pad * 2) * scale

        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        body = int(size * scale)
        body_rect = pygame.Rect(0, 0, body, body)
        body_rect.center = (canvas // 2, canvas // 2)

        pygame.draw.rect(
            big,
            color,
            body_rect,
            border_radius=int(size * 0.16 * scale)
        )

        # Tab bump on the top edge
        pygame.draw.circle(
            big,
            color,
            (body_rect.centerx, body_rect.top),
            int(radius * scale)
        )

        # Notch cut into the right edge, via an alpha-hole mask (the
        # same masking technique the real puzzle pieces use in puzzle.py)
        hole = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        hole.fill((255, 255, 255, 255))
        pygame.draw.circle(
            hole,
            (255, 255, 255, 0),
            (body_rect.right, body_rect.centery),
            int(radius * scale)
        )
        big.blit(hole, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        icon_size = canvas // scale
        icon = pygame.transform.smoothscale(big, (icon_size, icon_size))
        _piece_icon_cache[key] = icon

    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


_diamond_logo_cache = {}


def draw_diamond_logo(
    screen,
    center,
    size,
    color_a,
    color_b
):
    """The title-screen wordmark's icon: a gradient-filled square, marked
    with a small pinwheel seam at its centre and four short seam lines
    running to its edges (reading as '4 interlocking pieces'), rotated
    45 degrees into a diamond.
    """
    key = (size, color_a, color_b)
    logo = _diamond_logo_cache.get(key)

    if logo is None:
        scale = 4
        tile = size * scale

        base = pygame.Surface((tile, tile), pygame.SRCALPHA)
        base.fill((*color_a, 0))

        radius = int(tile * 0.22)
        pygame.draw.rect(base, (255, 255, 255, 255), base.get_rect(), border_radius=radius)

        gradient = _build_diagonal_gradient(tile, tile, color_a, color_b, small_size=32)
        base.blit(gradient, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        cx, cy = tile // 2, tile // 2
        seam_color = (255, 255, 255, 110)
        knob = int(tile * 0.12)
        line_w = max(2, int(tile * 0.018))

        pygame.draw.circle(base, seam_color, (cx - knob, cy - knob), knob, width=line_w)
        pygame.draw.circle(base, seam_color, (cx + knob, cy - knob), knob, width=line_w)
        pygame.draw.circle(base, seam_color, (cx - knob, cy + knob), knob, width=line_w)
        pygame.draw.circle(base, seam_color, (cx + knob, cy + knob), knob, width=line_w)

        pygame.draw.line(base, seam_color, (cx, 0), (cx, cy - knob), line_w)
        pygame.draw.line(base, seam_color, (cx, cy + knob), (cx, tile), line_w)
        pygame.draw.line(base, seam_color, (0, cy), (cx - knob, cy), line_w)
        pygame.draw.line(base, seam_color, (cx + knob, cy), (tile, cy), line_w)

        small = pygame.transform.smoothscale(base, (size, size))
        logo = pygame.transform.rotozoom(small, 45, 1.0)
        _diamond_logo_cache[key] = logo

    rect = logo.get_rect(center=center)
    screen.blit(logo, rect)


# --------------------------------------------------
# Layout: sidebar + content area
# --------------------------------------------------

# ---- Hover zoom tuning ----
# The nav button under the mouse grows a little, quickly. Every size a
# button is drawn at (its shadow, rounded shape and gradient) is built the
# first time it's used and then cached - so the zoom moves in a few fixed
# sizes rather than a continuous smear of new ones, which keeps it smooth.
NAV_HOVER_ZOOM = 0.06       # how much bigger a hovered button gets (6%)
NAV_HOVER_SPEED = 20.0      # how fast it grows / shrinks - higher = snappier
NAV_HOVER_STEPS = 6         # number of distinct sizes between resting and zoomed



# --------------------------------------------------
# Puzzle screen layout
# --------------------------------------------------
# The puzzle-solving screen drops the sidebar entirely (see main.py) so
# the board and tray get the whole window to breathe, full-bleed like
# the reference design. These constants are the single source of truth
# for that layout - shared by the header/board/tray drawing helpers
# below AND by main.py's create_puzzle(), so the fitted puzzle image
# always lines up with the chrome drawn around it.

PUZZLE_MARGIN = 40
PUZZLE_HEADER_TOP = 26
PUZZLE_ICON_RADIUS = 32
PUZZLE_PILL_RADIUS = 12  # the title/timer/progress pills use this smaller,
                          # more rectangular corner radius
PUZZLE_ICON_CORNER_RADIUS = 20  # back/gear buttons are a rounded square at
                                 # this corner radius, not a full circle
PUZZLE_HEADER_GAP = 16  # the one gap used between every pair of header
                         # elements, so the row reads as evenly spaced
PUZZLE_TRAY_HEIGHT = 170

# The carousel is a single row of upright, non-overlapping pieces, so it
# doesn't need the pile/wheel's tall, roomy dish - just enough height for
# one row of pieces plus a little breathing space, so it reads as a
# thin, minimalist strip instead of a mostly-empty tray.
PUZZLE_CAROUSEL_TRAY_HEIGHT = 118

PUZZLE_BOARD_GAP = 36
PUZZLE_TRAY_RADIUS = 44  # corner radius of the tray "dish" - shared with
                          # puzzle.py so the carousel can clip its pieces
                          # to the exact same rounded shape as the card
                          # drawn underneath them

GLASS_BORDER = (255, 255, 255, 200)
ACCENT_GLOW = (140, 210, 205)

_dock_active = False
_dock_position = "left"


def set_sidebar_mode(active, position="left"):
    """Called once per frame, before anything else draws, so
    get_content_rect() (and the dock itself) agree on whether the dock
    is on screen right now, and which edge it's docked to."""
    global _dock_active, _dock_position
    _dock_active = active
    _dock_position = position


def get_content_rect():
    """The page area, always leaving a clear strip for the dock along
    whichever edge it's docked to (see set_sidebar_mode) - or the full
    window on the few screens (title/welcome/puzzle/complete) the dock
    doesn't appear on."""
    if _dock_active:
        width = get_dock_rect(_dock_position).width
        if _dock_position == "right":
            return pygame.Rect(0, 0, WIDTH - width, HEIGHT)
        return pygame.Rect(width, 0, WIDTH - width, HEIGHT)

    return pygame.Rect(0, 0, WIDTH, HEIGHT)


# --------------------------------------------------
# Icon dock - the sidebar
#
# Icon-only, always visible, and can sit on either edge
# (settings["sidebar_position"]). Achievements gets its own button
# rather than living inside Collection's tabs, and there's a Menu
# button (back to the title screen).
#
# Distributed down the FULL height of the window, edge to edge, rather
# than a small cluster centred in the middle - Exit sits apart from the
# other five with a noticeably larger gap above it, so a mis-click
# there is much less likely, matching the reference layout.
# --------------------------------------------------

DOCK_ITEMS = (
    ("play", ("menu", "levels", "category", "daily", "journey", "main_menu")),
    ("collection", ("collection",)),
    ("achievements", ("achievements",)),
    ("shop", ("shop",)),
    ("settings", ("settings",)),
    ("menu_home", ("title",)),
    ("exit", ()),
)

DOCK_BUTTON_SIZE = 64
DOCK_MARGIN = 24        # distance from the screen edge, and from top/bottom
DOCK_EXIT_GAP_RATIO = 1.7  # the gap before Exit, as a multiple of a normal gap
DOCK_CORNER_RADIUS = 32
DOCK_PLAY_OFFSET = 14
DOCK_EXIT_OFFSET = 28

_dock_hover = {}
_dock_hover_tick = None


def _update_dock_hover(hovered_key):
    global _dock_hover_tick

    now = pygame.time.get_ticks() / 1000
    dt = 0.016 if _dock_hover_tick is None else min(0.05, now - _dock_hover_tick)
    _dock_hover_tick = now

    blend = 1 - math.exp(-dt * NAV_HOVER_SPEED)
    for key, _active_on in DOCK_ITEMS:
        target = 1.0 if key == hovered_key else 0.0
        value = _dock_hover.get(key, 0.0)
        value += (target - value) * blend
        if abs(target - value) < 0.01:
            value = target
        _dock_hover[key] = value


def get_dock_rect(position="left"):
    """The dock spans the full window height, minus a margin top and
    bottom - not just a cluster sized to its buttons."""
    width = DOCK_BUTTON_SIZE + DOCK_MARGIN
    x = DOCK_MARGIN if position != "right" else WIDTH - DOCK_MARGIN - width
    return pygame.Rect(round(x), DOCK_MARGIN, width, HEIGHT - 2 * DOCK_MARGIN)


def get_page_back_rect(dock_rect=None, dock_position=None, width=250, height=60):
    """A consistent Back-button slot aligned just above the sidebar's foot."""
    if dock_rect is None and _dock_active:
        dock_position = dock_position or _dock_position
        dock_rect = get_dock_rect(dock_position)

    if dock_rect is None or dock_position == "right":
        left = 60
    else:
        left = dock_rect.right + 40

    return pygame.Rect(left, HEIGHT - 88, width, height)


def _dock_button_centers(dock):
    """One y-coordinate per DOCK_ITEMS entry, evenly spaced down the
    dock's height except for a wider gap right before the last (Exit)."""
    count = len(DOCK_ITEMS)
    gaps = count - 1
    # Every gap counts as 1 unit except the last, which counts as
    # DOCK_EXIT_GAP_RATIO units - so the space between Exit and the
    # button above it is visibly larger than the others.
    units = (gaps - 1) + DOCK_EXIT_GAP_RATIO if gaps > 0 else 1

    usable = dock.height - DOCK_BUTTON_SIZE
    unit_height = usable / units if units else 0

    centers = []
    y = dock.top + DOCK_BUTTON_SIZE / 2
    for index in range(count):
        centers.append(round(y))
        if index < gaps - 1:
            y += unit_height
        else:
            y += unit_height * DOCK_EXIT_GAP_RATIO

    centers[0] += DOCK_PLAY_OFFSET
    centers[-1] -= DOCK_EXIT_OFFSET
    return centers


def _draw_dock_icon(screen, key, center, color):
    if key == "play":
        draw_play_icon(screen, center, 28, color)
    elif key == "collection":
        draw_gallery_icon(screen, center, 30, color)
    elif key == "achievements":
        draw_medal_icon(screen, center, 32, color)
    elif key == "shop":
        draw_shop_icon(screen, center, 28, color)
    elif key == "settings":
        draw_gear_icon(screen, center, 30, color)
    elif key == "menu_home":
        draw_menu_lines_icon(screen, center, 28, color)
    elif key == "exit":
        draw_power_icon(screen, center, 28, color)


def draw_icon_dock(screen, current_screen, position="left"):
    """Draws the icon-only dock and returns (nav_rects, None) - always
    None for the logo half of that pair, since the dock has no logo of
    its own; the click handler already treats a None logo_rect as
    "nothing to check" so this needs no special-casing there."""
    dock = get_dock_rect(position)
    mouse_position = pygame.mouse.get_pos()

    draw_glass(screen, dock, radius=DOCK_CORNER_RADIUS, tint=SIDEBAR_BACKGROUND)

    centers = _dock_button_centers(dock)
    layout = []
    for (key, active_on), cy in zip(DOCK_ITEMS, centers):
        rect = pygame.Rect(0, 0, DOCK_BUTTON_SIZE, DOCK_BUTTON_SIZE)
        rect.center = (dock.centerx, cy)
        layout.append((key, active_on, rect))

    hovered_key = None
    for key, _active_on, rect in layout:
        if rect.collidepoint(mouse_position):
            hovered_key = key

    _update_dock_hover(hovered_key)

    nav_rects = {}
    for key, active_on, rect in layout:
        nav_rects[key] = rect
        is_active = current_screen in active_on

        step = round(_dock_hover.get(key, 0.0) * NAV_HOVER_STEPS)
        grow = NAV_HOVER_ZOOM * step / NAV_HOVER_STEPS
        grown = rect.inflate(2 * round(rect.width * grow / 2), 2 * round(rect.height * grow / 2))

        if is_active:
            draw_gradient_rect(screen, grown, NAV_GRADIENT[0], NAV_GRADIENT[1], border_radius=grown.width // 2)
            icon_color = TEXT
        else:
            draw_card(screen, grown, WHITE, None, border_radius=grown.width // 2)
            icon_color = TEXT if key == hovered_key else MUTED_TEXT

        _draw_dock_icon(screen, key, grown.center, icon_color)

    return nav_rects, None





# A noticeably more transparent tint than the default draw_glass() tint,
# used for the puzzle-screen header row so it reads as actual frosted
# glass rather than a near-opaque white bar.
HEADER_GLASS_TINT = (255, 255, 255, 90)


def get_puzzle_header_rect():
    return pygame.Rect(
        PUZZLE_MARGIN,
        PUZZLE_HEADER_TOP,
        WIDTH - PUZZLE_MARGIN * 2,
        PUZZLE_ICON_RADIUS * 2
    )


def get_puzzle_board(tray_height=PUZZLE_TRAY_HEIGHT):
    header = get_puzzle_header_rect()
    top = header.bottom + 34
    bottom = HEIGHT - PUZZLE_MARGIN - tray_height - PUZZLE_BOARD_GAP
    return pygame.Rect(
        PUZZLE_MARGIN,
        top,
        WIDTH - PUZZLE_MARGIN * 2,
        max(200, bottom - top)
    )


def get_puzzle_pause_panel_rect(board_area, header_button, size=(320, 380)):
    """Place the pause panel below the active header control, on the same
    side of the puzzle workspace as that control."""
    panel = pygame.Rect((0, 0), size)
    panel.top = board_area.top + 16
    if header_button.centerx < board_area.centerx:
        panel.left = header_button.left
    else:
        panel.right = header_button.right
    panel.clamp_ip(board_area)
    return panel


def get_piece_area(tray_height=PUZZLE_TRAY_HEIGHT):
    top = HEIGHT - PUZZLE_MARGIN - tray_height
    return pygame.Rect(
        PUZZLE_MARGIN,
        top,
        WIDTH - PUZZLE_MARGIN * 2,
        tray_height
    )


# The POWER-UPS panel sits bottom-left, and the piece tray takes the rest
# of that row to its right.
PUZZLE_POWERUPS_WIDTH = 330
PUZZLE_POWERUPS_GAP = 24


def get_powerups_rect(tray_height=PUZZLE_TRAY_HEIGHT):
    return pygame.Rect(
        PUZZLE_MARGIN,
        HEIGHT - PUZZLE_MARGIN - tray_height,
        PUZZLE_POWERUPS_WIDTH,
        tray_height
    )


def get_tray_area(tray_height=PUZZLE_TRAY_HEIGHT):
    """The piece tray on the puzzle screen: everything to the right of
    the POWER-UPS panel, same row."""
    left = PUZZLE_MARGIN + PUZZLE_POWERUPS_WIDTH + PUZZLE_POWERUPS_GAP
    return pygame.Rect(
        left,
        HEIGHT - PUZZLE_MARGIN - tray_height,
        WIDTH - PUZZLE_MARGIN - left,
        tray_height
    )


def get_carousel_shuffle_button_rect(area):
    """A free shuffle control inside the carousel tray itself, pinned to the
    right edge so it uses otherwise empty tray space without changing the rest
    of the puzzle layout."""
    margin = 14
    button_h = min(area.height - margin * 2, max(54, int(area.height * 0.72)))
    button_w = min(max(220, int(area.width * 0.25)), area.width - margin * 2)
    rect = pygame.Rect(
        area.right - button_w - margin,
        area.top + (area.height - button_h) // 2,
        button_w,
        button_h,
    )
    return rect


def get_carousel_piece_view_rect(area):
    """Carousel content stays inset from the tray edge and ends before the
    shuffle button, leaving the button and its padding completely clear."""
    left = area.left + 32
    right = max(left, get_carousel_shuffle_button_rect(area).left - 24)
    return pygame.Rect(left, area.top, right - left, area.height)


def draw_carousel_shuffle_button(screen, area, font):
    """Prominent theme-aware button for the free carousel shuffle control."""
    rect = get_carousel_shuffle_button_rect(area)
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    draw_blurred_shadow(
        screen, rect, border_radius=18, blur=8, alpha=38,
        color=CARD_SHADOW, offset=(0, 4)
    )
    draw_smooth_rect(screen, rect, (*WHITE, 255), radius=18)
    draw_smooth_rect(
        screen, rect, (*TRACK_BACKGROUND, 255) if hovered else (*WHITE, 255),
        radius=18, width=1
    )
    draw_smooth_rect(screen, rect, (*CARD_BORDER, 220), radius=18, width=1)
    draw_text(screen, "SHUFFLE TRAY", font, TEXT, rect.centerx, rect.centery)

    return rect


def draw_tray_card(screen, area, carousel=False):
    """The piece tray: a glassy, rounded 'dish' the loose pieces are
    tipped into. A soft accent glow runs along its top and bottom edges,
    and a slightly darker, inset 'well' inside it gives the pile
    something to sit in.

    The carousel uses a flatter, brighter tray treatment so the row of
    upright pieces sits like a modern gallery strip rather than a deep
    pile dish.
    """
    radius = PUZZLE_TRAY_RADIUS

    if carousel:
        tray_color = tuple(max(0, channel - 8) for channel in CARD_BACKGROUND) if IS_DARK else CARD_BACKGROUND
        inset_color = tuple(max(0, channel - 12) for channel in TRACK_BACKGROUND) if IS_DARK else TRACK_BACKGROUND
        draw_blurred_shadow(
            screen, area, border_radius=26, blur=10, alpha=24,
            color=CARD_SHADOW, offset=(0, 5)
        )
        draw_smooth_rect(screen, area, (*tray_color, 245), radius=26)
        inset = area.inflate(-12, -12)
        draw_smooth_rect(screen, inset, (*inset_color, 190), radius=20)
        draw_smooth_rect(screen, area, (*CARD_BORDER, 220), radius=26, width=2)
        return

    glow_alpha = 28 if IS_DARK else 110
    glow_color = TRACK_BACKGROUND if IS_DARK else ACCENT_GLOW
    top_glow = pygame.Rect(area.left + 24, area.top - 2, area.width - 48, 14)
    draw_blurred_shadow(
        screen, top_glow, border_radius=7, blur=10, alpha=glow_alpha,
        color=glow_color, offset=(0, 0)
    )

    bottom_glow = pygame.Rect(area.left + 24, area.bottom - 12, area.width - 48, 16)
    draw_blurred_shadow(
        screen, bottom_glow, border_radius=8, blur=10, alpha=round(glow_alpha * 0.86),
        color=glow_color, offset=(0, 4)
    )

    draw_glass(screen, area, radius=radius, tint=PIECE_AREA_BACKGROUND)

    # The inset well: a cool, faintly darker surface with a light rim.
    well = area.inflate(-22, -22)
    draw_smooth_rect(screen, well, (*TRACK_BACKGROUND, 62), radius=radius - 11)
    draw_smooth_rect(screen, well, PIECE_AREA_BORDER, radius=radius - 11, width=1)


# --------------------------------------------------
# Glass surfaces - the shared "glassy" look used for every pill, icon
# button and menu button on the puzzle screen: a soft shadow, a
# translucent tint, a light sheen catching the top edge, and a hairline
# border. Cheaper than draw_frosted_panel below (no live backdrop
# sampling) so it's safe to use on things drawn every frame; still reads
# as the same family of "glass" thanks to the shared sheen + border.
# --------------------------------------------------

_sheen_cache = {}


def draw_glass_sheen(screen, rect, radius=20, max_alpha=60):
    """A soft light streak fading down from the top of a rounded shape,
    like light catching the top of a glass surface."""
    key = (rect.size, radius, max_alpha)
    sheen = _sheen_cache.get(key)

    if sheen is None:
        mask = _rounded_rect_surface(rect.size, (255, 255, 255, 255), radius)

        fade = pygame.Surface(rect.size, pygame.SRCALPHA)
        for y in range(rect.height):
            t = y / max(1, rect.height - 1)
            alpha = int(max_alpha * max(0.0, 1 - t * 1.8))
            if alpha > 0:
                pygame.draw.line(fade, (255, 255, 255, alpha), (0, y), (rect.width, y))

        sheen = mask.copy()
        sheen.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        _sheen_cache[key] = sheen

    screen.blit(sheen, rect.topleft)


_scrim_cache = {}


def draw_bottom_scrim(screen, rect, radius=20, color=(8, 12, 22), max_alpha=210, start=0.42):
    """A soft dark wash rising from the bottom of a rounded shape, just
    strong enough for white text to sit on top of a photo - used by the
    big, image-forward category tiles instead of a separate solid footer.
    `start` is how far down (as a fraction of the height) the wash begins.
    """
    key = (rect.size, radius, color, max_alpha, start)
    scrim = _scrim_cache.get(key)

    if scrim is None:
        mask = _rounded_rect_surface(rect.size, (255, 255, 255, 255), radius)

        fade = pygame.Surface(rect.size, pygame.SRCALPHA)
        fade_from = rect.height * start
        span = max(1, rect.height - fade_from)
        for y in range(rect.height):
            t = max(0.0, (y - fade_from) / span)
            alpha = int(max_alpha * (t ** 1.5))
            if alpha > 0:
                pygame.draw.line(fade, (*color, alpha), (0, y), (rect.width, y))

        scrim = mask.copy()
        scrim.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        if len(_scrim_cache) > 40:
            _scrim_cache.clear()
        _scrim_cache[key] = scrim

    screen.blit(scrim, rect.topleft)


def draw_glass(screen, rect, radius=20, tint=(255, 255, 255, 185), border=True, shadow=True, hovered=False):
    if hovered:
        r, g, b, a = tint
        tint = (r, g, b, min(255, a + 25))

    if shadow:
        draw_blurred_shadow(
            screen, rect, border_radius=radius, blur=9, alpha=42,
            color=CARD_SHADOW, offset=(0, 5)
        )

    draw_smooth_rect(screen, rect, tint, radius=radius)
    draw_glass_sheen(screen, rect, radius=radius)

    if border:
        draw_smooth_rect(screen, rect, GLASS_BORDER, radius=radius, width=1)


# --------------------------------------------------
# Icon buttons (back chevron / settings gear)
# --------------------------------------------------

_chevron_cache = {}


def _build_chevron_icon(size, color):
    key = (size, color)
    icon = _chevron_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        span = canvas * 0.24
        thickness = max(2, int(canvas * 0.09))
        points = [
            (int(canvas * 0.62), int(canvas / 2 - span)),
            (int(canvas * 0.62 - span), int(canvas / 2)),
            (int(canvas * 0.62), int(canvas / 2 + span))
        ]
        pygame.draw.lines(big, color, False, points, thickness)

        icon = pygame.transform.smoothscale(big, (size, size))
        _chevron_cache[key] = icon

    return icon


def draw_chevron_icon(screen, center, size, color=None):
    icon = _build_chevron_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


_play_cache = {}


def _build_play_icon(size, color):
    key = (size, color)
    icon = _play_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        cx, cy = canvas / 2, canvas / 2
        r = canvas * 0.32
        # A triangle's centroid sits left of its visual centre - nudge it
        # right a touch so it looks optically centred rather than
        # off-balance to the left.
        offset = r * 0.15
        points = [
            (cx - r * 0.6 + offset, cy - r),
            (cx - r * 0.6 + offset, cy + r),
            (cx + r * 0.9 + offset, cy),
        ]
        pygame.draw.polygon(big, color, points)

        icon = pygame.transform.smoothscale(big, (size, size))
        _play_cache[key] = icon

    return icon


def draw_play_icon(screen, center, size, color=None):
    icon = _build_play_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


_power_cache = {}


def _build_power_icon(size, color):
    key = (size, color)
    icon = _power_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        cx, cy = canvas / 2, canvas / 2
        radius = canvas * 0.30
        line_w = max(2, int(canvas * 0.11))
        transparent = (*color[:3], 0)

        # A ring: a filled circle with a smaller, fully transparent
        # circle punched out of its middle - pygame's draw functions
        # overwrite pixels rather than alpha-blend them, so painting
        # alpha-0 really does cut a hole (the same trick as the gear's
        # centre and the lightbulb's thread lines) - far more reliable
        # than pygame.draw.arc, whose sweep direction and anti-aliasing
        # made the previous version of this icon read as a spiral
        # rather than a power glyph.
        pygame.draw.circle(big, color, (cx, cy), radius)
        pygame.draw.circle(big, transparent, (cx, cy), radius - line_w)

        # A flat notch cut from the top of the ring, then the vertical
        # tick drawn back through it - the classic power-button glyph.
        gap_w = line_w * 1.8
        notch_h = line_w + 6
        notch = pygame.Rect(0, 0, gap_w, notch_h)
        notch.center = (cx, cy - radius)
        pygame.draw.rect(big, transparent, notch)

        pygame.draw.line(
            big, color,
            (cx, cy - radius * 1.25), (cx, cy - radius * 0.35), line_w
        )

        icon = pygame.transform.smoothscale(big, (size, size))
        _power_cache[key] = icon

    return icon


def draw_power_icon(screen, center, size, color=None):
    icon = _build_power_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


_menu_lines_cache = {}


def _build_menu_lines_icon(size, color):
    key = (size, color)
    icon = _menu_lines_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        line_w = canvas * 0.10
        half = canvas * 0.32
        cx, cy = canvas / 2, canvas / 2

        for frac in (-0.28, 0.0, 0.28):
            y = cy + canvas * frac
            rect = pygame.Rect(0, 0, half * 2, line_w)
            rect.center = (cx, y)
            pygame.draw.rect(big, color, rect, border_radius=int(line_w / 2))

        icon = pygame.transform.smoothscale(big, (size, size))
        _menu_lines_cache[key] = icon

    return icon


def draw_menu_lines_icon(screen, center, size, color=None):
    icon = _build_menu_lines_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


_medal_cache = {}


def _build_medal_icon(size, color):
    key = (size, color)
    icon = _medal_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        def P(x, y):
            return (canvas * x, canvas * y)

        pygame.draw.polygon(big, color, [P(.22, .03), P(.42, .03), P(.62, .56), P(.44, .56)])
        pygame.draw.polygon(big, color, [P(.78, .03), P(.58, .03), P(.38, .56), P(.56, .56)])

        cx, cy, r = canvas * .5, canvas * .66, canvas * .27
        halo = r + canvas * .055
        pygame.draw.circle(big, (*color[:3], 0), (cx, cy), halo)
        pygame.draw.circle(big, color, (cx, cy), r)

        star_points = []
        outer_r, inner_r = r * .68, r * .30
        for i in range(10):
            rr = outer_r if i % 2 == 0 else inner_r
            angle = -math.pi / 2 + i * math.pi / 5
            star_points.append((cx + rr * math.cos(angle), cy + rr * math.sin(angle)))
        pygame.draw.polygon(big, (*color[:3], 0), star_points)

        icon = pygame.transform.smoothscale(big, (size, size))
        _medal_cache[key] = icon

    return icon
def draw_medal_icon(screen, center, size, color=None):
    icon = _build_medal_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


_gear_cache = {}




_gallery_cache = {}


def _build_gallery_icon(size, color):
    """A framed landscape picture - Collection's icon. Clearer at a
    glance than the diamond logomark (that's the app's brand mark, not
    really a "your collection" glyph)."""
    key = (size, color)
    icon = _gallery_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        def P(x, y):
            return (canvas * x, canvas * y)

        thickness = canvas * 0.085
        outer = pygame.Rect(P(.10, .18), (canvas * .80, canvas * .64))
        pygame.draw.rect(big, color, outer, border_radius=int(canvas * .12))

        inner = outer.inflate(-thickness * 2, -thickness * 2)
        pygame.draw.rect(big, (*color[:3], 0), inner, border_radius=int(canvas * .06))

        sun_r = canvas * 0.07
        pygame.draw.circle(big, color, P(.67, .38), sun_r)

        pygame.draw.polygon(big, color, [P(.21, .70), P(.40, .46), P(.53, .62), P(.62, .53), P(.79, .70)])

        icon = pygame.transform.smoothscale(big, (size, size))
        _gallery_cache[key] = icon

    return icon


def draw_gallery_icon(screen, center, size, color=None):
    icon = _build_gallery_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


_shop_icon_cache = {}


def _build_shop_icon(size, color):
    key = (size, color)
    icon = _shop_icon_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        bag = pygame.Rect(int(canvas * 0.18), int(canvas * 0.24), int(canvas * 0.64), int(canvas * 0.54))
        pygame.draw.rect(big, color, bag, border_radius=int(canvas * 0.16))
        pygame.draw.line(big, color, (int(canvas * 0.28), int(canvas * 0.24)), (int(canvas * 0.34), int(canvas * 0.10)), int(canvas * 0.08))
        pygame.draw.line(big, color, (int(canvas * 0.72), int(canvas * 0.24)), (int(canvas * 0.66), int(canvas * 0.10)), int(canvas * 0.08))

        coin = pygame.Rect(int(canvas * 0.38), int(canvas * 0.46), int(canvas * 0.24), int(canvas * 0.24))
        pygame.draw.ellipse(big, color, coin)
        pygame.draw.circle(big, (*color[:3], 0), (int(canvas * 0.50), int(canvas * 0.58)), int(canvas * 0.07))

        icon = pygame.transform.smoothscale(big, (size, size))
        _shop_icon_cache[key] = icon

    return icon


def draw_shop_icon(screen, center, size, color=None):
    icon = _build_shop_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


def _build_gear_icon(size, color):
    key = (size, color)
    icon = _gear_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        cx = cy = canvas / 2
        outer_r = canvas * 0.30
        inner_r = canvas * 0.15
        tooth_len = canvas * 0.10
        tooth_half_w = canvas * 0.07

        pygame.draw.circle(big, color, (int(cx), int(cy)), int(outer_r))

        teeth = 8
        for i in range(teeth):
            angle = math.radians(i * (360 / teeth))
            # A small trapezoid pointing outward from the gear body,
            # built in local space (pointing "up") then rotated into
            # place around the gear's centre.
            local = [
                (-tooth_half_w, -(outer_r + tooth_len)),
                (tooth_half_w, -(outer_r + tooth_len)),
                (tooth_half_w * 0.7, -outer_r * 0.85),
                (-tooth_half_w * 0.7, -outer_r * 0.85)
            ]
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            world = [
                (int(cx + lx * cos_a - ly * sin_a), int(cy + lx * sin_a + ly * cos_a))
                for lx, ly in local
            ]
            pygame.draw.polygon(big, color, world)

        # Punch the centre hole through - same masked-hole trick as
        # draw_piece_icon's notch.
        hole = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        hole.fill((255, 255, 255, 255))
        pygame.draw.circle(hole, (255, 255, 255, 0), (int(cx), int(cy)), int(inner_r))
        big.blit(hole, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        icon = pygame.transform.smoothscale(big, (size, size))
        _gear_cache[key] = icon

    return icon


def draw_gear_icon(screen, center, size, color=None):
    icon = _build_gear_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


_lightbulb_cache = {}


def _build_lightbulb_icon(size, color):
    key = (size, color)
    icon = _lightbulb_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        cx = canvas / 2
        bulb_radius = canvas * 0.24
        bulb_cy = canvas * 0.40

        pygame.draw.circle(big, color, (int(cx), int(bulb_cy)), int(bulb_radius))

        base_width = canvas * 0.24
        base_height = canvas * 0.16
        base_rect = pygame.Rect(0, 0, int(base_width), int(base_height))
        base_rect.midtop = (int(cx), int(bulb_cy + bulb_radius * 0.5))
        pygame.draw.rect(big, color, base_rect, border_radius=int(base_height * 0.3))

        # Two thin "screw thread" gaps punched through the base - same
        # masked-hole trick as the gear's centre hole.
        for i in range(2):
            y = int(base_rect.top + base_rect.height * (0.32 + i * 0.36))
            hole = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
            hole.fill((255, 255, 255, 255))
            pygame.draw.line(
                hole, (255, 255, 255, 0),
                (base_rect.left - 2, y), (base_rect.right + 2, y),
                max(1, int(canvas * 0.025))
            )
            big.blit(hole, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        icon = pygame.transform.smoothscale(big, (size, size))
        _lightbulb_cache[key] = icon

    return icon


def draw_lightbulb_icon(screen, center, size, color=None):
    icon = _build_lightbulb_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


_coin_cache = {}


def _build_coin_icon(size, color):
    """A simple gold coin: an outer disc, an inner ring, and a small star
    stamped in the middle - reads clearly even at small reward-icon sizes.
    """
    key = (size, color)
    icon = _coin_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        cx = cy = canvas / 2
        outer_r = canvas * 0.46
        inner_r = canvas * 0.35

        darker = tuple(max(0, c - 55) for c in color[:3])

        pygame.draw.circle(big, color, (int(cx), int(cy)), int(outer_r))
        pygame.draw.circle(
            big, darker, (int(cx), int(cy)), int(inner_r),
            max(2, int(canvas * 0.05))
        )

        points = 5
        star_outer = inner_r * 0.6
        star_inner = star_outer * 0.42
        star_points = []
        for i in range(points * 2):
            angle = math.radians(i * (360 / (points * 2)) - 90)
            r = star_outer if i % 2 == 0 else star_inner
            star_points.append((
                int(cx + r * math.cos(angle)),
                int(cy + r * math.sin(angle))
            ))
        pygame.draw.polygon(big, darker, star_points)

        icon = pygame.transform.smoothscale(big, (size, size))
        _coin_cache[key] = icon

    return icon


def draw_coin_icon(screen, center, size, color=None):
    icon = _build_coin_icon(size, color or YELLOW)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


_trophy_cache = {}


def _build_trophy_icon(size, color):
    """A small trophy silhouette: a cup body, two side handles, a stem
    and a base - simple filled shapes, no outlines, so it reads well at
    the small sizes used in a reward row.
    """
    key = (size, color)
    icon = _trophy_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        cx = canvas / 2
        cup_top = canvas * 0.14
        cup_bottom = canvas * 0.52
        cup_half_top = canvas * 0.26
        cup_half_bottom = canvas * 0.13

        pygame.draw.polygon(big, color, [
            (cx - cup_half_top, cup_top),
            (cx + cup_half_top, cup_top),
            (cx + cup_half_bottom, cup_bottom),
            (cx - cup_half_bottom, cup_bottom),
        ])

        handle_radius = canvas * 0.15
        handle_width = max(2, int(canvas * 0.07))

        left_handle_rect = pygame.Rect(0, 0, handle_radius * 2, handle_radius * 2)
        left_handle_rect.center = (
            int(cx - cup_half_top - handle_radius * 0.25),
            int(cup_top + handle_radius * 0.85)
        )
        pygame.draw.arc(
            big, color, left_handle_rect,
            math.radians(-110), math.radians(110), handle_width
        )

        right_handle_rect = left_handle_rect.copy()
        right_handle_rect.center = (
            int(cx + cup_half_top + handle_radius * 0.25),
            int(cup_top + handle_radius * 0.85)
        )
        pygame.draw.arc(
            big, color, right_handle_rect,
            math.radians(70), math.radians(290), handle_width
        )

        stem_rect = pygame.Rect(0, 0, int(canvas * 0.09), int(canvas * 0.15))
        stem_rect.midtop = (int(cx), int(cup_bottom))
        pygame.draw.rect(big, color, stem_rect)

        base_rect = pygame.Rect(0, 0, int(canvas * 0.36), int(canvas * 0.09))
        base_rect.midtop = (int(cx), stem_rect.bottom)
        pygame.draw.rect(big, color, base_rect, border_radius=int(base_rect.height * 0.3))

        icon = pygame.transform.smoothscale(big, (size, size))
        _trophy_cache[key] = icon

    return icon


def draw_trophy_icon(screen, center, size, color=None):
    icon = _build_trophy_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


# ---- Achievement icons ----
# Small flat illustrations drawn with plain shapes (no image files needed),
# each on a soft round backdrop so they sit nicely on a card. Built at 4x
# and shrunk for smooth edges, then cached.

ACH_ICON_BG = (232, 241, 250)
_achievement_icon_cache = {}


def _medal_star_points(cx, cy, r_outer, r_inner, points=5):
    result = []
    for i in range(points * 2):
        radius = r_outer if i % 2 == 0 else r_inner
        angle = -math.pi / 2 + i * math.pi / points
        result.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return result


def _build_achievement_icon(kind, size):
    key = (kind, size)
    icon = _achievement_icon_cache.get(key)

    if icon is not None:
        return icon

    scale = 4
    c = size * scale
    big = pygame.Surface((c, c), pygame.SRCALPHA)
    big.fill((*ACH_ICON_BG, 0))

    def P(x, y):
        return (int(c * x), int(c * y))

    def R(x0, y0, x1, y1):
        return pygame.Rect(int(c * x0), int(c * y0), int(c * (x1 - x0)), int(c * (y1 - y0)))

    line = max(2, int(c * 0.04))

    pygame.draw.circle(big, ACH_ICON_BG, P(0.5, 0.5), int(c * 0.5))

    if kind == "medal":
        pygame.draw.polygon(big, (236, 112, 128), [P(.30, .10), P(.47, .10), P(.58, .50), P(.41, .50)])
        pygame.draw.polygon(big, (246, 150, 160), [P(.53, .10), P(.70, .10), P(.59, .50), P(.42, .50)])
        pygame.draw.circle(big, (245, 196, 80), P(.5, .62), int(c * .24))
        pygame.draw.circle(big, (252, 226, 140), P(.5, .62), int(c * .17))
        pygame.draw.polygon(big, (238, 170, 50), _medal_star_points(c * .5, c * .62, c * .11, c * .045))

    elif kind == "palette":
        pygame.draw.ellipse(big, (238, 200, 150), R(.14, .20, .88, .82))
        pygame.draw.circle(big, ACH_ICON_BG, P(.64, .66), int(c * .075))
        for x, y, color in (
            (.30, .42, (232, 110, 110)),
            (.44, .31, (240, 200, 90)),
            (.60, .32, (110, 170, 230)),
            (.72, .44, (120, 200, 150)),
        ):
            pygame.draw.circle(big, color, P(x, y), int(c * .06))

    elif kind == "calendar":
        radius = int(c * .07)
        body = R(.20, .24, .80, .80)
        pygame.draw.rect(big, (255, 255, 255), body, border_radius=radius)
        pygame.draw.rect(big, (196, 206, 222), body, width=max(2, int(c * .02)), border_radius=radius)
        pygame.draw.rect(
            big, (238, 112, 124), R(.20, .24, .80, .40),
            border_top_left_radius=radius, border_top_right_radius=radius
        )
        for x in (.34, .66):
            pygame.draw.rect(big, (150, 160, 180), R(x - .02, .16, x + .02, .30), border_radius=int(c * .02))
        for row in range(2):
            for col in range(3):
                x = .30 + col * .16
                y = .50 + row * .14
                pygame.draw.rect(big, (190, 200, 218), R(x, y, x + .10, y + .09), border_radius=int(c * .02))

    elif kind == "stopwatch":
        blue = (110, 140, 200)
        pygame.draw.rect(big, blue, R(.44, .13, .56, .24), border_radius=int(c * .02))
        pygame.draw.circle(big, blue, P(.5, .57), int(c * .30))
        pygame.draw.circle(big, (255, 255, 255), P(.5, .57), int(c * .24))
        pygame.draw.polygon(big, (250, 205, 210), [P(.5, .57), P(.5, .36), P(.64, .44)])
        pygame.draw.line(big, (232, 90, 100), P(.5, .57), P(.5, .38), line)

    elif kind == "bulb":
        yellow = (250, 208, 90)
        pygame.draw.circle(big, yellow, P(.5, .42), int(c * .22))
        pygame.draw.rect(big, yellow, R(.42, .55, .58, .68))
        pygame.draw.circle(big, (255, 240, 170), P(.43, .36), int(c * .05))
        pygame.draw.rect(big, (170, 178, 194), R(.40, .66, .60, .80), border_radius=int(c * .03))
        pygame.draw.line(big, (140, 148, 168), P(.42, .73), P(.58, .73), max(2, int(c * .02)))

    elif kind == "share":
        blue = (70, 140, 220)
        a, b, d = P(.27, .50), P(.72, .27), P(.72, .73)
        pygame.draw.line(big, blue, a, b, line)
        pygame.draw.line(big, blue, a, d, line)
        for point in (a, b, d):
            pygame.draw.circle(big, blue, point, int(c * .09))

    elif kind == "mountain":
        pygame.draw.circle(big, (250, 208, 90), P(.27, .30), int(c * .08))
        pygame.draw.polygon(
            big, (150, 168, 196),
            [P(.14, .74), P(.42, .28), P(.58, .50), P(.70, .34), P(.90, .74)]
        )
        pygame.draw.polygon(
            big, (110, 128, 158),
            [P(.42, .28), P(.58, .50), P(.48, .50), P(.36, .38)]
        )
        pygame.draw.polygon(big, (255, 255, 255), [P(.42, .28), P(.48, .38), P(.36, .38)])
        pygame.draw.polygon(
            big, (96, 190, 150),
            [P(.58, .50), P(.70, .34), P(.82, .50), P(.90, .74), P(.58, .74)]
        )
        pygame.draw.polygon(big, (255, 255, 255), [P(.70, .34), P(.76, .44), P(.64, .44)])

    elif kind == "moon":
        pygame.draw.circle(big, (255, 214, 120), P(.46, .46), int(c * .26))
        pygame.draw.circle(big, ACH_ICON_BG, P(.58, .38), int(c * .22))
        for x, y, r in ((.76, .24, .022), (.84, .36, .016), (.22, .72, .020)):
            pygame.draw.circle(big, (140, 150, 180), P(x, y), max(1, int(c * r)))

    elif kind == "wheel":
        rim = (150, 168, 196)
        pygame.draw.circle(big, rim, P(.5, .5), int(c * .32), width=max(3, int(c * .05)))
        pygame.draw.circle(big, (96, 190, 150), P(.5, .5), int(c * .08))
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            inner = P(.5 + .10 * math.cos(rad), .5 + .10 * math.sin(rad))
            outer = P(.5 + .30 * math.cos(rad), .5 + .30 * math.sin(rad))
            pygame.draw.line(big, rim, inner, outer, max(2, int(c * .025)))

    elif kind == "trophy":
        gold = (245, 196, 80)
        dark_gold = (208, 160, 55)
        pygame.draw.polygon(big, gold, [P(.34, .22), P(.66, .22), P(.60, .52), P(.40, .52)])
        handle_width = max(3, int(c * .045))
        pygame.draw.arc(big, gold, R(.16, .20, .40, .46), math.radians(90), math.radians(270), handle_width)
        pygame.draw.arc(big, gold, R(.60, .20, .84, .46), math.radians(-90), math.radians(90), handle_width)
        pygame.draw.rect(big, gold, R(.47, .52, .53, .64))
        pygame.draw.rect(big, dark_gold, R(.36, .64, .64, .72), border_radius=int(c * .02))

    elif kind == "puzzle":
        blue = (90, 140, 210)
        pygame.draw.rect(big, blue, R(.24, .24, .76, .76), border_radius=int(c * .06))
        pygame.draw.circle(big, blue, P(.5, .24), int(c * .10))
        pygame.draw.circle(big, ACH_ICON_BG, P(.5, .76), int(c * .105))

    elif kind == "gem":
        teal = (94, 200, 190)
        light = (172, 230, 220)
        pygame.draw.polygon(big, teal, [P(.28, .38), P(.72, .38), P(.5, .80)])
        pygame.draw.polygon(big, light, [P(.28, .38), P(.5, .20), P(.72, .38)])
        pygame.draw.polygon(big, (255, 255, 255), [P(.42, .38), P(.5, .26), P(.58, .38)])

    icon = pygame.transform.smoothscale(big, (size, size))
    _achievement_icon_cache[key] = icon
    return icon


def draw_achievement_icon(screen, kind, center, size=72):
    """kind: medal, palette, calendar, stopwatch, bulb, share, mountain,
    moon, wheel, trophy, puzzle or gem."""
    icon = _build_achievement_icon(kind, size)
    screen.blit(icon, icon.get_rect(center=center))


_lock_cache = {}


def _build_lock_icon(size, color):
    key = (size, color)
    icon = _lock_cache.get(key)

    if icon is None:
        scale = 4
        c = size * scale
        big = pygame.Surface((c, c), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        body = pygame.Rect(int(c * .22), int(c * .44), int(c * .56), int(c * .42))
        pygame.draw.arc(
            big, color,
            pygame.Rect(int(c * .32), int(c * .14), int(c * .36), int(c * .62)),
            0, math.pi, max(3, int(c * .08))
        )
        pygame.draw.rect(big, color, body, border_radius=int(c * .08))
        pygame.draw.circle(big, (255, 255, 255), (int(c * .5), int(c * .61)), int(c * .05))
        pygame.draw.rect(big, (255, 255, 255), pygame.Rect(int(c * .48), int(c * .61), int(c * .04), int(c * .12)))

        icon = pygame.transform.smoothscale(big, (size, size))
        _lock_cache[key] = icon

    return icon


def draw_lock_icon(screen, center, size, color=(150, 165, 190)):
    icon = _build_lock_icon(size, color)
    screen.blit(icon, icon.get_rect(center=center))


_pause_icon_cache = {}


def _build_pause_icon(size, color):
    """Two rounded bars - the Minimal puzzle header's pause button."""
    key = (size, color)
    icon = _pause_icon_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        bar_w = canvas * 0.16
        bar_h = canvas * 0.5
        gap = canvas * 0.14
        top = (canvas - bar_h) / 2

        for dx in (-gap / 2 - bar_w, gap / 2):
            rect = pygame.Rect(int(canvas / 2 + dx), int(top), int(bar_w), int(bar_h))
            pygame.draw.rect(big, color, rect, border_radius=int(bar_w * 0.35))

        icon = pygame.transform.smoothscale(big, (size, size))
        _pause_icon_cache[key] = icon

    return icon


def draw_pause_icon(screen, center, size, color=None):
    icon = _build_pause_icon(size, color or TEXT)
    rect = icon.get_rect(center=center)
    screen.blit(icon, rect)


def _star_points(center, outer_r, inner_r=None, points=5):
    """Corner points of a 5-point star, for pygame.draw.polygon."""
    if inner_r is None:
        inner_r = outer_r * 0.42

    result = []
    for i in range(points * 2):
        angle = math.radians(i * (360 / (points * 2)) - 90)
        r = outer_r if i % 2 == 0 else inner_r
        result.append((center[0] + r * math.cos(angle), center[1] + r * math.sin(angle)))
    return result


def draw_rating_stars(screen, center, total, filled, size, filled_color=None, empty_color=None):
    """`total` small stars in a row, centered on `center` - the first
    `filled` solid, the rest a light outline. Used by the puzzle header's
    difficulty rating (Minimal style)."""
    filled_color = filled_color or TEXT
    empty_color = empty_color or (*MUTED_TEXT, 130)

    spacing = size * 1.15
    start_x = center[0] - spacing * (total - 1) / 2

    for i in range(total):
        star_center = (start_x + i * spacing, center[1])
        points = _star_points(star_center, size / 2)
        if i < filled:
            pygame.draw.polygon(screen, filled_color, points)
        else:
            pygame.draw.polygon(screen, empty_color, points, width=max(1, int(size * 0.09)))


_line_icon_cache = {}


def _line_icon(kind, size, color):
    """Plain single-colour line icons for the header and power-up cards,
    drawn 4x and scaled down so the edges are smooth."""
    key = (kind, size, color)
    icon = _line_icon_cache.get(key)
    if icon is not None:
        return icon

    scale = 4
    c = size * scale
    big = pygame.Surface((c, c), pygame.SRCALPHA)
    col = color[:3]
    th = max(2, int(c * 0.085))

    def arrow_head(tip, direction, length):
        # A small filled triangle pointing along `direction` (radians).
        a1 = direction + math.radians(150)
        a2 = direction - math.radians(150)
        pts = [tip,
               (tip[0] + length * math.cos(a1), tip[1] + length * math.sin(a1)),
               (tip[0] + length * math.cos(a2), tip[1] + length * math.sin(a2))]
        pygame.draw.polygon(big, col, pts)

    if kind == "timer":
        cx, cy, r = c / 2, c * 0.57, c * 0.34
        pygame.draw.circle(big, col, (int(cx), int(cy)), int(r), th)
        pygame.draw.line(big, col, (int(cx - c * 0.10), int(c * 0.09)), (int(cx + c * 0.10), int(c * 0.09)), th)
        pygame.draw.line(big, col, (int(cx), int(c * 0.09)), (int(cx), int(cy - r)), th)
        pygame.draw.line(big, col, (int(cx), int(cy)), (int(cx), int(cy - r * 0.6)), th)
    elif kind == "shuffle":
        lo, hi = c * 0.30, c * 0.70
        left, right = c * 0.14, c * 0.80
        # two crossing lanes, each ending in an arrow head
        pygame.draw.lines(big, col, False, [(left, hi), (c * 0.40, hi), (c * 0.60, lo), (right, lo)], th)
        pygame.draw.lines(big, col, False, [(left, lo), (c * 0.40, lo), (c * 0.60, hi), (right, hi)], th)
        arrow_head((c * 0.90, lo), 0.0, c * 0.20)
        arrow_head((c * 0.90, hi), 0.0, c * 0.20)
    elif kind == "rotate":
        cx = cy = c / 2
        r = c * 0.32
        start, end = math.radians(-60), math.radians(200)
        pts = []
        steps = 40
        for i in range(steps + 1):
            a = start + (end - start) * i / steps
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pygame.draw.lines(big, col, False, pts, th)
        tip = pts[-1]
        arrow_head(tip, end + math.pi / 2, c * 0.22)

    icon = pygame.transform.smoothscale(big, (size, size))
    _line_icon_cache[key] = icon
    return icon


def draw_timer_icon(screen, center, size, color=None):
    icon = _line_icon("timer", size, color or TEXT)
    screen.blit(icon, icon.get_rect(center=center))


def draw_shuffle_icon(screen, center, size, color=None):
    icon = _line_icon("shuffle", size, color or TEXT)
    screen.blit(icon, icon.get_rect(center=center))


def draw_rotate_icon(screen, center, size, color=None):
    icon = _line_icon("rotate", size, color or TEXT)
    screen.blit(icon, icon.get_rect(center=center))


def draw_icon_button(screen, center, radius, hovered=None, tint=(255, 255, 255, 205), corner_radius=None):
    """The glass button behind the back-arrow / settings icons. By default
    it's a full circle (corner_radius == radius); pass a smaller
    corner_radius to get a rounded square instead.
    """
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = center

    if hovered is None:
        hovered = rect.collidepoint(pygame.mouse.get_pos())

    if corner_radius is None:
        corner_radius = radius

    draw_glass(screen, rect, radius=corner_radius, tint=tint, hovered=hovered)
    return rect


# --------------------------------------------------
# Progress pill (header)
# --------------------------------------------------

def draw_progress_pill(screen, rect, fraction, label, font, label_color=None, radius=None, tint=(255, 255, 255, 205)):
    if radius is None:
        radius = rect.height // 2

    draw_glass(screen, rect, radius=radius, tint=tint)

    label_surface = font.render(label, True, label_color or TEXT)
    label_rect = label_surface.get_rect(midright=(rect.right - 16, rect.centery))
    screen.blit(label_surface, label_rect)

    track_right = label_rect.left - 12
    track_height = 8
    track_rect = pygame.Rect(
        rect.left + 16,
        rect.centery - track_height // 2,
        max(10, track_right - (rect.left + 16)),
        track_height
    )
    draw_smooth_rect(screen, track_rect, TRACK_BACKGROUND, radius=track_height // 2)

    fraction = max(0.0, min(1.0, fraction))
    if fraction > 0:
        fill_width = max(track_height, int(track_rect.width * fraction))
        fill_rect = pygame.Rect(track_rect.left, track_rect.top, fill_width, track_height)
        draw_gradient_rect(
            screen, fill_rect, GRADIENT_PRIMARY[0], GRADIENT_PRIMARY[1],
            border_radius=track_height // 2
        )


# --------------------------------------------------
# Frosted glass panel (pause menu)
# --------------------------------------------------

def draw_frosted_panel(screen, rect, radius=28, blur=14, tint=None):
    """A glassmorphic panel: a blurred sample of whatever is already on
    screen behind it, plus a translucent white wash on top - the same
    cheap downscale/upscale blur trick as draw_blurred_shadow, just
    sampling the live frame instead of a solid colour.
    """
    if tint is None:
        tint = (*WHITE, 150)

    draw_blurred_shadow(
        screen, rect, border_radius=radius, blur=16, alpha=70,
        color=CARD_SHADOW, offset=(0, 14)
    )

    clamped = rect.clip(screen.get_rect())
    if clamped.width > 1 and clamped.height > 1:
        behind = screen.subsurface(clamped).copy()
        small = pygame.transform.smoothscale(
            behind,
            (max(1, clamped.width // blur), max(1, clamped.height // blur))
        )
        blurred = pygame.transform.smoothscale(small, clamped.size)
        mask = get_rounded_mask(clamped.size, radius)
        blurred.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(blurred, clamped.topleft)

    draw_smooth_rect(screen, rect, tint, radius=radius)
    draw_glass_sheen(screen, rect, radius=radius, max_alpha=45)
    draw_smooth_rect(screen, rect, GLASS_BORDER, radius=radius, width=1)


# --------------------------------------------------
# Settings screen widgets
# (sliders, toggles, dropdown, glass buttons)
# --------------------------------------------------

SETTINGS_TRACK = (203, 214, 229)
SETTINGS_MINT = (118, 226, 196)
SETTINGS_SKY = (132, 200, 240)
SETTINGS_BUTTON_TINT = (214, 224, 238, 170)
SETTINGS_PANEL_TINT = (255, 255, 255, 120)


# --------------------------------------------------
# Themes
#
# A handful of named accent palettes. GRADIENT_PRIMARY / NAV_GRADIENT /
# ACCENT_BLUE / SETTINGS_MINT / SETTINGS_SKY are read straight off the
# module (as `ui.GRADIENT_PRIMARY`, etc.) by every draw_* call, never
# captured once and cached - so re-pointing them in apply_theme() below
# re-colors every screen immediately, with nothing else to invalidate.
# --------------------------------------------------

THEMES = {
    "mint": {
        "label": "Mint & Sky",
        "gradient": ((178, 235, 222), (163, 209, 240)),
        "accent": (94, 142, 214),
        "settings_mint": (118, 226, 196),
        "settings_sky": (132, 200, 240),
    },
    "sunset": {
        "label": "Sunset",
        "gradient": ((255, 199, 154), (255, 145, 145)),
        "accent": (224, 112, 112),
        "settings_mint": (255, 189, 140),
        "settings_sky": (255, 148, 148),
    },
    "berry": {
        "label": "Berry",
        "gradient": ((214, 190, 247), (247, 168, 204)),
        "accent": (176, 108, 214),
        "settings_mint": (214, 190, 247),
        "settings_sky": (247, 168, 204),
    },
    "ocean": {
        "label": "Ocean",
        "gradient": ((120, 210, 206), (96, 140, 224)),
        "accent": (66, 118, 200),
        "settings_mint": (120, 210, 206),
        "settings_sky": (96, 140, 224),
    },
}

THEME_ORDER = ["mint", "sunset", "berry", "ocean"]


def apply_theme(name):
    """Swap the app's accent palette (buttons, active nav, sliders and
    toggles). Falls back to "mint" for an unknown/missing name."""
    global GRADIENT_PRIMARY, NAV_GRADIENT, ACCENT_BLUE
    global SETTINGS_MINT, SETTINGS_SKY

    theme = THEMES.get(name, THEMES["mint"])
    GRADIENT_PRIMARY = theme["gradient"]
    NAV_GRADIENT = theme["gradient"]
    ACCENT_BLUE = theme["accent"]
    SETTINGS_MINT = theme["settings_mint"]
    SETTINGS_SKY = theme["settings_sky"]


# --------------------------------------------------
# Light / Dark mode
#
# Separate from apply_theme() above: the accent theme (Mint & Sky,
# Sunset, Berry, Ocean) picks the gradient/highlight color; this picks
# the base surfaces everything else sits on - the page background, card
# and sidebar fills, borders, shadows and text. The two combine freely
# (any accent color works on either background).
#
# Every one of these names is read fresh off the module wherever it's
# used (as `ui.TEXT`, or as a bare `TEXT` in a function body within this
# file) rather than captured once into a default argument - confirmed
# with an AST check across both files before relying on it - so
# reassigning them here re-colors every screen immediately, exactly
# like apply_theme() already does for the accent colors.
# --------------------------------------------------

LIGHT_PALETTE = {
    "BACKGROUND_TOP": (246, 249, 250),
    "BACKGROUND_BOTTOM": (246, 249, 250),
    "TEXT": (38, 36, 40),
    "MUTED_TEXT": (118, 114, 122),
    "SIDEBAR_BACKGROUND": (255, 255, 255, 145),
    "SIDEBAR_BORDER": (255, 255, 255, 90),
    "NAV_ACTIVE_BACKGROUND": (255, 255, 255),
    "NAV_ACTIVE_SHADOW": (214, 205, 214),
    "BOARD_BACKGROUND": (255, 255, 252),
    "BOARD_BORDER": (225, 223, 216),
    "PIECE_AREA_BACKGROUND": (255, 255, 255, 150),
    "PIECE_AREA_BORDER": (255, 255, 255, 110),
    "WHITE": (255, 255, 255),
    "CARD_SHADOW": (150, 165, 195),
    "CONTENT_TOP": (255, 255, 255),
    "CONTENT_BOTTOM": (246, 249, 250),
    "CARD_BACKGROUND": (247, 250, 253),
    "CARD_BORDER": (223, 232, 243),
    "TRACK_BACKGROUND": (246, 249, 250),
    "GLASS_BORDER": (255, 255, 255, 180),
    "HEADER_GLASS_TINT": (255, 255, 255, 90),
    "ACH_ICON_BG": (232, 241, 250),
    "SETTINGS_TRACK": (235, 235, 250),
    "SETTINGS_BUTTON_TINT": (235, 235, 250, 170),
    "SETTINGS_PANEL_TINT": (255, 255, 255, 120),
}

DARK_PALETTE = {
    "BACKGROUND_TOP": (32, 35, 46),
    "BACKGROUND_BOTTOM": (20, 22, 30),
    "TEXT": (235, 236, 240),
    "MUTED_TEXT": (162, 166, 178),
    "SIDEBAR_BACKGROUND": (22, 24, 32, 170),
    "SIDEBAR_BORDER": (255, 255, 255, 35),
    "NAV_ACTIVE_BACKGROUND": (46, 50, 62),
    "NAV_ACTIVE_SHADOW": (10, 10, 14),
    "BOARD_BACKGROUND": (36, 39, 49),
    "BOARD_BORDER": (58, 62, 74),
    "PIECE_AREA_BACKGROUND": (40, 43, 54, 160),
    "PIECE_AREA_BORDER": (255, 255, 255, 35),
    "WHITE": (46, 49, 60),
    "CARD_SHADOW": (8, 9, 14),
    "CONTENT_TOP": (30, 33, 42),
    "CONTENT_BOTTOM": (22, 24, 31),
    "CARD_BACKGROUND": (42, 45, 57),
    "CARD_BORDER": (62, 66, 79),
    "TRACK_BACKGROUND": (54, 58, 71),
    "GLASS_BORDER": (255, 255, 255, 45),
    "HEADER_GLASS_TINT": (28, 30, 38, 120),
    "ACH_ICON_BG": (46, 50, 63),
    "SETTINGS_TRACK": (58, 62, 75),
    "SETTINGS_BUTTON_TINT": (54, 58, 71, 175),
    "SETTINGS_PANEL_TINT": (24, 26, 34, 150),
}

IS_DARK = False


def apply_appearance(dark):
    """Swap every base surface/text color between the light and dark
    palette - everything a card, panel, border or block of text is drawn
    in. Vivid accent colors (the gradients, the difficulty swatches, the
    danger-red of Reset Progress) are untouched, same as apply_theme()
    leaves them for any color theme."""
    global IS_DARK
    IS_DARK = dark
    for key, value in (DARK_PALETTE if dark else LIGHT_PALETTE).items():
        globals()[key] = value


def draw_theme_swatch(screen, rect, theme_key, font, selected=False):
    """One pickable color tile for the Theme settings row. The theme's
    name sits in the middle of the tile."""
    theme = THEMES.get(theme_key, THEMES["mint"])
    hovered = rect.collidepoint(pygame.mouse.get_pos())

    if selected:
        draw_blurred_shadow(
            screen, rect, border_radius=16, blur=10, alpha=110,
            color=theme["settings_mint"], offset=(0, 3)
        )

    draw_gradient_rect(
        screen, rect, theme["gradient"][0], theme["gradient"][1],
        border_radius=16
    )
    draw_glass_sheen(screen, rect, radius=16)

    if selected:
        draw_smooth_rect(screen, rect, (255, 255, 255, 235), radius=16, width=3)
    elif hovered:
        draw_smooth_rect(screen, rect, (255, 255, 255, 140), radius=16, width=2)

    label = font.render(theme["label"], True, (38, 36, 40))
    screen.blit(label, label.get_rect(center=rect.center))


def _blit_midleft(screen, font, text, color, x, center_y):
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(midleft=(x, center_y)))


def _blit_midright(screen, font, text, color, right, center_y):
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(midright=(right, center_y)))


def draw_settings_panel(screen, rect, radius=26):
    """The big frosted card that holds every setting."""
    draw_glass(
        screen, rect, radius=radius,
        tint=SETTINGS_PANEL_TINT, shadow=True
    )


# Warm gradient for the "are you sure?" state of Reset Progress, so a
# destructive button never looks like a normal green "selected" one.
SETTINGS_DANGER = ((255, 190, 160), (246, 140, 150))


def draw_settings_button(
    screen,
    rect,
    text,
    font,
    active=False,
    underline=False,
    text_color=None,
    active_colors=None
):
    """A soft glass button. `active` (= selected) fills it solid with the
    theme's green-blue gradient and a soft glow, like the 'Audio' button
    in the design. `active_colors` can swap in a different (top, bottom)
    color pair. Returns nothing; the caller keeps the rect for click
    detection."""
    hovered = rect.collidepoint(pygame.mouse.get_pos())

    if active:
        color_a, color_b = active_colors or (SETTINGS_MINT, SETTINGS_SKY)
        if hovered:
            color_a = _lerp_color(color_a, (255, 255, 255), 0.12)
            color_b = _lerp_color(color_b, (255, 255, 255), 0.12)

        draw_blurred_shadow(
            screen, rect, border_radius=18, blur=10, alpha=120,
            color=color_a, offset=(0, 4)
        )
        draw_gradient_rect(screen, rect, color_a, color_b, border_radius=16)
        draw_glass_sheen(screen, rect, radius=16)
        draw_smooth_rect(screen, rect, (255, 255, 255, 150), radius=16, width=1)
    else:
        draw_glass(
            screen, rect, radius=16, tint=SETTINGS_BUTTON_TINT,
            hovered=hovered
        )

    label = font.render(text, True, text_color or TEXT)
    label_rect = label.get_rect(center=rect.center)
    screen.blit(label, label_rect)

    if underline:
        y = label_rect.bottom - 2
        pygame.draw.line(
            screen, text_color or TEXT,
            (label_rect.left, y), (label_rect.right, y), 1
        )


def _draw_knob(screen, center, radius):
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = center
    draw_blurred_shadow(
        screen, rect, border_radius=radius, blur=6, alpha=70,
        color=CARD_SHADOW, offset=(0, 3)
    )
    draw_smooth_rect(screen, rect, (255, 255, 255, 255), radius=radius)
    draw_smooth_rect(screen, rect, (206, 219, 235, 255), radius=radius, width=1)


def draw_slider(screen, track_rect, value):
    """Horizontal slider. `track_rect` is the bar itself; value is 0..1.
    The round knob may overhang the ends of the bar by a few pixels."""
    value = max(0.0, min(1.0, value))
    track_h = 10

    track = pygame.Rect(track_rect.left, 0, track_rect.width, track_h)
    track.centery = track_rect.centery
    draw_smooth_rect(screen, track, SETTINGS_TRACK, radius=track_h // 2)

    knob_x = track.left + int(track.width * value)

    if value > 0:
        # Draw the full gradient bar once (it is cached) and just clip
        # it to the filled part, so dragging never builds new surfaces.
        previous_clip = screen.get_clip()
        screen.set_clip(pygame.Rect(track.left, track.top, max(1, knob_x - track.left), track_h))
        draw_gradient_rect(
            screen, track, SETTINGS_MINT, SETTINGS_SKY,
            border_radius=track_h // 2
        )
        screen.set_clip(previous_clip)

    _draw_knob(screen, (knob_x, track.centery), 13)


_toggle_anim = {}


def draw_toggle(screen, rect, on):
    """Pill switch with a sliding knob. The slide is animated, and each
    toggle remembers its own position by where it sits on screen."""
    key = (rect.x, rect.y)
    target = 1.0 if on else 0.0
    position = _toggle_anim.get(key, target)
    position += (target - position) * 0.3
    if abs(target - position) < 0.02:
        position = target
    _toggle_anim[key] = position

    radius = rect.height // 2
    color = _lerp_color(SETTINGS_TRACK, SETTINGS_MINT, position)
    draw_smooth_rect(screen, rect, color, radius=radius)

    knob_radius = radius - 4
    knob_x = rect.left + radius + int((rect.width - radius * 2) * position)
    _draw_knob(screen, (knob_x, rect.centery), knob_radius)


def draw_down_chevron(screen, center, size, color=None):
    icon = pygame.transform.rotate(_build_chevron_icon(size, color or TEXT), 90)
    screen.blit(icon, icon.get_rect(center=center))


def draw_dropdown_field(screen, rect, font, label, value, open=False):
    """The closed dropdown: label on the left, current choice + a small
    arrow on the right."""
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    draw_glass(
        screen, rect, radius=16, tint=SETTINGS_BUTTON_TINT,
        hovered=hovered or open
    )

    _blit_midleft(screen, font, label, TEXT, rect.left + 20, rect.centery)

    arrow_center = (rect.right - 26, rect.centery)
    if open:
        icon = pygame.transform.rotate(_build_chevron_icon(20, TEXT), -90)
        screen.blit(icon, icon.get_rect(center=arrow_center))
    else:
        draw_down_chevron(screen, arrow_center, 20)


def draw_dropdown_options(screen, field_rect, font, options, selected):
    """The list that drops down under the field. Draw it LAST so it sits
    on top of everything. Returns the list of option rects (same order
    as `options`) for click detection."""
    row_height = 44
    panel = pygame.Rect(
        field_rect.left, field_rect.bottom + 8,
        field_rect.width, row_height * len(options) + 16
    )
    draw_glass(screen, panel, radius=16, tint=(*WHITE, 248))

    mouse = pygame.mouse.get_pos()
    rects = []
    for index, option in enumerate(options):
        row = pygame.Rect(
            panel.left + 8, panel.top + 8 + index * row_height,
            panel.width - 16, row_height
        )
        rects.append(row)

        if option == selected:
            draw_smooth_rect(screen, row, (*SETTINGS_MINT, 120), radius=10)
        elif row.collidepoint(mouse):
            draw_smooth_rect(screen, row, (205, 220, 238, 140), radius=10)

        _blit_midleft(screen, font, option, TEXT, row.left + 14, row.centery)

    return panel, rects


# ======================================================================
# WIN SCREEN PATCH - helpers used by the new win screen in main.py
# ======================================================================

def blur_surface(surface, amount):
    """A soft, cheap blur: shrink by `amount`, then scale back up."""
    if amount <= 1:
        return surface

    size = surface.get_size()
    small = pygame.transform.smoothscale(
        surface,
        (max(1, size[0] // amount), max(1, size[1] // amount))
    )
    return pygame.transform.smoothscale(small, size)


_expand_icon_cache = {}


def _build_expand_icon(size, color):
    key = (size, color)
    icon = _expand_icon_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        margin = canvas * 0.16
        arm = canvas * 0.22
        thickness = max(2, int(canvas * 0.09))

        # Four L-shaped brackets, one per corner - the usual
        # "expand to fullscreen" glyph.
        corners = [
            ((margin, margin + arm), (margin, margin), (margin + arm, margin)),
            ((canvas - margin - arm, margin), (canvas - margin, margin), (canvas - margin, margin + arm)),
            ((canvas - margin, canvas - margin - arm), (canvas - margin, canvas - margin), (canvas - margin - arm, canvas - margin)),
            ((margin + arm, canvas - margin), (margin, canvas - margin), (margin, canvas - margin - arm)),
        ]
        for points in corners:
            pygame.draw.lines(big, color, False, points, thickness)

        icon = pygame.transform.smoothscale(big, (size, size))
        _expand_icon_cache[key] = icon

    return icon


def draw_expand_icon(screen, center, size, color=(40, 44, 52)):
    icon = _build_expand_icon(size, color)
    screen.blit(icon, icon.get_rect(center=center))


_close_icon_cache = {}


def _build_close_icon(size, color):
    key = (size, color)
    icon = _close_icon_cache.get(key)

    if icon is None:
        scale = 4
        canvas = size * scale
        big = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
        big.fill((*color[:3], 0))

        pad = canvas * 0.28
        thickness = max(2, int(canvas * 0.09))
        pygame.draw.line(big, color, (pad, pad), (canvas - pad, canvas - pad), thickness)
        pygame.draw.line(big, color, (canvas - pad, pad), (pad, canvas - pad), thickness)

        icon = pygame.transform.smoothscale(big, (size, size))
        _close_icon_cache[key] = icon

    return icon


def draw_close_icon(screen, center, size, color=(255, 255, 255)):
    icon = _build_close_icon(size, color)
    screen.blit(icon, icon.get_rect(center=center))
