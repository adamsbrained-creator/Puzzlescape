"""First-launch onboarding flow for Puzzlescape."""

import pygame

import animations


PAGE_COUNT = 7


PAGES = (
    {
        "eyebrow": "WELCOME",
        "title": "PUZZLESCAPE",
        "body": (
            "Hi.",
            "Welcome to Puzzlescape.",
            "A little place for puzzles, pictures, stories, and probably an unreasonable amount of time spent dragging tiny pieces around.",
        ),
        "action": "CONTINUE",
    },
    {
        "eyebrow": "BEFORE WE BEGIN",
        "title": "There's something you should know.",
        "body": (
            "Puzzlescape was made for a very specific person.",
            "A beautiful girl named Alice.",
            "She likes puzzles. She likes cute things. She likes stories.",
            "So I thought... why not make a whole little world for her?",
        ),
        "action": "CONTINUE",
    },
    {
        "eyebrow": "THE PLAYER",
        "title": "But enough about her.",
        "body": ("What should I call you?",),
        "action": "CONTINUE",
        "name_input": True,
    },
    {
        "eyebrow": "NICE TO MEET YOU",
        "title": "",
        "body": (),
        "action": "CONTINUE",
        "response": True,
    },
    {
        "eyebrow": "YOUR PROFILE",
        "title": "One more thing.",
        "body": (
            "Every puzzler needs a face.",
            "Choose your profile picture.",
            "It can be you. It can be a character. It can be a cat.",
            "Honestly, I don't make the rules.",
        ),
        "action": "CHOOSE PICTURE",
        "picture": True,
    },
    {
        "eyebrow": "PROFILE COMPLETE",
        "title": "",
        "body": (),
        "action": "CONTINUE",
        "profile_response": True,
    },
    {
        "eyebrow": "HOW IT WORKS",
        "title": "So... how does this work?",
        "body": (
            "It's pretty simple.",
            "You'll get a picture.",
            "The picture gets broken into pieces.",
            "Your job is to put it back together.",
        ),
        "action": "LET'S PLAY",
        "guide": True,
    },
)


def card_rect(width, height):
    card = pygame.Rect(0, 0, min(700, width - 120), min(720, height - 100))
    card.center = (width // 2, height // 2)
    return card


def input_rect(card):
    rect = pygame.Rect(0, 0, min(460, card.width - 100), 60)
    rect.center = (card.centerx, card.top + 330)
    return rect


def picture_rect(card):
    rect = pygame.Rect(0, 0, 300, 52)
    rect.center = (card.centerx, card.top + 490)
    return rect


def action_rect(card):
    rect = pygame.Rect(0, 0, 280, 56)
    rect.center = (card.centerx, card.bottom - 72)
    return rect


def _draw_wrapped(screen, text, font, color, rect, line_height=28, center=True):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and font.size(candidate)[0] > rect.width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)

    for index, line in enumerate(lines):
        ui_position = (rect.centerx if center else rect.left, rect.top + index * line_height)
        screen.blit(font.render(line, True, color), font.render(line, True, color).get_rect(center=ui_position) if center else font.render(line, True, color).get_rect(topleft=ui_position))
    return len(lines)


def _response_lines(state):
    name = state.get("name", "Player").strip() or "Player"
    if name.casefold() == "alice":
        return (f"{name}.", "Yeah. That sounds right.", f"Welcome, {name}.")
    return (f"{name}.", "Nice to meet you.", "I think you're going to like it here.")


def draw(screen, ui, fonts, state, now):
    """Draw the current onboarding page and return its interactive rects."""
    page_index = max(0, min(PAGE_COUNT - 1, state.get("step", 0)))
    page = PAGES[page_index]
    card = card_rect(ui.WIDTH, ui.HEIGHT)
    entry_offset = animations.slide_offset(state.get("started_at", now), 0.45, now)
    breathing = animations.breathe(now, speed=1.4, amount=0.012)
    card.move_ip(0, entry_offset)

    ui.draw_glass(screen, card, radius=32, tint=(*ui.WHITE, 245))
    ui.draw_text(screen, page["eyebrow"], fonts["small"], ui.MUTED_TEXT, card.centerx, card.top + 42)

    title = page["title"]
    if page.get("response"):
        lines = _response_lines(state)
        for index, line in enumerate(lines):
            ui.draw_text(screen, line, fonts["heading"], ui.TEXT, card.centerx, card.top + 180 + index * 42)
    elif page.get("profile_response"):
        ui.draw_text(screen, "There we go.", fonts["heading"], ui.TEXT, card.centerx, card.top + 190)
        ui.draw_text(screen, "Puzzlescape has officially met you.", fonts["subtitle"], ui.MUTED_TEXT, card.centerx, card.top + 242)
        ui.draw_text(screen, "Try not to look too suspicious.", fonts["subtitle"], ui.MUTED_TEXT, card.centerx, card.top + 286)
    else:
        if title:
            ui.draw_text(screen, title, fonts["hero" if page_index == 0 else "heading"], ui.TEXT, card.centerx, card.top + 112)
        body_top = card.top + (170 if title else 130)
        for index, paragraph in enumerate(page["body"]):
            body_rect = pygame.Rect(card.left + 54, body_top + index * 58, card.width - 108, 52)
            _draw_wrapped(screen, paragraph, fonts["subtitle"], ui.MUTED_TEXT if index else ui.TEXT, body_rect, 24)

    rects = {"action": action_rect(card)}
    if page.get("name_input"):
        input_box = input_rect(card)
        ui.draw_glass(screen, input_box, radius=20, tint=(*ui.WHITE, 245))
        value = state.get("name", "")
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            value += "|"
        shown = value or "Your name"
        color = ui.TEXT if value else ui.MUTED_TEXT
        ui.draw_text(screen, shown, fonts["button"], color, input_box.centerx, input_box.centery)
        rects["name_input"] = input_box
    elif page.get("picture"):
        picture_button = picture_rect(card)
        label = "CHANGE PICTURE" if state.get("profile_picture") else "CHOOSE PICTURE"
        ui.draw_smooth_rect(screen, picture_button, (*ui.TRACK_BACKGROUND, 255), radius=18)
        ui.draw_text(screen, label, fonts["button"], ui.TEXT, picture_button.centerx, picture_button.centery)
        rects["picture"] = picture_button
    elif page.get("guide"):
        for index, text in enumerate(("Get a picture.", "Put the pieces back.", "Enjoy the little world.")):
            y = card.top + 470 + index * 32
            ui.draw_text(screen, str(index + 1), fonts["button"], ui.ACCENT_BLUE, card.left + 88, y)
            ui.draw_text(screen, text, fonts["small"], ui.MUTED_TEXT, card.left + 132, y, center=False)

    for index in range(PAGE_COUNT):
        dot_size = round(7 * breathing) if index == page_index else 7
        dot = pygame.Rect(0, 0, dot_size, dot_size)
        dot.center = (card.centerx - (PAGE_COUNT - 1) * 6 // 2 + index * 6, card.bottom - 28)
        color = ui.ACCENT_BLUE if index == page_index else ui.TRACK_BACKGROUND
        ui.draw_smooth_rect(screen, dot, color, radius=4)

    ui.draw_gradient_rect(screen, rects["action"], ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=20)
    ui.draw_text(screen, page["action"], fonts["button"], ui.TEXT, rects["action"].centerx, rects["action"].centery)
    return rects
