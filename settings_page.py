import math

import pygame

import ui


# --------------------------------------------------
# Puzzlescape settings page
# --------------------------------------------------
# The Settings screen, laid out like the design: four frosted cards in
# two columns -
#
#     AUDIO SETTINGS        GRAPHICS & THEME
#     GAMEPLAY SETTINGS     ACCOUNT & SYSTEM
#
# and a BACK button under the left column. The icon dock stays on
# whichever edge it is set to (Settings > Graphics & Theme > Sidebar),
# and the cards fill the space next to it.
#
# This file only DRAWS - it owns no game state. main.py's
# draw_settings_screen() hands it the current settings and a few helpers
# (see draw() below), and gets back the clickable rectangles under the
# same names the click handling in main.py already uses (music_slider,
# tray_buttons, reset_button, ...) - so the click code didn't have to
# change at all.
#
# Anything a reward still locks (dark mode, color themes, the wheel and
# carousel trays, the hint button - see rewards.py) is drawn dimmed with
# a padlock and is deliberately left OUT of the returned rectangles, so
# it can't be clicked; hovering it shows what to do to unlock it.
#
# To add a control: add a row to the card it belongs in (see the
# _build_* functions), draw it, and put its rectangle in `rects` under
# the name main.py's click handling looks for.


CARD_PAD = 28          # space between a card's edge and its content
CARD_RADIUS = 28
TILE_SIZE = 56         # the little rounded icon square in each card's header
CARD_GAP = 24          # vertical gap between the two cards in a column
COLUMN_GAP = 32
LABEL_COLUMN = 190     # width reserved for a row's label, in the Gameplay card
BUTTON_H = 52
TOGGLE_W, TOGGLE_H = 66, 35
SLIDER_H = 24


# --------------------------------------------------
# Layout (pure arithmetic - no drawing)
# --------------------------------------------------

def compute_layout(width, height, dock_rect=None, dock_position="left"):
    """Where every card and the BACK button go. `dock_rect` is the icon
    dock's rectangle (or None) - the cards sit in whatever space is left
    beside it."""
    if dock_rect is None:
        inner_left, inner_right = 60, width - 60
    elif dock_position == "right":
        inner_left, inner_right = 60, dock_rect.left - 40
    else:
        inner_left, inner_right = dock_rect.right + 40, width - 60

    column_w = (inner_right - inner_left - COLUMN_GAP) // 2
    left_x = inner_left
    right_x = inner_left + column_w + COLUMN_GAP

    top = 112
    bottom = height - 112
    total = bottom - top - CARD_GAP           # what two stacked cards share

    audio_h = 250
    graphics_h = 402

    cards = {
        "audio": pygame.Rect(left_x, top, column_w, audio_h),
        "gameplay": pygame.Rect(left_x, top + audio_h + CARD_GAP, column_w, total - audio_h),
        "graphics": pygame.Rect(right_x, top, column_w, graphics_h),
        "account": pygame.Rect(right_x, top + graphics_h + CARD_GAP, column_w, total - graphics_h),
    }
    back = ui.get_page_back_rect(dock_rect, dock_position)

    return {
        "cards": cards,
        "back": back,
        "title_pos": (inner_left, 52),
    }


def _body_area(card):
    """The part of a card below its header, where the rows go."""
    top = card.top + CARD_PAD + TILE_SIZE + 18
    return top, card.bottom - CARD_PAD + 2


def _spread(area_top, area_bottom, heights, min_gap=12, max_gap=34):
    """Top y of each row, spaced evenly through the body area. If there's
    a lot of spare room the rows stay a sensible distance apart and the
    whole group is centred instead of being stretched thin."""
    count = len(heights)
    used = sum(heights)
    room = area_bottom - area_top

    if count > 1:
        gap = (room - used) / (count - 1)
        gap = max(min_gap, min(max_gap, gap))
    else:
        gap = 0

    block = used + gap * (count - 1)
    y = area_top + max(0, (room - block) / 2)

    tops = []
    for height in heights:
        tops.append(round(y))
        y += height + gap
    return tops


# --------------------------------------------------
# Small drawing helpers
# --------------------------------------------------

def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _icon_color():
    """The soft teal-blue the header glyphs use, following the accent
    theme so they change with it."""
    return _mix(ui.SETTINGS_MINT, ui.SETTINGS_SKY, 0.55)


_glyph_cache = {}


def _build_glyph(kind, size, color):
    key = (kind, size, color)
    icon = _glyph_cache.get(key)
    if icon is not None:
        return icon

    scale = 4
    c = size * scale
    big = pygame.Surface((c, c), pygame.SRCALPHA)
    big.fill((*color[:3], 0))

    def P(x, y):
        return (int(c * x), int(c * y))

    if kind == "speaker":
        pygame.draw.polygon(big, color, [
            P(.14, .40), P(.30, .40), P(.48, .22),
            P(.48, .78), P(.30, .60), P(.14, .60),
        ])
        wave_w = max(3, int(c * .055))
        for radius in (.20, .33):
            box = pygame.Rect(0, 0, int(c * radius * 2), int(c * radius * 2))
            box.center = P(.50, .50)
            pygame.draw.arc(big, color, box, -0.75, 0.75, wave_w)

    elif kind == "picture":
        frame = pygame.Rect(P(.14, .18), (int(c * .72), int(c * .64)))
        line = max(3, int(c * .06))
        pygame.draw.rect(big, color, frame, width=line, border_radius=int(c * .10))
        pygame.draw.circle(big, color, P(.68, .38), int(c * .075))
        pygame.draw.polygon(big, color, [P(.22, .72), P(.42, .46), P(.56, .64), P(.64, .55), P(.80, .72)])

    elif kind == "person":
        ring = max(3, int(c * .06))
        pygame.draw.circle(big, color, P(.5, .5), int(c * .40), ring)
        pygame.draw.circle(big, color, P(.5, .40), int(c * .12))

        # Shoulders: an ellipse cut to the ring's circle.
        layer = pygame.Surface((c, c), pygame.SRCALPHA)
        pygame.draw.ellipse(layer, color, pygame.Rect(P(.26, .56), (int(c * .48), int(c * .40))))
        mask = pygame.Surface((c, c), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), P(.5, .5), int(c * .37))
        layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        big.blit(layer, (0, 0))

    icon = pygame.transform.smoothscale(big, (size, size))
    _glyph_cache[key] = icon
    return icon


def _draw_card(screen, card, title, kind, fonts, subtitle=None):
    """The frosted card, its icon tile, and its title. `kind` picks the
    glyph: speaker, picture, piece (the jigsaw icon) or person."""
    ui.draw_settings_panel(screen, card, radius=CARD_RADIUS)

    tile = pygame.Rect(card.left + CARD_PAD, card.top + CARD_PAD, TILE_SIZE, TILE_SIZE)
    ui.draw_glass(screen, tile, radius=16, tint=(*ui.WHITE[:3], 235))

    color = _icon_color()
    if kind == "piece" and hasattr(ui, "draw_piece_icon"):
        ui.draw_piece_icon(screen, tile.center, 30, color)
    else:
        glyph = _build_glyph(kind if kind != "piece" else "picture", 32, color)
        screen.blit(glyph, glyph.get_rect(center=tile.center))

    title_x = tile.right + 18
    if subtitle:
        ui._blit_midleft(screen, fonts["heading"], title, ui.TEXT, title_x, tile.centery - 10)
        ui._blit_midleft(screen, fonts["small"], subtitle, ui.MUTED_TEXT, title_x, tile.centery + 18)
    else:
        ui._blit_midleft(screen, fonts["heading"], title, ui.TEXT, title_x, tile.centery)


def _dim_locked(screen, rect, radius=16):
    """Over a control that's still locked: a frosted veil and a padlock."""
    ui.draw_smooth_rect(screen, rect, (*ui.WHITE[:3], 165), radius=radius)
    if hasattr(ui, "draw_lock_icon"):
        size = max(14, min(24, rect.height - 14))
        ui.draw_lock_icon(screen, rect.center, size, ui.MUTED_TEXT)


def _row_buttons(screen, fonts, area_left, area_right, row_top, height, options, is_selected, on_locked=None, gap=12):
    """A row of equal-width option buttons. `options` is a list of
    (key, label, locked_hint_or_None). Returns ([(key, rect)] for the
    ones that can be clicked, [(rect, hint)] for the locked ones)."""
    count = len(options)
    width = (area_right - area_left - gap * (count - 1)) // count

    clickable, locked = [], []
    for index, (key, label, hint) in enumerate(options):
        rect = pygame.Rect(area_left + index * (width + gap), row_top, width, height)
        ui.draw_settings_button(screen, rect, label, fonts["label"], active=is_selected(key) and hint is None)
        if hint is None:
            clickable.append((key, rect))
        else:
            _dim_locked(screen, rect)
            locked.append((rect, hint))
    return clickable, locked


def _tooltip(screen, font, text, mouse, bounds):
    """A small note next to the mouse - used to say how to unlock
    something."""
    label = font.render(text, True, ui.TEXT)
    box = pygame.Rect(0, 0, label.get_width() + 28, label.get_height() + 18)
    box.midbottom = (mouse[0], mouse[1] - 14)
    box.clamp_ip(bounds.inflate(-16, -16))
    ui.draw_glass(screen, box, radius=12, tint=(*ui.WHITE[:3], 246))
    screen.blit(label, label.get_rect(center=box.center))


# --------------------------------------------------
# The four cards
# --------------------------------------------------

def _build_audio(screen, card, ctx, fonts, rects):
    _draw_card(screen, card, "AUDIO SETTINGS", "speaker", fonts)
    settings = ctx["settings"]

    top, bottom = _body_area(card)
    tops = _spread(top, bottom, [56, 56], min_gap=14)

    left = card.left + CARD_PAD
    right = card.right - CARD_PAD
    slider_w = int((right - left) * 0.62)

    for name, label, top_y in (
        ("music", "Music Volume", tops[0]),
        ("sfx", "SFX Volume", tops[1]),
    ):
        ui._blit_midleft(screen, fonts["label"], label, ui.TEXT, left, top_y + 11)
        track = pygame.Rect(left, top_y + 32, slider_w, SLIDER_H)
        ui.draw_slider(screen, track, settings[name + "_volume"])
        rects[name + "_slider"] = track

    # Mute All sits to the right of the two sliders, level with the
    # first one's label, its switch just below.
    ui._blit_midright(screen, fonts["label"], "Mute All", ui.TEXT, right, tops[0] + 11)
    mute = pygame.Rect(0, 0, TOGGLE_W, TOGGLE_H)
    mute.midright = (right, tops[0] + 32 + SLIDER_H // 2 + 14)
    ui.draw_toggle(screen, mute, settings["mute_all"])
    rects["mute_toggle"] = mute


def _build_gameplay(screen, card, ctx, fonts, rects, tips):
    _draw_card(screen, card, "GAMEPLAY SETTINGS", "piece", fonts)
    settings = ctx["settings"]
    feature = ctx["has_feature"]
    hint_for = ctx["locked_hint"]

    top, bottom = _body_area(card)
    tops = _spread(top, bottom, [BUTTON_H, BUTTON_H, 48, 48])

    left = card.left + CARD_PAD
    right = card.right - CARD_PAD
    buttons_left = left + LABEL_COLUMN

    # Piece Tray: Pile / Wheel / Carousel
    row = tops[0]
    ui._blit_midleft(screen, fonts["label"], "Piece Tray", ui.TEXT, left, row + BUTTON_H // 2)
    options = []
    for style in ctx["tray_styles"]:
        name = "tray_" + style
        hint = None if feature(name) else (hint_for(name) or "Locked")
        options.append((style, ctx["tray_labels"].get(style, style.title()), hint))
    clickable, locked = _row_buttons(
        screen, fonts, buttons_left, right, row, BUTTON_H, options,
        lambda key: settings["tray_style"] == key
    )
    rects["tray_buttons"] = clickable
    tips.extend(locked)

    # Puzzle Header: Classic / Minimal
    row = tops[1]
    ui._blit_midleft(screen, fonts["label"], "Puzzle Header", ui.TEXT, left, row + BUTTON_H // 2)
    options = []
    for style in ctx["header_styles"]:
        hint = None
        if style != "classic" and not feature("minimal_header"):
            hint = hint_for("minimal_header") or "Locked"
        options.append((style, ctx["header_labels"].get(style, style.title()), hint))
    clickable, _ = _row_buttons(
        screen, fonts, buttons_left, right, row, BUTTON_H, options,
        lambda key: settings["header_style"] == key
    )
    rects["header_style_buttons"] = clickable

    # Show Hint Button
    row = tops[2]
    ui._blit_midleft(screen, fonts["label"], "Show Hint Button", ui.TEXT, left, row + 24)
    hint_toggle = pygame.Rect(0, 0, TOGGLE_W, TOGGLE_H)
    hint_toggle.midright = (right, row + 24)
    hint_unlocked = feature("hint_button")
    ui.draw_toggle(screen, hint_toggle, settings["show_hint"] and hint_unlocked)
    if hint_unlocked:
        rects["hint_toggle"] = hint_toggle
    else:
        _dim_locked(screen, hint_toggle, radius=hint_toggle.height // 2)
        tips.append((hint_toggle, hint_for("hint_button") or "Locked"))

    # Board Opacity: how visible the faint picture behind the board is
    row = tops[3]
    ui._blit_midleft(screen, fonts["label"], "Board Opacity", ui.TEXT, left, row + 24)
    percent_w = fonts["label"].size("100%")[0]
    track = pygame.Rect(buttons_left, row + 24 - SLIDER_H // 2, right - percent_w - 18 - buttons_left, SLIDER_H)
    if feature("board_opacity"):
        ui.draw_slider(screen, track, settings["board_opacity"])
        rects["board_opacity_slider"] = track
        percent = f"{round(settings['board_opacity'] * 100)}%"
        ui._blit_midright(screen, fonts["label"], percent, ui.MUTED_TEXT, right, row + 24)
    else:
        _dim_locked(screen, track, radius=5)
        ui._blit_midright(screen, fonts["label"], "LOCKED", ui.MUTED_TEXT, right, row + 24)
        tips.append((track, hint_for("board_opacity") or "Locked"))


def _build_graphics(screen, card, ctx, fonts, rects, tips):
    _draw_card(screen, card, "GRAPHICS & THEME", "picture", fonts)
    settings = ctx["settings"]
    feature = ctx["has_feature"]
    hint_for = ctx["locked_hint"]

    top, bottom = _body_area(card)
    tops = _spread(top, bottom, [BUTTON_H, 48, BUTTON_H, BUTTON_H])

    left = card.left + CARD_PAD
    right = card.right - CARD_PAD
    half = (right - left) // 2 - 10

    def switch_row(center_y, left_label, left_key, left_value, right_label, right_key, right_value, right_unlocked=True):
        """Two 'label + switch' pairs on one row: the left pair ends at
        the middle of the card, the right pair at its right edge."""
        if left_label:
            ui._blit_midleft(screen, fonts["label"], left_label, ui.TEXT, left, center_y)
            box = pygame.Rect(0, 0, TOGGLE_W, TOGGLE_H)
            box.midright = (left + half, center_y)
            ui.draw_toggle(screen, box, left_value)
            rects[left_key] = box

        box = pygame.Rect(0, 0, TOGGLE_W, TOGGLE_H)
        box.midright = (right, center_y)
        ui._blit_midright(screen, fonts["label"], right_label, ui.TEXT, box.left - 14, center_y)
        ui.draw_toggle(screen, box, right_value)
        if right_unlocked:
            rects[right_key] = box
        else:
            _dim_locked(screen, box, radius=box.height // 2)
            tips.append((box, hint_for("dark_mode") or "Locked"))

    # Row 1: Resolution (drawn last, so its list can float on top) | Quality
    row = tops[0]
    resolution = pygame.Rect(left, row, half, BUTTON_H)
    rects["resolution_dropdown"] = resolution
    center_y = row + BUTTON_H // 2
    box = pygame.Rect(0, 0, TOGGLE_W, TOGGLE_H)
    box.midright = (right, center_y)
    ui._blit_midright(screen, fonts["label"], "Quality", ui.TEXT, box.left - 14, center_y)
    ui.draw_toggle(screen, box, settings["quality"])
    rects["quality_toggle"] = box

    # Row 2: Fullscreen | Dark Mode
    dark_unlocked = feature("dark_mode")
    switch_row(
        tops[1] + 24,
        "Fullscreen", "fullscreen_toggle", settings["fullscreen"],
        "Dark Mode", "darkmode_toggle", settings["dark_mode"] and dark_unlocked,
        right_unlocked=dark_unlocked
    )

    # Row 3: the four color themes
    row = tops[2]
    theme_order = list(getattr(ui, "THEME_ORDER", []))
    swatch_gap = 14
    count = max(1, len(theme_order))
    swatch_w = (right - left - swatch_gap * (count - 1)) // count
    themes_unlocked = feature("color_themes")

    swatches = []
    for index, theme_key in enumerate(theme_order):
        rect = pygame.Rect(left + index * (swatch_w + swatch_gap), row, swatch_w, BUTTON_H)
        is_default = index == 0
        ui.draw_theme_swatch(
            screen, rect, theme_key, fonts["label"],
            selected=(settings["theme"] == theme_key)
        )
        if is_default or themes_unlocked:
            swatches.append((theme_key, rect))
        else:
            _dim_locked(screen, rect)
            tips.append((rect, hint_for("color_themes") or "Locked"))
    rects["theme_swatches"] = swatches

    # Row 4: which edge the icon dock sits on
    row = tops[3]
    ui._blit_midleft(screen, fonts["label"], "Sidebar", ui.TEXT, left, row + BUTTON_H // 2)
    options = [
        (position, ctx["position_labels"].get(position, position.title()), None)
        for position in ctx["sidebar_positions"]
    ]
    clickable, _ = _row_buttons(
        screen, fonts, left + LABEL_COLUMN - 40, right, row, BUTTON_H, options,
        lambda key: settings["sidebar_position"] == key
    )
    rects["sidebar_position_buttons"] = clickable


def _build_account(screen, card, ctx, fonts, rects):
    name = ctx.get("player_name")
    coins = ctx.get("coins")
    subtitle = None
    if ctx.get("profile_name_editing"):
        subtitle = f"Editing: {name or 'type a name'}  ·  press Enter to save"
    elif name and coins is not None:
        subtitle = f"{name}  \u00b7  {coins} coins"
    elif name:
        subtitle = name
    elif coins is not None:
        subtitle = f"{coins} coins"

    _draw_card(screen, card, "ACCOUNT & SYSTEM", "person", fonts, subtitle=subtitle)

    top, bottom = _body_area(card)
    rows = _spread(top, bottom, [52, 52])

    left = card.left + CARD_PAD
    right = card.right - CARD_PAD
    gap = 16
    width = (right - left - gap) // 2

    name_button = pygame.Rect(left, rows[0], right - left, 52)
    ui.draw_settings_button(
        screen, name_button, "Set the Name", fonts["label"], underline=True
    )
    rects["profile_name_button"] = name_button

    row = rows[1]
    reset = pygame.Rect(left, row, width, 52)
    if ctx["reset_flash"]:
        reset_label = "Progress reset"
    elif ctx["reset_armed"]:
        reset_label = "Tap again to confirm"
    else:
        reset_label = "Reset Progress"
    ui.draw_settings_button(
        screen, reset, reset_label, fonts["label"],
        active=ctx["reset_armed"], active_colors=getattr(ui, "SETTINGS_DANGER", None)
    )
    rects["reset_button"] = reset

    picture = pygame.Rect(left + width + gap, row, width, 52)
    ui.draw_settings_button(
        screen, picture, "Set the Profile Picture", fonts["label"], underline=True
    )
    rects["profile_picture_button"] = picture



# --------------------------------------------------
# The page
# --------------------------------------------------

def _fallback_back(screen, rect, fonts):
    ui.draw_blurred_shadow(
        screen, rect, border_radius=20, blur=12, alpha=60,
        color=(120, 140, 200), offset=(0, 6)
    )
    ui.draw_gradient_rect(
        screen, rect, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=20
    )
    label = fonts["button"].render("BACK", True, ui.TEXT)
    screen.blit(label, label.get_rect(center=rect.center))


def draw(screen, ctx):
    """Draws the whole Settings page. Returns (rects, dropdown_rects):
    `rects` are the clickable areas (same names main.py's click handling
    already uses), `dropdown_rects` the resolution list's option
    rectangles while it's open.

    ctx (all supplied by main.py's draw_settings_screen):
        settings, fonts (title/heading/label/small/button), the option
        lists and labels (tray_styles, tray_labels, header_styles,
        header_labels, sidebar_positions, position_labels),
        available_resolutions(), resolution_label(key), has_feature(name),
        locked_hint(name), reset_armed, reset_flash, show_version,
        version, dropdown_open, player_name, coins, draw_back(rect)."""
    settings = ctx["settings"]
    fonts = ctx["fonts"]

    try:
        dock = ui.get_dock_rect(settings["sidebar_position"])
    except (AttributeError, TypeError):
        dock = None
    layout = compute_layout(ui.WIDTH, ui.HEIGHT, dock, settings["sidebar_position"])
    cards = layout["cards"]

    ui.draw_text(
        screen, "SETTINGS", fonts["title"], ui.TEXT,
        layout["title_pos"][0], layout["title_pos"][1], center=False
    )

    rects = {}
    tips = []          # (rect, text) for locked controls, shown on hover

    _build_audio(screen, cards["audio"], ctx, fonts, rects)
    _build_gameplay(screen, cards["gameplay"], ctx, fonts, rects, tips)
    _build_graphics(screen, cards["graphics"], ctx, fonts, rects, tips)
    _build_account(screen, cards["account"], ctx, fonts, rects)

    back = layout["back"]
    if ctx.get("draw_back"):
        ctx["draw_back"](back)
    else:
        ui.draw_page_back_button(screen, back, fonts["button"])
    rects["back_button"] = back

    # The Resolution field and its list go last so the list floats over
    # the rows beneath it.
    resolution = rects["resolution_dropdown"]
    ui.draw_dropdown_field(screen, resolution, fonts["label"], "", "", open=ctx["dropdown_open"])
    ui._blit_midleft(
        screen, fonts["label"], settings["resolution"], ui.TEXT,
        resolution.left + 20, resolution.centery
    )

    dropdown_rects = []
    if ctx["dropdown_open"]:
        list_rect = resolution.copy()
        list_rect.width = max(list_rect.width, 290)
        _, dropdown_rects = ui.draw_dropdown_options(
            screen, list_rect, fonts["button"],
            [ctx["resolution_label"](key) for key in ctx["available_resolutions"]()],
            ctx["resolution_label"](settings["resolution"])
        )
    else:
        mouse = pygame.mouse.get_pos()
        for rect, text in tips:
            if rect.collidepoint(mouse):
                _tooltip(screen, fonts["small"], text, mouse, screen.get_rect())
                break

    return rects, dropdown_rects
