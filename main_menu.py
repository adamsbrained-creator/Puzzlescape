import pygame


CARDS = (
    ("levels", "LEVELS", "Classic puzzle progression. Master each stage.", "piece", True),
    ("journey", "JOURNEY", "Embark on a story-based adventure.", "journey", True),
    ("investigation", "INVESTIGATION", "Solve mysteries by piecing clues.", "search", False),
    ("daily", "DAILY CHALLENGE", "New puzzle every day. Earn rewards.", "calendar", True),
)
CARD_GAP = 32
SIDE_MARGIN = 40
CARD_RADIUS = 24
CARD_MAX_HEIGHT = 298
CONTENT_MAX_WIDTH = 1300

rects = {}


def _visible_action_set(visible_actions):
    if visible_actions is None:
        return {action for action, *_ in CARDS if action != "journey"}
    return set(visible_actions)


def sidebar_target(key, last_screens):
    """Play always opens its hub; other spaces restore their last page."""
    if key == "play":
        return "main_menu"
    return last_screens.get(key)


def compute_layout(content, ui, visible_actions=None):
    visible_actions = _visible_action_set(visible_actions)
    visible_cards = [card for card in CARDS if card[0] in visible_actions]
    back = ui.get_page_back_rect()
    width = min(CONTENT_MAX_WIDTH, content.width - SIDE_MARGIN * 2)
    left = content.left + (content.width - width) // 2
    back.left = left
    top = content.top + 112
    bottom = min(content.bottom - 24, back.top - 24)
    card_width = (width - CARD_GAP) // 2
    card_height = min(CARD_MAX_HEIGHT, (bottom - top - CARD_GAP) // 2)
    cards = {}
    for index, (action, _title, _description, _icon, _enabled) in enumerate(visible_cards):
        column, row = index % 2, index // 2
        cards[action] = pygame.Rect(
            left + column * (card_width + CARD_GAP),
            top + row * (card_height + CARD_GAP),
            card_width,
            card_height,
        )
    return {"title": pygame.Rect(left, content.top + 38, width, 52), "cards": cards, "back": back}


def _draw_card_base(screen, ui, rect, hovered):
    ui.draw_blurred_shadow(
        screen, rect, border_radius=CARD_RADIUS, blur=14,
        alpha=62 if hovered else 42, color=ui.CARD_SHADOW,
        offset=(0, 7 if hovered else 5),
    )
    ui.draw_smooth_rect(screen, rect, (*ui.CARD_BACKGROUND, 255), radius=CARD_RADIUS)
    ui.draw_smooth_rect(screen, rect, (*ui.CARD_BORDER, 255), radius=CARD_RADIUS, width=1)


def _draw_action_button(screen, ui, rect, label, font, enabled, hovered):
    if enabled:
        ui.draw_blurred_shadow(
            screen, rect, border_radius=16, blur=9,
            alpha=44 if hovered else 30, color=ui.CARD_SHADOW, offset=(0, 4)
        )
        ui.draw_gradient_rect(
            screen, rect, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=16
        )
        color = ui.TEXT
    else:
        ui.draw_smooth_rect(screen, rect, (*ui.TRACK_BACKGROUND, 255), radius=16)
        color = ui.MUTED_TEXT
    ui.draw_text(screen, label, font, color, rect.centerx, rect.centery)


def _wrap_description(font, text, width):
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


def draw(screen, ui, content, fonts=None, mouse_pos=None, visible_actions=None):
    fonts = dict(fonts or {})
    fonts.setdefault("title", pygame.font.Font(None, 42))
    fonts.setdefault("heading", pygame.font.Font(None, 28))
    fonts.setdefault("subtitle", pygame.font.Font(None, 20))
    fonts.setdefault("button", pygame.font.Font(None, 22))
    fonts.setdefault("small", pygame.font.Font(None, 16))
    mouse = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
    visible_actions = _visible_action_set(visible_actions)
    visible_cards = [card for card in CARDS if card[0] in visible_actions]
    layout = compute_layout(content, ui, visible_actions)
    rects.clear()

    ui.draw_content_panel(screen, content)
    ui.draw_text(screen, "PLAY MENU", fonts["title"], ui.TEXT, layout["title"].left, layout["title"].top, center=False)

    for action, title, description, icon, enabled in visible_cards:
        card = layout["cards"][action]
        hovered = card.collidepoint(mouse)
        _draw_card_base(screen, ui, card, hovered)

        text_left = card.left + 24
        icon_tile = pygame.Rect(text_left, card.top + 28, 84, 84)
        ui.draw_smooth_rect(screen, icon_tile, (*ui.WHITE, 240), radius=18)
        if icon == "piece":
            ui.draw_achievement_icon(screen, "puzzle", icon_tile.center, 50)
        elif icon == "journey":
            ui.draw_achievement_icon(screen, "mountain", icon_tile.center, 50)
        elif icon == "search":
            center = (icon_tile.centerx - 4, icon_tile.centery - 4)
            pygame.draw.circle(screen, ui.ACCENT_BLUE, center, 15, width=4)
            pygame.draw.line(screen, ui.ACCENT_BLUE, (center[0] + 11, center[1] + 11), (center[0] + 24, center[1] + 24), 5)
        else:
            ui.draw_achievement_icon(screen, "calendar", icon_tile.center, 50)
        title_left = icon_tile.right + 18
        ui.draw_text(screen, title, fonts["heading"], ui.TEXT, title_left, icon_tile.centery, center=False)
        for line_index, line in enumerate(_wrap_description(fonts["subtitle"], description, card.width - 48)):
            ui.draw_text(screen, line, fonts["subtitle"], ui.MUTED_TEXT, text_left, card.top + 142 + line_index * 24, center=False)

        button = pygame.Rect(text_left, card.bottom - 84, card.width - 48, 64)
        _draw_action_button(screen, ui, button, "PLAY" if enabled else "COMING SOON", fonts["button"], enabled, hovered)
        rects[action] = card
        rects[f"button:{action}"] = button if enabled else None

    rects["back"] = layout["back"]
    ui.draw_page_back_button(screen, layout["back"], fonts["button"])


def hit_test(pos):
    if rects.get("back") and rects["back"].collidepoint(pos):
        return "back"
    for action, card in rects.items():
        if action.startswith("button:") or action == "back":
            continue
        button = rects.get(f"button:{action}")
        if button is None:
            continue
        if (button and button.collidepoint(pos)) or (card and card.collidepoint(pos)):
            return action
    return None
