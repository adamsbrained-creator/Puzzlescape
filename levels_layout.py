import pygame


ITEM_COUNT = 10
CARD_GAP = 44
CARD_HEIGHT = 570
CARD_WIDTH = 430
HEADER_CLEARANCE = 100
SIDE_MARGIN = 40
SCROLLBAR_HEIGHT = 8
SCROLLBAR_BOTTOM_CLEARANCE = 28
HOVER_SCALE = 1.0


def compute_layout(content, scroll_x=0, item_count=ITEM_COUNT):
    item_count = max(1, int(item_count))
    viewport_top = content.top + HEADER_CLEARANCE
    viewport = pygame.Rect(
        content.left + SIDE_MARGIN,
        viewport_top,
        content.width - SIDE_MARGIN * 2,
        CARD_HEIGHT,
    )
    card_width = min(CARD_WIDTH, max(280, (viewport.width - CARD_GAP * 2) // 3))
    first_row_width = 3 * card_width + 2 * CARD_GAP
    initial_inset = max(0, (viewport.width - first_row_width) // 2)
    content_width = item_count * card_width + (item_count - 1) * CARD_GAP
    scrollable_width = viewport.width - initial_inset
    max_scroll = max(0, content_width - scrollable_width)
    scroll_x = max(0, min(int(scroll_x), max_scroll))

    items = [
        pygame.Rect(
            viewport.left + initial_inset + index * (card_width + CARD_GAP) - scroll_x,
            viewport.top,
            card_width,
            CARD_HEIGHT,
        )
        for index in range(item_count)
    ]

    return {
        "viewport": viewport,
        "cards": items[:item_count - 1],
        "hidden": items[-1],
        "items": items,
        "scroll_x": scroll_x,
        "max_scroll": max_scroll,
        "content_width": content_width,
        "card_width": card_width,
        "initial_inset": initial_inset,
        "scrollable_width": scrollable_width,
        "scrollbar": pygame.Rect(
            viewport.left,
            content.bottom - SCROLLBAR_BOTTOM_CLEARANCE - SCROLLBAR_HEIGHT,
            viewport.width,
            SCROLLBAR_HEIGHT,
        ),
    }


def compute_level_grid_layout(content, level_count=10):
    level_count = max(0, int(level_count))
    columns = min(5, max(1, level_count))
    rows = (level_count + columns - 1) // columns
    gap = 16
    viewport = pygame.Rect(
        content.left + 40,
        content.top + 100,
        content.width - 80,
        max(1, content.height - 212),
    )
    card_width = (viewport.width - gap * (columns - 1)) // columns
    card_height = min(320, max(1, (viewport.height - gap * max(0, rows - 1)) // max(1, rows)))
    cards = [
        pygame.Rect(
            viewport.left + (index % columns) * (card_width + gap),
            viewport.top + (index // columns) * (card_height + gap),
            card_width,
            card_height,
        )
        for index in range(level_count)
    ]
    return {
        "viewport": viewport,
        "cards": cards,
        "columns": columns,
        "rows": rows,
        "card_width": card_width,
        "card_height": card_height,
    }


def scroll_by(scroll_y, delta, max_scroll):
    return max(0, min(int(scroll_y + delta), int(max_scroll)))


def hover_rect(rect, viewport, scale=HOVER_SCALE):
    grown = rect.inflate(
        round(rect.width * (scale - 1)),
        round(rect.height * (scale - 1)),
    )
    grown.clamp_ip(viewport)
    return grown


def category_card_content_layout(card_rect, photo_height, wrap_font=None):
    photo = pygame.Rect(
        card_rect.left + 12,
        card_rect.top + 12,
        card_rect.width - 24,
        min(photo_height, card_rect.height - 24),
    )
    progress_ring = pygame.Rect(0, 0, 64, 64)
    progress_ring.bottomright = (photo.right - 10, photo.bottom - 10)

    text_column = pygame.Rect(
        photo.left + 16,
        photo.bottom - 64,
        max(1, photo.width - 108),
        46,
    )
    title = pygame.Rect(text_column.left, text_column.top, text_column.width, 24)
    progress = pygame.Rect(text_column.left, text_column.top + 28, text_column.width, 18)

    section_top = photo.bottom + 12
    rewards_center = card_rect.left + card_rect.width // 4
    unlockables_center = card_rect.left + card_rect.width * 3 // 4
    icon_y = section_top + 70
    label_y = section_top + 108
    icon_gap = 48

    description_left = card_rect.left + 18
    description_width = card_rect.width - 36
    description_title_y = label_y + 58
    description_top = description_title_y + 24

    wrap_font = wrap_font or pygame.font.Font(None, 16)

    def description_lines(text):
        lines = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            if current and wrap_font.size(candidate)[0] > description_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines[:2]

    return {
        "photo": photo,
        "progress_ring": progress_ring,
        "text_column": text_column,
        "title": title,
        "progress": progress,
        "section_top": section_top,
        "rewards_left": card_rect.left + 18,
        "rewards_center": rewards_center,
        "unlockables_center": unlockables_center,
        "reward_icon_centers": (
            (rewards_center - icon_gap, icon_y),
            (rewards_center + icon_gap, icon_y),
        ),
        "unlock_icon_centers": (
            (unlockables_center - icon_gap, icon_y),
            (unlockables_center + icon_gap, icon_y),
        ),
        "reward_label_y": label_y,
        "unlock_label_y": label_y,
        "description_left": description_left,
        "description_title_center": card_rect.centerx,
        "description_title_y": description_title_y,
        "description_top": description_top,
        "description_lines": description_lines,
    }