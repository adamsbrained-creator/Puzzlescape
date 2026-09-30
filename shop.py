try:
    import pygame
except ModuleNotFoundError:  # pragma: no cover - pygame is required at runtime
    pygame = None


SHOP_ITEMS = [
    {"key": "sunset", "title": "Sunset Glow", "description": "Warm coral skies and golden accents.", "cost": 80, "accent": (255, 175, 118)},
    {"key": "berry", "title": "Berry Pop", "description": "Violet tones with a candy-bright finish.", "cost": 120, "accent": (176, 108, 214)},
    {"key": "ocean", "title": "Oceanic", "description": "Cool blues for a calm, modern look.", "cost": 140, "accent": (96, 140, 224)},
    {"key": "mint", "title": "Mint & Sky", "description": "The default pastel theme, always ready.", "cost": 0, "accent": (118, 226, 196)},
]
SHOP_TABS = (
    ("themes", "THEMES"),
    ("wallpapers", "WALLPAPERS"),
    ("powerups", "POWER-UPS"),
    ("levels", "LEVELS"),
    ("bundles", "BUNDLES"),
)
SHOP_BUNDLE = {
    "key": "theme_bundle",
    "title": "COLOR THEME BUNDLE",
    "description": "Own every color theme and save 40 coins.",
    "cost": 300,
}
LEVEL_PACKS = (
    {"key": "space", "label": "Space", "description": "Planets, stars, and distant worlds.", "cost": 100, "icon": "moon", "accent": (83, 117, 184)},
    {"key": "gravity_falls", "label": "Gravity Falls", "description": "Mysterious forests and strange discoveries.", "cost": 100, "icon": "mountain", "accent": (102, 145, 111)},
    {"key": "flowers", "label": "Flowers", "description": "Bright blooms from gardens and fields.", "cost": 100, "icon": "palette", "accent": (218, 129, 165)},
    {"key": "games", "label": "Games", "description": "Scenes from playful worlds and adventures.", "cost": 100, "icon": "puzzle", "accent": (124, 123, 210)},
    {"key": "landscapes", "label": "Landscapes", "description": "Wide views, mountains, and open skies.", "cost": 100, "icon": "mountain", "accent": (106, 157, 173)},
    {"key": "cities", "label": "Cities", "description": "Streets, skylines, and city landmarks.", "cost": 100, "icon": "wheel", "accent": (102, 132, 192)},
    {"key": "art", "label": "Art", "description": "Color, shapes, and works of art.", "cost": 100, "icon": "palette", "accent": (194, 124, 201)},
    {"key": "ocean_underwater", "label": "Ocean & Underwater", "description": "Ocean life beneath the waves.", "cost": 100, "icon": "gem", "accent": (68, 165, 190)},
    {"key": "entertainment", "label": "Entertainment", "description": "Stages, screens, and special events.", "cost": 100, "icon": "trophy", "accent": (223, 165, 78)},
    {"key": "time", "label": "Time", "description": "Clocks, calendars, and moments in time.", "cost": 100, "icon": "stopwatch", "accent": (108, 160, 191)},
    {"key": "hannibal", "label": "Hannibal", "description": "A collection inspired by Hannibal.", "cost": 100, "icon": "medal", "accent": (172, 92, 105)},
    {"key": "autumn", "label": "Autumn", "description": "Fall colors, leaves, and cooler days.", "cost": 100, "icon": "gem", "accent": (202, 132, 77)},
)
LEVELS_PER_PACK = 10
POWERUP_PREVIEWS = (
    ("HINT BOOSTER", "Reveal a piece on the puzzle board.", "bulb"),
    ("TIME FREEZE", "Pause the timer during a tricky puzzle.", "timer"),
    ("SHUFFLE PACK", "More ways to organize your loose pieces.", "shuffle"),
)

rects = {}
active_tab = "themes"
wallpaper_scroll = 0
SHOP_ZOOM = 0.9


def _shop_size(value):
    return max(1, round(value * SHOP_ZOOM))


def get_item(item_key):
    return next((item for item in SHOP_ITEMS if item["key"] == item_key), None)


def _ensure_inventory(data):
    if not isinstance(data.get("shop"), dict):
        data["shop"] = {}
    if not isinstance(data["shop"].get("owned"), dict):
        data["shop"]["owned"] = {}
    return data["shop"]["owned"]


def is_owned(data, item_key):
    if item_key == "mint":
        return True
    return item_key in _ensure_inventory(data)


def purchase_item(data, item_key):
    item = get_item(item_key)
    if item is None or item_key == "mint" or is_owned(data, item_key):
        return False
    if data.get("coins", 0) < item["cost"]:
        return False

    data["coins"] -= item["cost"]
    _ensure_inventory(data)[item_key] = True
    return True


def purchase_bundle(data, bundle_key="theme_bundle"):
    if bundle_key != SHOP_BUNDLE["key"] or is_owned(data, bundle_key):
        return False
    if data.get("coins", 0) < SHOP_BUNDLE["cost"]:
        return False

    data["coins"] -= SHOP_BUNDLE["cost"]
    owned = _ensure_inventory(data)
    owned[bundle_key] = True
    for item in SHOP_ITEMS:
        if item["key"] != "mint":
            owned[item["key"]] = True
    return True


def get_level_pack(pack_key):
    return next((pack for pack in LEVEL_PACKS if pack["key"] == pack_key), None)


def is_level_pack_owned(data, pack_key):
    return bool(_ensure_inventory(data).get(pack_key))


def purchase_level_pack(data, pack_key):
    pack = get_level_pack(pack_key)
    if pack is None or is_level_pack_owned(data, pack_key):
        return False
    if data.get("coins", 0) < pack["cost"]:
        return False

    data["coins"] -= pack["cost"]
    _ensure_inventory(data)[pack_key] = True
    return True


def set_tab(tab):
    global active_tab, wallpaper_scroll
    if tab in {key for key, _label in SHOP_TABS}:
        active_tab = tab
        wallpaper_scroll = 0


def scroll_by(delta):
    global wallpaper_scroll
    wallpaper_scroll = max(0, wallpaper_scroll + int(delta))


def compute_layout(content, ui_module=None):
    if ui_module is None:
        import ui as ui_module

    margin = _shop_size(68)
    back = ui_module.get_page_back_rect()
    header = pygame.Rect(content.left + margin, content.top + _shop_size(28), content.width - margin * 2, _shop_size(48))
    wallet = pygame.Rect(content.right - margin - _shop_size(218), content.top + _shop_size(28), _shop_size(218), _shop_size(48))
    tabs = pygame.Rect(content.left + margin, content.top + _shop_size(96), content.width - margin * 2, _shop_size(64))
    body_top = tabs.bottom + _shop_size(22)
    body_bottom = min(back.top - _shop_size(28), content.bottom - _shop_size(28))
    body = pygame.Rect(content.left + margin, body_top, content.width - margin * 2, max(1, body_bottom - body_top))

    tab_gap = _shop_size(8)
    tab_width = (tabs.width - tab_gap * (len(SHOP_TABS) - 1)) // len(SHOP_TABS)
    tab_rects = {
        key: pygame.Rect(tabs.left + index * (tab_width + tab_gap), tabs.top, tab_width, tabs.height)
        for index, (key, _label) in enumerate(SHOP_TABS)
    }

    columns = 4
    card_gap = _shop_size(16)
    card_width = (body.width - card_gap * (columns - 1)) // columns
    theme_card_height = max(_shop_size(250), body.height - _shop_size(106))
    theme_cards = {
        item["key"]: pygame.Rect(body.left + index * (card_width + card_gap), body.top, card_width, theme_card_height)
        for index, item in enumerate(SHOP_ITEMS)
    }
    bundle = pygame.Rect(body.left, body.bottom - _shop_size(88), body.width, _shop_size(88))
    return {
        "header": header,
        "wallet": wallet,
        "tabs": tabs,
        "tab_rects": tab_rects,
        "body": body,
        "theme_cards": theme_cards,
        "bundle": bundle,
        "back": back,
        "card_width": card_width,
    }


def _draw_card(screen, ui, rect, hovered=False, selected=False):
    ui.draw_blurred_shadow(
        screen, rect, border_radius=22, blur=12,
        alpha=55 if hovered else 36, color=ui.CARD_SHADOW,
        offset=(0, 6 if hovered else 4),
    )
    ui.draw_smooth_rect(screen, rect, (*ui.CARD_BACKGROUND, 255), radius=22)
    border = ui.GRADIENT_PRIMARY[0] if selected else ui.CARD_BORDER
    ui.draw_smooth_rect(screen, rect, (*border, 255), radius=22, width=2 if selected else 1)


def _draw_button(screen, ui, rect, label, font, primary=False, disabled=False):
    hovered = rect.collidepoint(pygame.mouse.get_pos()) and not disabled
    if primary and not disabled:
        ui.draw_gradient_rect(screen, rect, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=14)
        text_color = ui.TEXT
    else:
        fill = ui.TRACK_BACKGROUND if hovered else ui.WHITE
        ui.draw_smooth_rect(screen, rect, (*fill, 255), radius=14)
        ui.draw_smooth_rect(screen, rect, (*ui.CARD_BORDER, 255), radius=14, width=1)
        text_color = ui.MUTED_TEXT if disabled else ui.TEXT
    ui.draw_text(screen, label, font, text_color, rect.centerx, rect.centery)


def _preview(screen, ui, rect, level, catalog, accent):
    image = None
    loader = catalog.get("load_thumbnail")
    if level and loader:
        try:
            image = loader(level["image"])
        except (KeyError, OSError, pygame.error):
            image = None
    if image is None:
        ui.draw_gradient_rect(screen, rect, accent, ui.GRADIENT_PRIMARY[1], border_radius=16)
        ui.draw_piece_icon(screen, rect.center, min(72, rect.height // 2), (*ui.WHITE, 220))
    else:
        ui.draw_image_rounded(screen, image, rect, radius=16)


def _wrapped_lines(font, text, width):
    lines = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and font.size(candidate)[0] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _draw_tab_bar(screen, ui, layout, font):
    rects["tabs"] = {}
    for key, label in SHOP_TABS:
        rect = layout["tab_rects"][key]
        selected = key == active_tab
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        fill = ui.WHITE if selected or hovered else ui.CARD_BACKGROUND
        ui.draw_smooth_rect(screen, rect, (*fill, 245), radius=18)
        if selected:
            underline = pygame.Rect(rect.left + 24, rect.bottom - 5, rect.width - 48, 4)
            ui.draw_gradient_rect(screen, underline, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=2)
        ui.draw_text(screen, label, font, ui.TEXT if selected else ui.MUTED_TEXT, rect.centerx, rect.centery)
        rects["tabs"][key] = rect


def _theme_level(item, catalog):
    preferred = {"sunset": "nature", "berry": "art", "ocean": "world", "mint": "architecture"}.get(item["key"])
    return next((level for level in catalog.get("levels", []) if level.get("category") == preferred), None)


def _draw_themes(screen, ui, layout, fonts, save_data, current_theme, catalog):
    mouse = pygame.mouse.get_pos()
    for item in SHOP_ITEMS:
        card = layout["theme_cards"][item["key"]]
        _draw_card(screen, ui, card, card.collidepoint(mouse), selected=current_theme == item["key"])
        image_rect = pygame.Rect(card.left + _shop_size(12), card.top + _shop_size(12), card.width - _shop_size(24), _shop_size(172))
        _preview(screen, ui, image_rect, _theme_level(item, catalog), catalog, item["accent"])

        owned = is_owned(save_data, item["key"])
        selected = current_theme == item["key"]
        title_y = image_rect.bottom + _shop_size(30)
        ui.draw_text(screen, item["title"], fonts["heading"], ui.TEXT, card.left + _shop_size(22), title_y, center=False)
        for index, line in enumerate(_wrapped_lines(fonts["small"], item["description"], card.width - 44)[:2]):
            ui.draw_text(screen, line, fonts["small"], ui.MUTED_TEXT, card.left + _shop_size(22), title_y + _shop_size(30) + index * _shop_size(20), center=False)

        price = pygame.Rect(card.left + _shop_size(22), card.bottom - _shop_size(62), card.width // 2, _shop_size(42))
        ui.draw_text(screen, "FREE" if item["cost"] == 0 else f"{item['cost']} COINS", fonts["button"], ui.TEXT, price.left, price.centery, center=False)
        action = pygame.Rect(card.right - _shop_size(142), price.top, _shop_size(120), price.height)
        _draw_button(screen, ui, action, "ACTIVE" if selected else ("OWNED" if owned else "BUY"), fonts["button"], primary=selected or not owned)
        rects[f"theme:{item['key']}"] = action

    bundle_rect = layout["bundle"]
    ui.draw_blurred_shadow(screen, bundle_rect, border_radius=20, blur=10, alpha=35, color=ui.CARD_SHADOW, offset=(0, 4))
    ui.draw_smooth_rect(screen, bundle_rect, (*ui.CARD_BACKGROUND, 255), radius=20)
    ui.draw_smooth_rect(screen, bundle_rect, (*ui.CARD_BORDER, 255), radius=20, width=1)
    for index, item in enumerate(SHOP_ITEMS[:3]):
        swatch = pygame.Rect(bundle_rect.left + _shop_size(16) + index * _shop_size(58), bundle_rect.top + _shop_size(14), _shop_size(48), _shop_size(60))
        ui.draw_gradient_rect(screen, swatch, item["accent"], ui.GRADIENT_PRIMARY[1], border_radius=10)
    ui.draw_text(screen, "SPECIAL BUNDLE", fonts["heading"], ui.TEXT, bundle_rect.left + 202, bundle_rect.top + 24, center=False)
    ui.draw_text(screen, SHOP_BUNDLE["description"], fonts["small"], ui.MUTED_TEXT, bundle_rect.left + 202, bundle_rect.top + 58, center=False)
    ui.draw_text(screen, f"{SHOP_BUNDLE['cost']} COINS", fonts["button"], ui.TEXT, bundle_rect.right - 320, bundle_rect.centery)
    action = pygame.Rect(bundle_rect.right - 142, bundle_rect.top + 20, 120, 48)
    bundle_owned = is_owned(save_data, SHOP_BUNDLE["key"])
    _draw_button(screen, ui, action, "OWNED" if bundle_owned else "VIEW", fonts["button"], primary=not bundle_owned)
    rects["bundle:theme_bundle"] = None if bundle_owned else action


def _draw_wallpapers(screen, ui, layout, fonts, save_data, catalog):
    global wallpaper_scroll
    levels = [level for level in catalog.get("levels", []) if save_data.get("levels", {}).get(level.get("name"), {}).get("completed")]
    body = layout["body"]
    columns, gap, card_height, row_gap = 4, _shop_size(16), _shop_size(236), _shop_size(18)
    card_width = (body.width - gap * (columns - 1)) // columns
    rows = (len(levels) + columns - 1) // columns
    total_height = rows * card_height + max(0, rows - 1) * row_gap
    max_scroll = max(0, total_height - body.height)
    wallpaper_scroll = min(wallpaper_scroll, max_scroll)

    previous_clip = screen.get_clip()
    screen.set_clip(body)
    for index, level in enumerate(levels):
        col, row = index % columns, index // columns
        card = pygame.Rect(body.left + col * (card_width + gap), body.top + row * (card_height + row_gap) - wallpaper_scroll, card_width, card_height)
        active = catalog.get("wallpaper") == level["name"]
        _draw_card(screen, ui, card, card.collidepoint(pygame.mouse.get_pos()), selected=active)
        image_rect = pygame.Rect(card.left + _shop_size(10), card.top + _shop_size(10), card.width - _shop_size(20), _shop_size(142))
        _preview(screen, ui, image_rect, level, catalog, ui.ACCENT_BLUE)
        ui.draw_text(screen, level["name"], fonts["heading"], ui.TEXT, card.left + _shop_size(18), image_rect.bottom + _shop_size(26), center=False)
        action = pygame.Rect(card.left + _shop_size(14), card.bottom - _shop_size(48), card.width - _shop_size(28), _shop_size(34))
        _draw_button(screen, ui, action, "ACTIVE" if active else "USE WALLPAPER", fonts["small"], primary=active)
        rects[f"wallpaper:{level['name']}"] = action
    screen.set_clip(previous_clip)

    if not levels:
        ui.draw_text(screen, "Complete a puzzle to unlock its wallpaper.", fonts["heading"], ui.MUTED_TEXT, body.centerx, body.centery)
    if max_scroll:
        track = pygame.Rect(body.right - 6, body.top, 5, body.height)
        thumb_height = max(44, int(body.height * body.height / total_height))
        thumb_y = body.top + int((body.height - thumb_height) * wallpaper_scroll / max_scroll)
        ui.draw_smooth_rect(screen, track, ui.TRACK_BACKGROUND, radius=3)
        ui.draw_smooth_rect(screen, pygame.Rect(track.left, thumb_y, track.width, thumb_height), ui.MUTED_TEXT, radius=3)


def _draw_powerups(screen, ui, layout, fonts):
    body = layout["body"]
    gap, columns = _shop_size(20), 3
    card_width = (body.width - gap * (columns - 1)) // columns
    card_height = min(_shop_size(300), body.height - _shop_size(8))
    for index, (title, description, icon) in enumerate(POWERUP_PREVIEWS):
        card = pygame.Rect(body.left + index * (card_width + gap), body.top, card_width, card_height)
        _draw_card(screen, ui, card)
        tile = pygame.Rect(card.left + _shop_size(22), card.top + _shop_size(22), _shop_size(72), _shop_size(72))
        ui.draw_smooth_rect(screen, tile, (*ui.WHITE, 255), radius=18)
        if icon == "bulb":
            ui.draw_lightbulb_icon(screen, tile.center, 38, ui.ACCENT_BLUE)
        elif icon == "timer":
            ui.draw_timer_icon(screen, tile.center, 38, ui.ACCENT_BLUE)
        else:
            ui.draw_shuffle_icon(screen, tile.center, 38, ui.ACCENT_BLUE)
        ui.draw_text(screen, title, fonts["heading"], ui.TEXT, card.left + _shop_size(22), card.top + _shop_size(132), center=False)
        for line_index, line in enumerate(_wrapped_lines(fonts["small"], description, card.width - 44)[:2]):
            ui.draw_text(screen, line, fonts["small"], ui.MUTED_TEXT, card.left + _shop_size(22), card.top + _shop_size(166) + line_index * _shop_size(20), center=False)
        _draw_button(screen, ui, pygame.Rect(card.left + _shop_size(22), card.bottom - _shop_size(62), card.width - _shop_size(44), _shop_size(42)), "COMING SOON", fonts["small"], disabled=True)


def _draw_levels(screen, ui, layout, fonts, save_data, catalog):
    body = layout["body"]
    columns, gap = 3, _shop_size(18)
    card_width = (body.width - gap * (columns - 1)) // columns
    card_height = min(_shop_size(168), (body.height - gap * 3) // 4)
    coin_count = save_data.get("coins", 0)
    has_image = catalog.get("has_image", lambda _path: True)

    for index, pack in enumerate(LEVEL_PACKS):
        col, row = index % columns, index // columns
        card = pygame.Rect(body.left + col * (card_width + gap), body.top + row * (card_height + gap), card_width, card_height)
        levels = [level for level in catalog.get("levels", []) if level.get("category") == pack["key"]]
        completed = sum(save_data.get("levels", {}).get(level["name"], {}).get("completed", False) for level in levels)
        owned = is_level_pack_owned(save_data, pack["key"])
        _draw_card(screen, ui, card, card.collidepoint(pygame.mouse.get_pos()), selected=owned)
        preview_rect = pygame.Rect(card.left + _shop_size(10), card.top + _shop_size(10), _shop_size(112), card.height - _shop_size(20))
        has_pack_image = bool(levels and has_image(levels[0]["image"]))
        if has_pack_image:
            _preview(screen, ui, preview_rect, levels[0], catalog, pack["accent"])
        else:
            ui.draw_gradient_rect(screen, preview_rect, pack["accent"], ui.GRADIENT_PRIMARY[1], border_radius=16)
            ui.draw_achievement_icon(screen, pack["icon"], preview_rect.center, min(72, preview_rect.height - 20))

        text_left = preview_rect.right + _shop_size(16)
        ui.draw_text(screen, f"{pack['label']} PACK", fonts["heading"], ui.TEXT, text_left, card.top + _shop_size(40), center=False)
        detail = f"{completed}/{len(levels)} completed" if owned else f"{LEVELS_PER_PACK} puzzles - {pack['cost']} coins"
        ui.draw_text(screen, detail, fonts["small"], ui.MUTED_TEXT, text_left, card.top + _shop_size(76), center=False)
        action = pygame.Rect(card.right - _shop_size(112), card.bottom - _shop_size(50), _shop_size(96), _shop_size(34))
        can_afford = coin_count >= pack["cost"]
        label = "OPEN" if owned else (f"BUY {pack['cost']}" if can_afford else "NEED COINS")
        _draw_button(screen, ui, action, label, fonts["small"], primary=owned or can_afford, disabled=not owned and not can_afford)
        rects[f"level:{pack['key']}"] = action


def _draw_bundles(screen, ui, layout, fonts, save_data, catalog):
    body = layout["body"]
    card = pygame.Rect(body.left, body.top, body.width, min(_shop_size(380), body.height))
    _draw_card(screen, ui, card, card.collidepoint(pygame.mouse.get_pos()))
    preview = pygame.Rect(card.left + _shop_size(18), card.top + _shop_size(18), min(_shop_size(520), card.width // 2), card.height - _shop_size(36))
    _preview(screen, ui, preview, _theme_level(SHOP_ITEMS[2], catalog), catalog, SHOP_ITEMS[2]["accent"])
    text_left = preview.right + _shop_size(34)
    ui.draw_text(screen, SHOP_BUNDLE["title"], fonts["title"], ui.TEXT, text_left, card.top + _shop_size(64), center=False)
    ui.draw_text(screen, SHOP_BUNDLE["description"], fonts["heading"], ui.MUTED_TEXT, text_left, card.top + _shop_size(114), center=False)
    ui.draw_text(screen, "Includes Sunset, Berry, and Ocean themes.", fonts["small"], ui.MUTED_TEXT, text_left, card.top + _shop_size(154), center=False)
    ui.draw_text(screen, f"{SHOP_BUNDLE['cost']} COINS", fonts["heading"], ui.TEXT, text_left, card.bottom - _shop_size(58), center=False)
    action = pygame.Rect(card.right - _shop_size(172), card.bottom - _shop_size(82), _shop_size(148), _shop_size(50))
    owned = is_owned(save_data, SHOP_BUNDLE["key"])
    _draw_button(screen, ui, action, "OWNED" if owned else "BUY BUNDLE", fonts["button"], primary=not owned)
    rects["bundle:theme_bundle"] = None if owned else action


def draw(screen, ui, content, fonts=None, save_data=None, current_theme=None, mouse_pos=None, catalog=None):
    fonts = dict(fonts or {})
    save_data = save_data or {}
    catalog = dict(catalog or {})
    layout = compute_layout(content, ui)
    rects.clear()
    ui.draw_content_panel(screen, content)

    fonts = {
        "title": fonts.get("title") or pygame.font.Font(None, 40),
        "heading": fonts.get("heading") or pygame.font.Font(None, 24),
        "small": fonts.get("small") or pygame.font.Font(None, 16),
        "button": fonts.get("button") or pygame.font.Font(None, 20),
    }
    ui.draw_text(screen, "SHOP", fonts["title"], ui.TEXT, layout["header"].left, layout["header"].top, center=False)
    wallet = layout["wallet"]
    ui.draw_glass(screen, wallet, radius=18, tint=(*ui.WHITE, 235))
    ui.draw_coin_icon(screen, (wallet.left + 24, wallet.centery), 20)
    ui._blit_midleft(screen, fonts["small"], f"COINS: {save_data.get('coins', 0)}", ui.TEXT, wallet.left + 44, wallet.centery)

    rects["tabs"] = {}
    for tab, label in SHOP_TABS:
        tab_rect = layout["tab_rects"][tab]
        selected = tab == active_tab
        hovered = tab_rect.collidepoint(pygame.mouse.get_pos())
        fill = ui.WHITE if selected or hovered else ui.CARD_BACKGROUND
        ui.draw_smooth_rect(screen, tab_rect, (*fill, 245), radius=18)
        if selected:
            underline = pygame.Rect(tab_rect.left + 24, tab_rect.bottom - 5, tab_rect.width - 48, 4)
            ui.draw_gradient_rect(screen, underline, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=2)
        ui.draw_text(screen, label, fonts["heading"], ui.TEXT if selected else ui.MUTED_TEXT, tab_rect.centerx, tab_rect.centery)
        rects["tabs"][tab] = tab_rect

    rects["back"] = layout["back"]
    ui.draw_page_back_button(screen, layout["back"], fonts["button"])
    if active_tab == "themes":
        _draw_themes(screen, ui, layout, fonts, save_data, current_theme, catalog)
    elif active_tab == "wallpapers":
        _draw_wallpapers(screen, ui, layout, fonts, save_data, catalog)
    elif active_tab == "powerups":
        _draw_powerups(screen, ui, layout, fonts)
    elif active_tab == "levels":
        _draw_levels(screen, ui, layout, fonts, save_data, catalog)
    else:
        _draw_bundles(screen, ui, layout, fonts, save_data, catalog)


def hit_test(pos):
    if rects.get("back") and rects["back"].collidepoint(pos):
        return "back"
    for tab, rect in rects.get("tabs", {}).items():
        if rect.collidepoint(pos):
            return f"tab:{tab}"
    for action, rect in rects.items():
        if action.startswith(("theme:", "wallpaper:", "bundle:", "level:")) and rect and rect.collidepoint(pos):
            return action
    return None
