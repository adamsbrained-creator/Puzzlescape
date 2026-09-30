"""
Clean White UI Module for Puzzlescape Settings
"""

import pygame

# --- Color Palette (Light Theme) ---
BG_COLOR = (245, 247, 250)
CARD_BG = (255, 255, 255)
CARD_BORDER = (226, 232, 240)
TEXT_PRIMARY = (30, 41, 59)
TEXT_MUTED = (100, 116, 139)
ACCENT_BLUE = (59, 130, 246)
BTN_WHITE_BG = (255, 255, 255)


def get_default_font():
    """Fallback font loader to prevent missing font crashes."""
    try:
        return pygame.font.SysFont("segoeui", 18, bold=True)
    except Exception:
        return pygame.font.Font(None, 24)


def draw_settings_sidebar(surface, active_section, font=None):
    """Renders the clean sidebar dock with indicator bar."""
    if font is None:
        font = get_default_font()

    sidebar_rect = pygame.Rect(0, 0, 240, surface.get_height())
    pygame.draw.rect(surface, (255, 255, 255), sidebar_rect)
    pygame.draw.line(surface, CARD_BORDER, (240, 0), (240, surface.get_height()), 2)

    title_text = font.render("SETTINGS", True, TEXT_PRIMARY)
    surface.blit(title_text, (30, 40))

    sections = [("Audio", "audio"), ("Video", "video"), ("Controls", "controls")]
    start_y = 120

    for label, section_key in sections:
        item_rect = pygame.Rect(20, start_y, 200, 44)

        if str(active_section).lower() == section_key:
            pygame.draw.rect(
                surface, (239, 246, 255), item_rect, border_radius=8
            )
            pygame.draw.rect(
                surface, ACCENT_BLUE, (20, start_y + 8, 4, 28), border_radius=2
            )
            text_color = ACCENT_BLUE
        else:
            text_color = TEXT_MUTED

        text_surf = font.render(label, True, text_color)
        surface.blit(text_surf, (36, start_y + 10))
        start_y += 56


def draw_white_card(surface, x, y, width, height):
    """Draws a clean white container card."""
    card_rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, CARD_BG, card_rect, border_radius=12)
    pygame.draw.rect(
        surface, CARD_BORDER, card_rect, width=1, border_radius=12
    )
    return card_rect


def draw_audio_settings(surface, settings_data=None, font=None):
    """Renders Audio settings inside white cards."""
    if font is None:
        font = get_default_font()
    if settings_data is None:
        settings_data = {}

    card_1 = draw_white_card(surface, 280, 100, 480, 120)
    label = font.render("Master Volume", True, TEXT_PRIMARY)
    surface.blit(label, (card_1.x + 24, card_1.y + 20))

    track_rect = pygame.Rect(card_1.x + 24, card_1.y + 65, 432, 10)
    pygame.draw.rect(surface, CARD_BORDER, track_rect, border_radius=5)

    vol_val = (
        settings_data.get("volume", 0.8)
        if isinstance(settings_data, dict)
        else 0.8
    )
    try:
        vol_pct = max(0.0, min(1.0, float(vol_val)))
    except (ValueError, TypeError):
        vol_pct = 0.8

    active_track = pygame.Rect(
        card_1.x + 24, card_1.y + 65, int(432 * vol_pct), 10
    )
    pygame.draw.rect(surface, ACCENT_BLUE, active_track, border_radius=5)

    card_2 = draw_white_card(surface, 280, 240, 480, 80)
    sfx_label = font.render("Sound Effects (SFX)", True, TEXT_PRIMARY)
    surface.blit(sfx_label, (card_2.x + 24, card_2.y + 28))


def draw_flat_back_button(surface, font=None):
    """Renders the flat white back button."""
    if font is None:
        font = get_default_font()

    button_rect = pygame.Rect(280, 520, 140, 44)
    pygame.draw.rect(surface, BTN_WHITE_BG, button_rect, border_radius=8)
    pygame.draw.rect(
        surface, CARD_BORDER, button_rect, width=1, border_radius=8
    )

    text_surf = font.render("<- Back", True, TEXT_PRIMARY)
    text_rect = text_surf.get_rect(center=button_rect.center)
    surface.blit(text_surf, text_rect)
    return button_rect


def draw_settings_screen(surface, *args, **kwargs):
    """Universal renderer wrapper that accepts any argument format."""
    font = None
    settings_data = {}
    active_section = "audio"

    for arg in args:
        if isinstance(arg, dict):
            if "active_section" in arg or "section" in arg:
                active_section = arg.get("active_section") or arg.get("section")
            else:
                settings_data = arg
        elif isinstance(arg, str):
            active_section = arg
        elif hasattr(arg, "render"):
            font = arg

    if "settings" in kwargs and isinstance(kwargs["settings"], dict):
        settings_data = kwargs["settings"]
    if "font" in kwargs and hasattr(kwargs["font"], "render"):
        font = kwargs["font"]

    if font is None:
        font = get_default_font()

    surface.fill(BG_COLOR)
    draw_settings_sidebar(surface, active_section, font)

    header_text = font.render(
        str(active_section).capitalize(), True, TEXT_PRIMARY
    )
    surface.blit(header_text, (280, 40))

    if str(active_section).lower() == "audio":
        draw_audio_settings(surface, settings_data, font)

    back_btn_rect = draw_flat_back_button(surface, font)
    return back_btn_rect