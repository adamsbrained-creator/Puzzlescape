import clean_settings_ui
import pygame
import sys
import json
import os
import atexit
import time
import random
import math
from datetime import date

import paths
paths.enter_bundle_dir()   # must run before anything below loads a font or image

from puzzle import Puzzle
import animations
import onboarding
import ui
import save_manager
import main_menu
import achievements
import journey
import rewards
import settings_page
import selection
import shop
import levels_layout

# Wraps a handful of puzzle.Piece / puzzle.Puzzle methods so a boxed
# selection can be dragged as one unit - see selection.py's own docstring.
# Has to run before any Puzzle/Piece object is created, so it happens here,
# right at import time, rather than waiting for the first puzzle screen.
selection.install()


# --------------------------------------------------
# Puzzlescape
# --------------------------------------------------

# Windows scales a non-DPI-aware app's whole window as a bitmap to match
# the display's scaling setting (125%, 150%, ...). When it does, the
# mouse positions pygame receives land in a different coordinate space
# than what's actually drawn on screen - which shows up exactly like a
# piece hitting an invisible wall well before it reaches the true edge
# of the window, or a chunk of the window that looks blank/dead even
# though the canvas is supposed to reach all the way there. Declaring
# the process DPI-aware before anything else stops Windows from doing
# that scaling itself, so pygame's own window-to-canvas mapping is the
# only scaling happening. No effect on macOS/Linux.
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # per-monitor DPI aware
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()    # older Windows fallback
        except (AttributeError, OSError):
            pass

pygame.init()


WIDTH = 1600
HEIGHT = 900


# The game always draws on a fixed 1600x900 canvas (`screen`) - a true
# 16:9 shape, matching every resolution preset below and virtually every
# real monitor, so present_frame()'s stretch-to-fill is always a plain,
# equal x/y scale with no distortion. (It used to be 1440x900 - an 8:5
# shape - which meant every 16:9 window stretched the canvas about 11%
# wider than tall: circles a little oval, square tiles visibly flattened.
# Widening the canvas to match, rather than shrinking it to fit inside a
# 16:9 window, keeps every screen's existing height-based layout exactly
# as it was and just gives everything more room sideways.) Every frame,
# present_frame() copies that canvas onto the real window, stretched to
# fill it exactly (see the display section below). That is what lets the
# window be any size - 720p, 1080p, 4K, fullscreen - without touching any
# drawing code.
os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

window = pygame.display.set_mode((WIDTH, HEIGHT))   # replaced by open_window()
screen = pygame.Surface((WIDTH, HEIGHT)).convert()


pygame.display.set_caption(
    "Puzzlescape"
)

# Only the welcome screen's name field uses this, but it's harmless to
# leave on everywhere else - pygame just won't fire TEXTINPUT events
# unless something is actually listening for them in the event loop.
pygame.key.start_text_input()

try:
    # Same picture as the sidebar logo - used for the window/taskbar icon.
    # Optional: a missing or unreadable logo just means the default
    # pygame icon shows instead, never a crash.
    pygame.display.set_icon(pygame.image.load("assets/logo.png"))
except (pygame.error, FileNotFoundError):
    pass


clock = pygame.time.Clock()


# --------------------------------------------------
# Fonts
# --------------------------------------------------

FONT_PATH = "assets/fonts/InterVariable.ttf"


title_font = pygame.font.Font(
    FONT_PATH,
    40
)


hero_font = pygame.font.Font(
    FONT_PATH,
    46
)


subtitle_font = pygame.font.Font(
    FONT_PATH,
    19
)


button_font = pygame.font.Font(
    FONT_PATH,
    20
)


small_font = pygame.font.Font(
    FONT_PATH,
    16
)


heading_font = pygame.font.Font(
    FONT_PATH,
    28
)


timer_font = pygame.font.Font(
    FONT_PATH,
    20
)


header_font = pygame.font.Font(
    FONT_PATH,
    22
)


# --------------------------------------------------
# Levels
# --------------------------------------------------

# Nine themed categories, each with its own folder of 10 numbered images
# (assets/images/levels/<key>/<key>1.jpg ... <key>10.jpg). A missing image
# just falls back to the test image (see load_level_image) - so a category
# works fine even before all 10 pictures have been dropped into place.
DEFAULT_CATEGORIES = [
    {
        "key": "architecture",
        "label": "Architecture",
        "description": "Buildings, bridges, and city landmarks.",
        "legacy_labels": ["Architectural Marvels"],
        "level_names": ["Stone Bridge", "Town Hall", "Old Library", "Clock Tower", "Glass Tower", "Garden Pavilion", "Stone Castle", "City Museum", "Riverside Homes", "City Skyline"],
    },
    {
        "key": "nature",
        "label": "Nature",
        "description": "Mountains, forests, and quiet places.",
        "legacy_labels": ["Natural Landscapes"],
        "level_names": ["Forest Path", "Mountain Lake", "Waterfall", "Wildflower Field", "Pine Valley", "Ocean Shore", "Autumn Woods", "Desert Sunrise", "Snowy Peak", "Green Valley"],
    },
    {
        "key": "animals",
        "label": "Animals",
        "description": "Wild animals, pets, and life outdoors.",
        "legacy_labels": ["Wildlife Wonders"],
        "level_names": ["Red Fox", "Sea Turtle", "Arctic Owl", "Forest Deer", "River Otter", "Monarch Butterfly", "Mountain Goat", "Golden Retriever", "Elephant Herd", "Wild Horses"],
    },
    {
        "key": "movies_and_series",
        "label": "Movies & Shows",
        "description": "Scenes and settings from film and television.",
        "legacy_labels": ["Movies & Series"],
        "image_prefix": "movies_and_shows",
        "level_names": ["Old Cinema", "Spotlight", "Film Set", "Space Voyage", "City Chase", "Costume Room", "Mystery Scene", "Cartoon World", "Movie Premiere", "Final Scene"],
    },
    {
        "key": "music",
        "label": "Music",
        "description": "Instruments, performers, and musical places.",
        "legacy_labels": ["Musical Moments"],
        "level_names": ["Piano Room", "Jazz Night", "Guitar Strings", "Drum Circle", "Violin Solo", "Record Shop", "Concert Hall", "Street Music", "Sound Studio", "Grand Orchestra"],
    },
    {
        "key": "books",
        "label": "Books",
        "description": "Books, stories, and reading spaces.",
        "level_names": ["Open Book", "Quiet Library", "Bookshop Window", "Reading Nook", "Storybook Garden", "Paperbacks", "Library Steps", "Book Stacks", "Story Time", "The Last Chapter"],
    },
    {
        "key": "photography",
        "label": "Photography",
        "description": "Photographs of places and everyday details.",
        "level_names": ["Golden Hour", "Mountain View", "City Lights", "Ocean Frame", "Rainy Street", "Forest Reflection", "Desert Colors", "Window Light", "Night Sky", "Coastline"],
    },
    {
        "key": "world",
        "label": "World",
        "description": "Landmarks and places around the globe.",
        "legacy_labels": ["World Wonders"],
        "level_names": ["Paris Street", "Kyoto Garden", "Sahara Dunes", "Venice Canal", "Andes Peaks", "Cairo Market", "New York Skyline", "Great Wall", "Santorini Coast", "Safari Plains"],
    },
    {
        "key": "alice",
        "label": "Alice",
        "description": "Alice's curious trip through Wonderland.",
        "legacy_labels": ["Alice's Adventures"],
        "level_names": ["White Rabbit", "Rabbit Hole", "Mad Tea Party", "Cheshire Cat", "Card Garden", "Queen's Croquet", "Bottle and Cake", "Looking Glass", "Tulgey Wood", "Wonderland"],
    },
]

LEVEL_PACK_CATEGORIES = [
    {
        **pack,
        "paid_pack": True,
        "level_names": [f"{pack['label']} {number}" for number in range(1, shop.LEVELS_PER_PACK + 1)],
    }
    for pack in shop.LEVEL_PACKS
]
CATEGORIES = DEFAULT_CATEGORIES + LEVEL_PACK_CATEGORIES
LEVEL_PACK_KEYS = {category["key"] for category in LEVEL_PACK_CATEGORIES}

LEVELS_PER_CATEGORY = 10

# Shared 1..10 difficulty curve (piece grid) every category climbs through -
# puzzle 1 is a quick 12-piece warm-up, puzzle 10 is a proper 150-piece
# puzzle. (columns, rows).
LEVEL_GRID_PROGRESSION = [
    (4, 3),    # 12
    (5, 4),    # 20
    (6, 5),    # 30
    (7, 6),    # 42
    (8, 7),    # 56
    (9, 8),    # 72
    (11, 8),   # 88
    (12, 9),   # 108
    (13, 10),  # 130
    (15, 10),  # 150
]

# A puzzle's difficulty rating for the Minimal header - just its own
# piece count, split into three tiers. These two breakpoints (42, 108)
# are chosen to cut the whole range used by any puzzle in the game -
# category levels run 12..150 pieces over 10 steps, Journey runs
# 12..768 over 7 - into three roughly even-feeling bands, so both
# systems' early/mid/late levels land somewhere sensible.
DIFFICULTY_TIERS = [(42, "Easy"), (108, "Medium")]
DIFFICULTY_STAR_COUNT = 3


def difficulty_rating(level):
    """(stars filled out of DIFFICULTY_STAR_COUNT, label) for `level`."""
    pieces = level["columns"] * level["rows"]

    for tier_index, (ceiling, label) in enumerate(DIFFICULTY_TIERS):
        if pieces <= ceiling:
            return tier_index + 1, label

    return len(DIFFICULTY_TIERS) + 1, "Hard"


# The secret 10th "category": one giant puzzle stitched from the whole
# journey, unlocked only once every puzzle in every category above has
# been completed - see is_ultimate_unlocked().
ULTIMATE_LEVEL = {
    "name": "The Ultimate Puzzle",
    "category": "ultimate",
    "category_label": "The Ultimate Puzzle",
    "index_in_category": 1,
    "image": "assets/images/levels/ultimate/ultimate1.jpg",
    "columns": 32,
    "rows": 24,   # 768 pieces
    "hidden": True,
}


def _build_levels(categories):
    built = []
    for category in categories:
        key = category["key"]
        for n in range(1, LEVELS_PER_CATEGORY + 1):
            columns, rows = LEVEL_GRID_PROGRESSION[n - 1]
            level_names = category.get("level_names", [])
            name = level_names[n - 1] if n <= len(level_names) else f"{category['label']} {n}"
            image_folder = category.get("image_folder", key)
            image_prefix = category.get("image_prefix", image_folder)
            built.append({
                "name": name,
                "category": key,
                "category_label": category["label"],
                "index_in_category": n,
                "image": f"assets/images/levels/{image_folder}/{image_prefix}{n}.jpg",
                "columns": columns,
                "rows": rows,
            })
    return built


# Every playable puzzle except the hidden one - what the daily rotation,
# the category grid and "finish everything" checks all count against.
REGULAR_LEVELS = _build_levels(DEFAULT_CATEGORIES)
LEVEL_PACK_LEVELS = _build_levels(LEVEL_PACK_CATEGORIES)
ALL_REGULAR_LEVELS = REGULAR_LEVELS + LEVEL_PACK_LEVELS

# The flat list used everywhere else in the file. Built category by
# category, in order, so "next puzzle" on the win screen can just walk
# forward through it - Alice 10 is naturally followed by the hidden
# Ultimate puzzle.
LEVELS = ALL_REGULAR_LEVELS + [ULTIMATE_LEVEL]


def category_levels(category_key):
    return [level for level in ALL_REGULAR_LEVELS if level["category"] == category_key]


def available_categories(data):
    return [
        category for category in CATEGORIES
        if not category.get("paid_pack")
        or shop.is_level_pack_owned(data, category["key"])
    ]


def available_regular_levels(data):
    return REGULAR_LEVELS + [
        level for level in LEVEL_PACK_LEVELS
        if shop.is_level_pack_owned(data, level["category"])
    ]


def _build_legacy_level_name_map():
    aliases = {}
    for category in CATEGORIES:
        levels = category_levels(category["key"])
        for old_label in category.get("legacy_labels", []):
            for level in levels:
                aliases[f"{old_label} {level['index_in_category']}"] = level["name"]
    return aliases


LEGACY_LEVEL_NAME_MAP = _build_legacy_level_name_map()


def find_level_by_name(name):
    """Any level by its save-file name - a category puzzle, the Ultimate,
    or a Journey rung (so the wallpaper system is already ready for
    Journey pictures whenever they get a picker)."""
    for level in LEVELS:
        if level["name"] == name:
            return level
    for level in journey.JOURNEY_ALL:
        if level["name"] == name:
            return level
    return None


def active_wallpaper_path():
    """The selected unlocked level photo, or None if it is no longer valid.
    Checked fresh every frame so a wallpaper can never outlive the
    unlock it came from."""
    name = settings.get("wallpaper")
    if not name or name not in completed_level_names:
        return None

    level = find_level_by_name(name)
    return level["image"] if level else None


def is_ultimate_unlocked(data):
    """True once every puzzle in every regular category has been finished."""
    return all(
        save_manager.level_entry(data, level["name"])["completed"]
        for level in REGULAR_LEVELS
    )


def is_level_unlocked(level):
    """Puzzles open up one at a time within their category: puzzle 1 is
    always playable, and puzzle N needs puzzle N-1 (same category)
    finished first. The hidden Ultimate puzzle has its own, separate
    unlock check (is_ultimate_unlocked) since it isn't part of a
    category at all."""
    if level.get("hidden"):
        return is_ultimate_unlocked(save_data)

    if level["category"] in LEVEL_PACK_KEYS and not shop.is_level_pack_owned(save_data, level["category"]):
        return False

    if level["index_in_category"] <= 1:
        return True

    levels = category_levels(level["category"])
    previous = levels[level["index_in_category"] - 2]
    return save_manager.level_entry(save_data, previous["name"])["completed"]


def is_daily_unlocked():
    """Daily Challenge opens when Architecture puzzle 2 becomes available."""
    architecture_levels = category_levels("architecture")
    if len(architecture_levels) < 2:
        return False
    return is_level_unlocked(architecture_levels[1])


def visible_play_actions():
    """Modes currently earned by the player, in play-menu order."""
    actions = {"levels"}
    if rewards.has_feature(save_data, "journey"):
        actions.add("journey")
    if is_daily_unlocked():
        actions.add("daily")
    return actions


FALLBACK_IMAGE_PATH = "assets/images/test.jpg"

# A level picture can be saved as .jpg, .jpeg, .png or .webp - whichever
# one it is, "animals3" is found by its name. (Windows hides file
# extensions by default, so it's easy not to know which one a file has.)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

# Menus, cards and the gallery only ever need a small copy of a picture,
# so those are kept small. The full-size picture is only needed while a
# puzzle is being solved (and on the win screen), so only the last few
# are kept in memory - otherwise 91 big photos would pile up as the
# player browses through the categories.
THUMBNAIL_WIDTH = 640
FULL_IMAGE_CACHE_SIZE = 3

_level_image_cache = {}      # path -> full-size picture (most recently used last)
_thumbnail_cache = {}        # path -> small picture for menus


def find_level_image_file(path):
    """The real file for a level picture path, trying the other common
    picture extensions too. Returns None if no such file exists yet."""
    if os.path.exists(path):
        return path

    stem = os.path.splitext(path)[0]
    for extension in IMAGE_EXTENSIONS:
        for candidate in (stem + extension, stem + extension.upper()):
            if os.path.exists(candidate):
                return candidate

    return None


def _read_level_image(path):
    """Loads a picture from disk (no caching). A missing or unreadable
    file gives the placeholder picture instead."""
    real_path = find_level_image_file(path)

    if real_path is not None:
        try:
            return pygame.image.load(real_path).convert_alpha()
        except (pygame.error, FileNotFoundError):
            pass

    return pygame.image.load(FALLBACK_IMAGE_PATH).convert_alpha()


def load_level_image(
    path
):
    """The full-size picture - for solving the puzzle and the win screen."""
    image = _level_image_cache.pop(path, None)
    if image is None:
        image = _read_level_image(path)

    _level_image_cache[path] = image          # now the most recently used
    while len(_level_image_cache) > FULL_IMAGE_CACHE_SIZE:
        del _level_image_cache[next(iter(_level_image_cache))]

    return image


def load_level_thumbnail(path):
    """A small copy of the picture, for menus, cards and the gallery."""
    thumbnail = _thumbnail_cache.get(path)

    if thumbnail is None:
        full = _level_image_cache.get(path)
        if full is None:
            full = _read_level_image(path)

        if full.get_width() > THUMBNAIL_WIDTH:
            height = max(1, round(full.get_height() * THUMBNAIL_WIDTH / full.get_width()))
            thumbnail = pygame.transform.smoothscale(full, (THUMBNAIL_WIDTH, height))
        else:
            thumbnail = full

        _thumbnail_cache[path] = thumbnail

    return thumbnail


def report_missing_images():
    """Prints (in the console window) which level pictures haven't been
    added yet - those puzzles show the placeholder picture until they are.
    Handy while filling the 91 slots in."""
    missing = {}
    for level in LEVELS + journey.JOURNEY_ALL:
        if find_level_image_file(level["image"]) is None:
            missing.setdefault(level["category_label"], []).append(
                os.path.basename(level["image"])
            )

    if not missing:
        print("All level pictures found.")
        return

    total = sum(len(files) for files in missing.values())
    print(f"{total} level picture(s) not added yet (the placeholder is shown instead):")
    for label, files in missing.items():
        print(f"  {label}: {', '.join(files)}")

    if "Journey" in missing:
        print("  (Until its own picture is added, each Journey level uses the first picture of its theme.)")


def resolve_journey_pictures():
    """A Journey level whose own picture (journey3.jpg, ...) hasn't been
    added yet borrows the first picture of its theme (architecture1.jpg,
    ...), so the map and the puzzle aren't full of blank placeholders.
    Runs once at startup - a picture added later is picked up next launch."""
    for level in journey.JOURNEY_ALL:
        if find_level_image_file(level["image"]) is None:
            fallback = level.get("fallback_image")
            if fallback and find_level_image_file(fallback) is not None:
                level["image"] = fallback


# --------------------------------------------------
# Game state
# --------------------------------------------------

current_screen = "title"
puzzle = None
selected_piece = None
current_level = LEVELS[0]

# sidebar (shared across every screen)
nav_rects = {}
logo_rect = None

# "Are you sure you want to exit?" dialog (opened by the sidebar's EXIT)
exit_confirm_open = False
exit_confirm_rects = {}

# Daily Challenge page
daily_play_button = None

# Spaces (PLAY / COLLECTION): which tab each one was last showing, and the
# clickable tab rectangles drawn this frame (see draw_tabs)
space_last_screen = {"play": "main_menu", "collection": "collection"}
SPACE_OF_SCREEN = {
    "menu": "play", "levels": "play", "daily": "play",
    "collection": "collection"
}
tab_rects = {}

# title screen (no sidebar - its own full-bleed layout)
title_button_scale = {
    "play": 1.0,
    "collection": 1.0,
    "achievements": 1.0,
    "settings": 1.0,
    "exit": 1.0,
}

# A short, hand-written list of recent changes for the title screen's
# "what's new" pill - newest first. Just add a line here when something
# worth mentioning ships; the title screen always shows entry 0.
WHATS_NEW = [
    "Version 0.7 · A cleaner greeting hub is here!",
    "New: the Journey mode - one tower, six puzzles, one secret finale",
    "3 new piece trays to choose from - Pile, Wheel and Carousel",
]

# welcome screen (first launch only, until a name is saved)
welcome_name_input = ""
welcome_button = None
welcome_picture_button = None
welcome_started_at = time.time()
welcome_step = 0
unlock_code_buffer = ""

# per-screen buttons
play_now_button = None
resume_button = None
back_button = None
gear_button = None
hint_button = None
shuffle_button = None
carousel_shuffle_button = None
powerup_notice = None       # (text, show-until timestamp) - e.g. "Not enough coins"
hint_active = False
hint_used_this_level = False    # tracks the current level, for the "no hints" achievement
tray_scroll_dragging = False
tray_scroll_last_x = 0
achievements_scroll_y = 0   # pixels scrolled down the Achievements grid
play_again_button = None
menu_button = None
next_level_button = None

# Levels gallery click targets
category_card_rects = []
levels_scroll_x = 0
levels_scroll_max = 0
levels_viewport_rect = None
selected_category_key = None
category_level_card_rects = []
category_level_back_rect = None
achievements_back_rect = None   # the white BACK pill at the foot of the Achievements page
achievement_reward_rects = []
rewards_back_rect = None
reward_card_rects = []
rewards_entry_rect = None
gallery_back_rect = None

# The Journey map (a full-screen page: clickable circles, no sidebar)
journey_node_rects = []
journey_back_rect = None

# Where the puzzle on screen was opened from, so the back arrow returns
# to the right page.
puzzle_origin = "levels"

# puzzle screen: pause overlay (opened via the gear icon or Esc)
puzzle_paused = False
pause_started_at = None
pause_button_rects = {}

# settings screen
VERSION = "0.8"
SETTINGS_FILE = save_manager.app_path("settings.json")
DEFAULT_BOARD_OPACITY = 45 / 255
DEFAULT_HEADER_STYLE = "classic"

settings = {
    "music_volume": 0.7,
    "sfx_volume": 0.8,
    "mute_all": False,
    "board_opacity": DEFAULT_BOARD_OPACITY,  # how visible the faint reference image is
                                # behind the board while solving - see
                                # apply_board_opacity(). Default matches
                                # what used to be a fixed value.
    "resolution": "1080p",
    "quality": True,
    "dark_mode": False,
    "theme": "mint",          # one of ui.THEME_ORDER
    "tray_style": "pile",     # bottom tray while solving: "pile", "wheel" or "carousel"
    "show_hint": True,        # show the lightbulb hint button while solving
    "fullscreen": False,      # F11 or the Fullscreen switch in Settings
    "header_style": DEFAULT_HEADER_STYLE,  # the puzzle screen's top bar: "classic" or "minimal"
    "sidebar_position": "left",  # which edge the icon dock sits on ("left" or "right")
    "wallpaper": None,        # name of an unlocked level whose photo is the
                              # menu-page background, or None for the plain theme look
}
# Window sizes on offer (windowed mode). Only the ones that fit the player's
# monitor are shown - see available_resolutions().
RESOLUTION_SIZES = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4K": (3840, 2160),
}
RESOLUTIONS = list(RESOLUTION_SIZES)
TRAY_STYLES = ["pile", "wheel", "carousel"]
HEADER_STYLES = ["classic", "minimal"]
SIDEBAR_POSITIONS = ["left", "right"]

# The one option in each of these lists that's always available, reward
# or no reward - what a locked setting falls back to (see
# normalize_settings_for_rewards()).
DEFAULT_TRAY_STYLE = TRAY_STYLES[0]
DEFAULT_THEME = ui.THEME_ORDER[0]

settings_rects = {}
settings_dropdown_open = False
settings_dropdown_rects = []
settings_dragging_slider = None
settings_return_screen = "title"    # where the BACK button goes
settings_section = "audio"          # which category button is highlighted
settings_show_version = False
reset_progress_armed = False
reset_flash_until = 0               # "Progress reset" message timer
profile_name_editing = False
profile_name_draft = ""
profile_picture_cache = {"path": None, "image": None}


def load_settings():
    """Reads settings.json (if it exists) so choices survive restarts."""
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)
    except (OSError, ValueError):
        return

    if not isinstance(saved, dict):
        return

    for key in ("music_volume", "sfx_volume", "board_opacity"):
        if isinstance(saved.get(key), (int, float)):
            settings[key] = max(0.0, min(1.0, float(saved[key])))
    for key in ("mute_all", "quality", "dark_mode", "show_hint", "fullscreen"):
        if isinstance(saved.get(key), bool):
            settings[key] = saved[key]
    if saved.get("resolution") in RESOLUTIONS:
        settings["resolution"] = saved["resolution"]
    if saved.get("theme") in list(ui.THEMES):
        settings["theme"] = saved["theme"]
    if saved.get("tray_style") in TRAY_STYLES:
        settings["tray_style"] = saved["tray_style"]
    if saved.get("header_style") in HEADER_STYLES:
        settings["header_style"] = saved["header_style"]
    if saved.get("sidebar_position") in SIDEBAR_POSITIONS:
        settings["sidebar_position"] = saved["sidebar_position"]
    if saved.get("wallpaper") is None or isinstance(saved.get("wallpaper"), str):
        # Whether it's still a real, still-earned level is re-checked every
        # frame (active_wallpaper_path) - completed_level_names isn't
        # loaded yet this early in startup.
            old_wallpaper = saved.get("wallpaper")
            wallpaper = LEGACY_LEVEL_NAME_MAP.get(old_wallpaper, old_wallpaper)
            valid_level_names = {level["name"] for level in LEVELS + journey.JOURNEY_ALL}
            if wallpaper not in valid_level_names:
                wallpaper = None
            settings["wallpaper"] = wallpaper
            if wallpaper != old_wallpaper:
                save_settings()


def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
            json.dump(settings, file, indent=2)
    except OSError:
        pass


def apply_board_opacity():
    """Pushes settings["board_opacity"] onto the live puzzle's faint
    reference backdrop, if one exists right now. Surface.set_alpha() is
    a cheap, live blit-time property - not baked into the image's own
    pixels - so this can run on every slider move with nothing to
    rebuild, and takes effect immediately even if the puzzle is only
    paused behind the Settings screen rather than actually being drawn
    this instant."""
    if puzzle is not None:
        puzzle.blurred_backdrop.set_alpha(round(settings["board_opacity"] * 255))


# --------------------------------------------------
# Display: window size, fullscreen, scaling the canvas to fit
# --------------------------------------------------
# `screen` (1440x900) is only a canvas. The real window is `window`, and it
# can be any size. present_frame() stretches the canvas to exactly fill the
# window (not fit inside it keeping its own shape, which would leave dead
# bars down the sides or top/bottom that a piece could never actually
# reach), and window_to_canvas() turns mouse positions in the window back
# into canvas positions, so every click and hover in the game keeps
# working unchanged.

view_scale_x = 1.0                # canvas -> window scale factor, horizontal
view_scale_y = 1.0                # canvas -> window scale factor, vertical
view_offset = (0, 0)              # where the scaled canvas starts in the window
view_size = (WIDTH, HEIGHT)       # size of the scaled canvas in the window
_scaled_buffer = None             # reused every frame instead of re-allocated
_real_mouse_get_pos = pygame.mouse.get_pos


def window_to_canvas(pos):
    return (
        int((pos[0] - view_offset[0]) / view_scale_x),
        int((pos[1] - view_offset[1]) / view_scale_y),
    )


# Every hover check in main.py and ui.py calls pygame.mouse.get_pos(), so
# swapping it here converts them all at once.
pygame.mouse.get_pos = lambda: window_to_canvas(_real_mouse_get_pos())


def resolution_label(key):
    """'1080p' -> '1080p  ·  1920×1080' for the option list."""
    width, height = RESOLUTION_SIZES[key]
    return f"{key}  \u00b7  {width}\u00d7{height}"


def desktop_size():
    try:
        return pygame.display.get_desktop_sizes()[0]
    except (AttributeError, IndexError, pygame.error):
        return (1920, 1080)


def available_resolutions():
    """The presets no bigger than this monitor. Never empty."""
    desktop_w, desktop_h = desktop_size()
    fits = [
        key for key, (w, h) in RESOLUTION_SIZES.items()
        if w <= desktop_w and h <= desktop_h
    ]
    return fits or [RESOLUTIONS[0]]


def windowed_size():
    """The window size for the chosen preset. If the preset is as big as
    the whole monitor (1080p on a 1080p screen) it is trimmed just enough
    to leave room for the title bar and taskbar - use Fullscreen to fill
    the screen completely."""
    width, height = RESOLUTION_SIZES[settings["resolution"]]
    desktop_w, desktop_h = desktop_size()
    shrink = min(1.0, desktop_w / width, (desktop_h - 100) / height)
    return max(640, int(width * shrink)), max(400, int(height * shrink))


def update_view():
    """Works out how the canvas maps onto whatever window currently
    exists. The canvas is stretched to fill the window exactly - not
    fit inside it keeping its own 8:5 shape - so there's never a dead
    strip down the sides or across the top/bottom that a piece can be
    dragged toward but can never actually reach. On a window shaped
    differently from 8:5 this stretches the picture very slightly
    (pieces a touch wider or taller than perfectly round); the trade
    is a window that's genuinely usable edge to edge instead of one
    with disguised dead space."""
    global view_scale_x, view_scale_y, view_offset, view_size, _scaled_buffer

    window_w, window_h = window.get_size()
    view_scale_x = window_w / WIDTH
    view_scale_y = window_h / HEIGHT
    view_size = (window_w, window_h)
    view_offset = (0, 0)
    _scaled_buffer = None


def open_window():
    """(Re)creates the real window from the current settings: fullscreen
    at the monitor's own resolution, or a window of the chosen size."""
    global window

    if settings["fullscreen"]:
        window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        window = pygame.display.set_mode(windowed_size())

    window.fill((0, 0, 0))
    update_view()


def apply_resolution():
    """Called after a new resolution is picked. In fullscreen the monitor
    decides the size, so the choice waits until the player leaves it."""
    if not settings["fullscreen"]:
        open_window()


def set_fullscreen(on):
    """Switch between windowed and fullscreen."""
    if on == settings["fullscreen"]:
        return

    settings["fullscreen"] = on
    save_settings()
    open_window()


def present_frame():
    """Shows the finished canvas, stretched to exactly fill the window,
    then flipped."""
    global _scaled_buffer

    if view_size == (WIDTH, HEIGHT):
        window.blit(screen, (0, 0))
    else:
        if _scaled_buffer is None:
            _scaled_buffer = pygame.Surface(view_size).convert()

        # Smooth scaling looks best; above ~4.5 million pixels (4K) it costs
        # too much time per frame, so the fast plain scaler takes over.
        if view_size[0] * view_size[1] > 4_500_000:
            pygame.transform.scale(screen, view_size, _scaled_buffer)
        else:
            try:
                pygame.transform.smoothscale(screen, view_size, _scaled_buffer)
            except ValueError:
                pygame.transform.scale(screen, view_size, _scaled_buffer)

        window.blit(_scaled_buffer, (0, 0))

    pygame.display.flip()


load_settings()
ui.apply_theme(settings["theme"])
ui.apply_appearance(settings["dark_mode"])

# A saved size that doesn't fit this monitor (say the game was last used on
# a bigger screen) falls back to the largest one that does.
_fitting_resolutions = available_resolutions()
if settings["resolution"] not in _fitting_resolutions:
    settings["resolution"] = _fitting_resolutions[-1]

open_window()



# --------------------------------------------------
# Timer
# --------------------------------------------------

puzzle_start_time = None
puzzle_end_time = None
final_time = 0
confetti_particles = []


def init_confetti():
    global confetti_particles
    palette = [(255, 209, 102), (6, 214, 160), (17, 138, 178), (239, 71, 111), (155, 93, 229)]
    confetti_particles = [
        {
            "x": random.uniform(0, WIDTH),
            "y": random.uniform(-HEIGHT, 0),
            "speed": random.uniform(40, 90),
            "size": random.uniform(6, 12),
            "color": random.choice(palette),
            "sway": random.uniform(0, 6.28),
        }
        for _ in range(28)
    ]


def update_confetti(dt):
    for p in confetti_particles:
        p["y"] += p["speed"] * dt
        p["sway"] += dt * 2
        if p["y"] > HEIGHT:
            p["y"] = random.uniform(-120, -20)
            p["x"] = random.uniform(0, WIDTH)


def draw_confetti():
    for p in confetti_particles:
        x = p["x"] + math.sin(p["sway"]) * 14
        rect = pygame.Rect(0, 0, p["size"], p["size"] * 1.6)
        rect.center = (x, p["y"])
        pygame.draw.rect(screen, p["color"], rect, border_radius=2)


# --------------------------------------------------
# Create puzzle
# --------------------------------------------------

# Building a puzzle cuts every piece out of the picture, which takes a
# moment - a few seconds for the 768-piece Ultimate. Bigger puzzles show a
# loading bar while that happens, so the window never just looks frozen.
LOADING_SCREEN_MIN_PIECES = 100


# --------------------------------------------------
# Stars
# --------------------------------------------------
# A star rating for ONE completed attempt - performance, not difficulty
# (that's difficulty_rating, above: how hard the puzzle IS, fixed by its
# piece count, shown before you start). Stars are about how well you
# personally did on this particular clear: fast without help earns all
# three; using the hint caps it at two, since the puzzle wasn't solved
# unaided; anything else that still finishes always earns at least one.
#
# The "how fast is fast" bar itself is what actually differs per
# puzzle, and it scales with piece count for exactly the same reason
# coins_for_completion (below) does: a 12-piece puzzle and a 384-piece
# puzzle can't share one flat time and have it mean anything for both.
STAR_SECONDS_PER_PIECE = (3.0, 6.0)   # (3-star cutoff, 2-star cutoff)


def star_rating(level, seconds, hint_used):
    """1, 2 or 3 stars for finishing `level` in `seconds`, with or
    without a hint."""
    piece_count = level["columns"] * level["rows"]
    fast_cutoff, medium_cutoff = (piece_count * t for t in STAR_SECONDS_PER_PIECE)

    if seconds <= fast_cutoff:
        stars = 3
    elif seconds <= medium_cutoff:
        stars = 2
    else:
        stars = 1

    if hint_used:
        stars = min(stars, 2)

    return stars


def coins_for_completion(piece_count, stars):
    """What a level is worth in total at a given star rating - the same
    flat-plus-piece-count base as before, now scaled by performance, so
    doing better on a puzzle is worth more, not just finishing it. 0
    stars (not actually reachable - even 1 star always pays something)
    is worth nothing, so the completion handler below can always pay
    just the DIFFERENCE between the new best and the old one, first
    clear included (old best starts at 0 stars = 0 coins), without a
    separate "is this the first time" case."""
    if stars <= 0:
        return 0
    base = 10 + piece_count // 4
    return base * stars


# What each power-up costs. Coins are only paid out on a first clear
# (see coins_for_completion), so these are kept small - tune freely.
POWERUP_COSTS = {"hint": 5, "shuffle": 3}


def try_spend_powerup(kind):
    """Pays for one use of a power-up. False (with a short on-screen
    note) if the player can't afford it."""
    global powerup_notice

    cost = POWERUP_COSTS[kind]
    if save_data["coins"] < cost:
        powerup_notice = ("Not enough coins", time.time() + 1.8)
        return False

    save_manager.add_coins(save_data, -cost)
    save_manager.save(save_data)
    return True


def show_loading(fraction):
    """Draws one 'loading' frame (and keeps the window responsive)."""
    pygame.event.pump()

    ui.draw_background(screen)

    panel = pygame.Rect(0, 0, 440, 170)
    panel.center = (WIDTH // 2, HEIGHT // 2)
    ui.draw_frosted_panel(screen, panel, radius=28)

    ui.draw_tracked_text(
        screen, "LOADING", title_font, ui.TEXT,
        panel.centerx, panel.top + 62, tracking=3
    )

    track = pygame.Rect(panel.left + 44, panel.top + 116, panel.width - 88, 10)
    ui.draw_smooth_rect(screen, track, ui.TRACK_BACKGROUND, radius=5)

    fill = pygame.Rect(track.left, track.top, max(track.height, int(track.width * fraction)), track.height)
    ui.draw_gradient_rect(
        screen, fill, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=5
    )

    present_frame()


def create_puzzle(columns, rows, image_path):
    tray_style = settings["tray_style"]

    # The carousel is a single thin row of upright pieces rather than a
    # deep dish, so it gets its own (much shorter) tray height - and the
    # board grows to fill the height that frees up, same as it would for
    # any other tray height.
    tray_height = (
        ui.PUZZLE_CAROUSEL_TRAY_HEIGHT if tray_style == "carousel" else ui.PUZZLE_TRAY_HEIGHT
    )

    image = load_level_image(image_path)
    board = ui.get_puzzle_board(tray_height)

    # Calculate scaling to fit within the board while maintaining proportions
    img_w, img_h = image.get_size()
    board_ratio = board.width / board.height
    img_ratio = img_w / img_h

    if img_ratio > board_ratio:
        new_w = board.width
        new_h = int(new_w / img_ratio)
    else:
        new_h = board.height
        new_w = int(new_h * img_ratio)

    image = pygame.transform.smoothscale(image, (new_w, new_h))

    # Center the dynamically scaled puzzle board 
    offset_x = board.left + (board.width - new_w) // 2
    offset_y = board.top + (board.height - new_h) // 2
    actual_board = pygame.Rect(offset_x, offset_y, new_w, new_h)

    # The tray takes the bottom row to the right of the POWER-UPS panel.
    piece_area = ui.get_tray_area(tray_height)

    progress = show_loading if columns * rows >= LOADING_SCREEN_MIN_PIECES else None

    # A hair of a margin in from the literal window edge - just enough
    # that a piece never sits flush against the glass or renders right
    # on the display surface's exact boundary (a dragged piece has been
    # seen to come out as a stretched, garbled shape exactly at pixel 0
    # or the far edge). Kept as small as it can be so almost the whole
    # window is usable for spreading pieces out - if that edge glitch
    # ever reappears, nudge this back up rather than removing it.
    edge_margin = 2
    bounds = pygame.Rect(0, 0, WIDTH, HEIGHT).inflate(-edge_margin * 2, -edge_margin * 2)

    puzzle_obj = Puzzle(
        image,
        columns=columns,
        rows=rows,
        board_rect=actual_board,
        piece_area=piece_area,
        tray_style=tray_style,
        progress=progress,
        bounds=bounds
    )
    puzzle_obj.blurred_backdrop.set_alpha(round(settings["board_opacity"] * 255))
    return puzzle_obj


# --------------------------------------------------
# Start level
# --------------------------------------------------

def start_level(
    level,
    fresh=False
):
    """Builds the puzzle for `level` and switches to the puzzle screen.

    Normally this picks up whatever was saved for the level (placed
    pieces, the clock, whether a hint was used). With fresh=True - used
    by RESTART LEVEL - the saved attempt is wiped first, so it really
    starts from zero."""
    global puzzle
    global current_level
    global current_screen
    global puzzle_start_time
    global puzzle_end_time
    global final_time
    global puzzle_paused
    global pause_started_at
    global hint_used_this_level

    current_level = level
    puzzle = create_puzzle(
        level["columns"],
        level["rows"],
        level["image"]
    )

    # Clicks made while a big puzzle was loading shouldn't land on it.
    pygame.event.clear(pygame.MOUSEBUTTONDOWN)

    entry = save_manager.level_entry(save_data, level["name"])
    if fresh:
        save_manager.clear_progress(entry)

    # If this level has an unfinished attempt saved, drop those pieces
    # straight into place and pick the clock (and the hint flag) back up
    # where they were - this is what makes leaving mid-puzzle, even
    # closing the app, safe. A finished level being replayed starts clean.
    resumed_elapsed = 0.0
    hint_used_this_level = False

    if not entry["completed"]:
        saved_cells = set(entry["snapped_cells"])
        for piece in puzzle.pieces:
            if (piece.col, piece.row) in saved_cells:
                piece.position = pygame.Vector2(piece.correct_position)
                piece.in_tray = False
                piece.is_snapped = True
        resumed_elapsed = entry["elapsed"]
        hint_used_this_level = entry["hint_used"]

    puzzle_start_time = time.time() - resumed_elapsed
    puzzle_end_time = None
    final_time = 0
    current_screen = "puzzle"
    puzzle_paused = False
    pause_started_at = None

    entry["grid"] = [level["columns"], level["rows"]]
    save_data["last_level"] = level["name"]
    save_manager.save(save_data)


# --------------------------------------------------
# Leaving / re-entering the puzzle screen
# --------------------------------------------------

def resume_puzzle_clock():
    """Un-freezes the clock. The time spent away (in the pause menu or
    in the level menu) is added onto the start time, so it never counts
    against the player."""
    global puzzle_paused, pause_started_at, puzzle_start_time

    if pause_started_at is not None:
        puzzle_start_time += time.time() - pause_started_at
    pause_started_at = None
    puzzle_paused = False


def show_level_list_for(level):
    """Returns puzzle play to the relevant mode gallery."""
    global current_screen

    if "journey_index" in level:
        current_screen = "journey"
    elif puzzle_origin == "category":
        current_screen = "category"
    else:
        current_screen = "menu"


def origin_for(level):
    """Which page a puzzle's back arrow should return to: the Daily
    Challenge page, the Journey map, or wherever normal category
    browsing left off. (A Journey level says so itself; "daily" vs
    "levels" isn't visible from the level - a daily puzzle is just an
    ordinary category level played from another page - hence the
    current_screen check.)"""
    global selected_category_key

    if current_screen == "daily":
        return "daily"
    if "journey_index" in level:
        return "journey"
    if current_screen == "category" or puzzle_origin == "category":
        selected_category_key = level["category"]
        return "category"
    return "levels"


def leave_puzzle():
    """Back to the level menu from the puzzle screen (the back arrow, or
    QUIT TO MENU in the pause panel). Freezes the clock at this exact
    moment and writes everything to disk, so nothing about the attempt
    can be lost or drift while the player is elsewhere."""
    global current_screen, selected_piece, puzzle_paused, pause_started_at

    if puzzle is not None and not puzzle.is_complete():
        if not puzzle_paused:
            puzzle_paused = True
            pause_started_at = time.time()
        persist_puzzle_progress()

    selected_piece = None
    if puzzle_origin == "daily":
        current_screen = "daily"
    else:
        show_level_list_for(current_level)


def open_level(level):
    """Opens a level from the menu, the daily page or RESUME. If that
    exact puzzle is still sitting in memory from this session (same
    level, unfinished, same tray style), it's switched straight back to
    with the clock un-frozen; otherwise it's rebuilt from the save."""
    global current_screen, puzzle_origin

    puzzle_origin = origin_for(level)

    already_live = (
        puzzle is not None
        and current_level is not None
        and current_level["name"] == level["name"]
        and not puzzle.is_complete()
        and puzzle.tray_style == settings["tray_style"]
    )

    if already_live:
        resume_puzzle_clock()
        current_screen = "puzzle"
    else:
        start_level(level)


def next_level_after(level):
    """The puzzle the win screen's primary button should open next, or
    None if `level` is the last one currently available.

    Journey levels are gated in order by journey.py, so they get their
    own branch: ask it what comes next and whether it's actually open yet
    (the hidden finale isn't until the whole tower is climbed).

    Category levels use the flat LEVELS list, built category by
    category, so this is normally just "the next entry" - except for the
    last regular puzzle (Alice 10), whose "next" entry is the hidden
    Ultimate, which only counts once it's actually unlocked.
    """
    if "journey_index" in level:
        index = level["journey_index"]
        if index >= len(journey.JOURNEY_ALL):
            return None

        candidate = journey.JOURNEY_ALL[index]
        return candidate if journey.is_unlocked(save_data, candidate) else None

    available_levels = available_regular_levels(save_data) + [ULTIMATE_LEVEL]
    try:
        index = next(i for i, item in enumerate(available_levels) if item["name"] == level["name"]) + 1
    except StopIteration:
        return None

    if index >= len(available_levels):
        return None
    candidate = available_levels[index]
    if candidate.get("hidden") and not is_ultimate_unlocked(save_data):
        return None

    return candidate


# --------------------------------------------------
# Format timer
# --------------------------------------------------

def format_time(
    seconds
):
    seconds = int(
        seconds
    )
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"


# --------------------------------------------------
# Current timer
# --------------------------------------------------

def get_current_time():
    if puzzle_start_time is None:
        return 0

    if puzzle_end_time is not None:
        return final_time

    if puzzle_paused and pause_started_at is not None:
        # Freeze the displayed time at the instant pause was pressed
        # instead of letting it keep ticking in the background.
        return pause_started_at - puzzle_start_time

    return (
        time.time()
        - puzzle_start_time
    )


# --------------------------------------------------
# Buttons
# --------------------------------------------------

def draw_button(
    rect,
    color,
    text,
    text_color=None
):
    mouse_position = pygame.mouse.get_pos()
    hovered = rect.collidepoint(
        mouse_position
    )

    draw_color = color
    if hovered:
        draw_color = tuple(
            min(
                255,
                value + 12
            )
            for value in color
        )

    ui.draw_smooth_rect(screen, rect, draw_color, radius=18)

    ui.draw_text(
        screen,
        text,
        button_font,
        text_color or ui.TEXT,
        rect.centerx,
        rect.centery
    )


def draw_gradient_button(
    rect,
    color_a,
    color_b,
    text,
    text_color=None
):
    mouse_position = pygame.mouse.get_pos()
    hovered = rect.collidepoint(mouse_position)
    
    # Soft blurred shadow (blue-tinted, matching the rest of the UI) instead
    # of hard concentric rings.
    ui.draw_blurred_shadow(
        screen,
        rect,
        border_radius=20,
        blur=12,
        alpha=75 if hovered else 60,
        color=(120, 140, 200),
        offset=(0, 6 if not hovered else 8)
    )

    ui.draw_gradient_rect(
        screen,
        rect,
        color_a,
        color_b,
        border_radius=20
    )

    # A light sheen on top keeps the gradient CTA in the same "glass"
    # family as the rest of the puzzle screen's buttons and pills.
    ui.draw_glass_sheen(screen, rect, radius=20)

    ui.draw_text(
        screen,
        text,
        button_font,
        text_color or ui.WHITE,
        rect.centerx,
        rect.centery
    )


def draw_glass_button(rect, text, radius=18):
    """A secondary button in the same translucent-glass style as the
    puzzle screen's header pills, instead of a flat opaque fill."""
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    ui.draw_glass(screen, rect, radius=radius, tint=(*ui.WHITE, 190), hovered=hovered)
    ui.draw_text(screen, text, button_font, ui.TEXT, rect.centerx, rect.centery)


def draw_back_link(
    content,
    text="← BACK"
):
    rect = pygame.Rect(
        content.left + 40,
        36,
        150,
        44
    )

    draw_button(
        rect,
        ui.WHITE,
        text
    )

    return rect


# --------------------------------------------------
# Title screen (splash) - full-bleed, no sidebar
# --------------------------------------------------

def get_title_button_rects():
    center_x = WIDTH // 2

    button_width = 300
    button_height = 52
    first_y = 270
    gap = 14

    play_rect = pygame.Rect(0, 0, button_width, button_height)
    play_rect.center = (center_x, first_y)

    collection_rect = pygame.Rect(0, 0, button_width, button_height)
    collection_rect.center = (center_x, first_y + (button_height + gap))

    achievements_rect = pygame.Rect(0, 0, button_width, button_height)
    achievements_rect.center = (center_x, first_y + 2 * (button_height + gap))

    settings_rect = pygame.Rect(0, 0, button_width, button_height)
    settings_rect.center = (center_x, first_y + 3 * (button_height + gap))

    exit_rect = pygame.Rect(0, 0, button_width, button_height)
    exit_rect.center = (center_x, first_y + 4 * (button_height + gap))

    return {
        "play": play_rect,
        "collection": collection_rect,
        "achievements": achievements_rect,
        "settings": settings_rect,
        "exit": exit_rect,
    }


def scaled_rect(rect, scale):
    return rect.inflate(rect.width * (scale - 1), rect.height * (scale - 1))


def draw_title_primary_button(rect, scale, text):
    grown = scaled_rect(rect, scale)

    # More glow the further into the hover animation it is, so the growth
    # reads as "lighting up" rather than just resizing.
    glow_alpha = int(60 + (scale - 1.0) * 500)

    ui.draw_blurred_shadow(
        screen, grown, border_radius=22, blur=16,
        alpha=max(50, min(140, glow_alpha)),
        color=(110, 150, 210), offset=(0, 8)
    )
    ui.draw_gradient_rect(screen, grown, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=22)
    ui.draw_text(screen, text, button_font, ui.TEXT, grown.centerx, grown.centery)


def draw_title_secondary_button(rect, scale, text):
    grown = scaled_rect(rect, scale)

    ui.draw_blurred_shadow(
        screen, grown, border_radius=18, blur=10,
        alpha=35 + int((scale - 1.0) * 300),
        color=ui.CARD_SHADOW, offset=(0, 6)
    )
    ui.draw_smooth_rect(screen, grown, ui.WHITE, radius=18)
    ui.draw_smooth_rect(screen, grown, ui.CARD_BORDER, radius=18, width=1)
    ui.draw_text(screen, text, button_font, ui.TEXT, grown.centerx, grown.centery)


def draw_main_menu_hub():
    """The MAIN MENU hub page. All the drawing and hit-testing lives in
    main_menu.py - this just hands it the screen, the ui module, the page
    area and the fonts."""
    _fonts = globals()
    main_menu.draw(
        screen, ui, ui.get_content_rect(),
        {
            "title": _fonts.get("title_font"),
            "heading": _fonts.get("heading_font") or _fonts.get("header_font"),
            "subtitle": _fonts.get("header_font") or _fonts.get("subtitle_font"),
            "button": _fonts.get("button_font"),
            "small": _fonts.get("small_font"),
        },
        visible_actions=visible_play_actions(),
    )


def draw_shop_screen():
    _fonts = globals()
    catalog = {
        "level_packs": LEVEL_PACK_CATEGORIES,
        "levels": ALL_REGULAR_LEVELS + journey.JOURNEY_ALL,
        "load_thumbnail": load_level_thumbnail,
        "has_image": lambda path: find_level_image_file(path) is not None,
        "wallpaper": settings.get("wallpaper"),
    }
    shop.draw(
        screen, ui, ui.get_content_rect(),
        {
            "title": _fonts.get("title_font"),
            "heading": _fonts.get("header_font") or _fonts.get("heading_font"),
            "subtitle": _fonts.get("subtitle_font"),
            "button": _fonts.get("button_font"),
            "small": _fonts.get("small_font"),
        },
        save_data,
        settings["theme"],
        catalog=catalog,
    )


def draw_title_info_panel(rect, title, lines):
    """Draw a compact live-information panel for the greeting screen."""
    ui.draw_glass(screen, rect, radius=22, tint=(*ui.WHITE, 190))
    ui.draw_text(screen, title, small_font, ui.MUTED_TEXT, rect.left + 22, rect.top + 18, center=False)
    for index, (label, value) in enumerate(lines):
        y = rect.top + 52 + index * 30
        ui.draw_text(screen, label, small_font, ui.MUTED_TEXT, rect.left + 22, y, center=False)
        value_surface = button_font.render(value, True, ui.TEXT)
        screen.blit(value_surface, (rect.right - 22 - value_surface.get_width(), y))


def choose_profile_picture():
    """Open the native file picker and persist a user-selected avatar path."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="Choose profile picture",
            filetypes=[
                ("Image files", "*.png *.PNG *.jpg *.JPG *.jpeg *.JPEG *.webp *.WEBP"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
    except Exception:
        return False

    if path:
        save_data["profile_picture"] = os.path.abspath(path)
        profile_picture_cache["path"] = None
        profile_picture_cache["image"] = None
        save_manager.save(save_data)
        return True
    return False


def load_profile_picture(size):
    path = save_data.get("profile_picture")
    if not path or not os.path.exists(path):
        return None
    if profile_picture_cache["path"] != path:
        try:
            image = pygame.image.load(path).convert_alpha()
            scaled = pygame.transform.smoothscale(image, (size, size))
            profile_picture_cache["image"] = scaled.convert_alpha()
            profile_picture_cache["path"] = path
        except (pygame.error, OSError):
            profile_picture_cache["path"] = path
            profile_picture_cache["image"] = None
    return profile_picture_cache["image"]


def title_greeting(name):
    """Choose a friendly greeting from the current local time."""
    hour = time.localtime().tm_hour
    if hour < 6:
        greetings = ("Still solving, {name}?", "Late-night puzzles, {name}?")
    elif hour < 12:
        greetings = ("Good morning, {name}", "Hello, {name}", "A bright start, {name}")
    elif hour < 17:
        greetings = ("Hi, {name}", "Hey, {name}", "What's up, {name}?")
    elif hour < 22:
        greetings = ("Good evening, {name}", "Welcome back, {name}", "Evening, {name}")
    else:
        greetings = ("Quiet night, {name}?", "Welcome back, {name}")
    return greetings[hour % len(greetings)].format(name=name)


def draw_title_screen():
    center_x = WIDTH // 2

    ui.draw_floating_pieces(screen)

    name = save_data.get("player_name") or "there"
    greeting = title_greeting(name)
    profile_image = load_profile_picture(54)
    greeting_surface = heading_font.render(greeting, True, ui.TEXT)
    if profile_image is not None:
        group_width = 54 + 14 + greeting_surface.get_width()
        image_rect = pygame.Rect(0, 0, 54, 54)
        image_rect.left = center_x - group_width // 2
        image_rect.top = 188 - image_rect.height // 2
        ui.draw_image_rounded(screen, profile_image, image_rect, radius=27)
        text_rect = greeting_surface.get_rect(midleft=(image_rect.right + 14, 188))
        screen.blit(greeting_surface, text_rect)
    else:
        screen.blit(greeting_surface, greeting_surface.get_rect(center=(center_x, 188)))

    ui.draw_tracked_text(
        screen, "PUZZLESCAPE", hero_font, ui.TEXT,
        center_x, 110, tracking=6
    )

    rects = get_title_button_rects()
    draw_title_primary_button(rects["play"], title_button_scale["play"], "PLAY")
    draw_title_secondary_button(rects["collection"], title_button_scale["collection"], "COLLECTION")
    draw_title_secondary_button(rects["achievements"], title_button_scale["achievements"], "ACHIEVEMENTS")
    draw_title_secondary_button(rects["settings"], title_button_scale["settings"], "SETTINGS")
    draw_title_secondary_button(rects["exit"], title_button_scale["exit"], "EXIT")

    puzzles_solved = sum(1 for entry in save_data["levels"].values() if entry["completed"])
    streak = save_manager.current_streak(save_data)
    unlocked_n = achievements.unlocked_count(save_data)
    total_n = achievements.available_count()
    recent = achievements.most_recent_unlock(save_data)
    recent_title = recent["title"].title() if recent else "No reward yet"
    draw_title_info_panel(
        pygame.Rect(1160, 180, 340, 150),
        "PROGRESS",
        (
            ("CURRENT STREAK", f"{streak} days"),
            ("DAILY COMPLETED", str(daily_stats["completed"])),
            ("RECENT REWARD", recent_title),
        ),
    )

    draw_title_info_panel(
        pygame.Rect(1160, 350, 340, 150),
        "PLAYER STATS",
        (
            ("PUZZLES SOLVED", str(puzzles_solved)),
            ("ACHIEVEMENTS", f"{unlocked_n}/{total_n}"),
            ("COINS", f"{save_data['coins']}"),
        ),
    )
    draw_title_info_panel(
        pygame.Rect(1160, 520, 340, 150),
        "LATEST UPDATE",
        (
            ("VERSION", VERSION),
            ("LATEST", "New greeting hub"),
            ("NEXT", "More worlds ahead"),
        ),
    )

    version_pill = pygame.Rect(0, 0, 132, 32)
    version_pill.center = (center_x, 820)
    ui.draw_glass(screen, version_pill, radius=16, tint=(*ui.WHITE, 205))
    ui.draw_text(screen, f"VERSION {VERSION}", small_font, ui.TEXT, version_pill.centerx, version_pill.centery)


# --------------------------------------------------
# Welcome screen (first launch only, until a name is saved)
# --------------------------------------------------

def get_welcome_button_rect():
    rect = pygame.Rect(0, 0, 280, 56)
    rect.center = (WIDTH // 2, 735)
    return rect


def get_welcome_input_rect():
    rect = pygame.Rect(0, 0, 420, 58)
    rect.center = (WIDTH // 2, 442)
    return rect


def get_welcome_picture_button_rect():
    rect = pygame.Rect(0, 0, 280, 48)
    rect.center = (WIDTH // 2, 520)
    return rect


def draw_welcome_screen():
    global welcome_button, welcome_picture_button

    screen.fill((250, 252, 253))
    rects = onboarding.draw(
        screen,
        ui,
        {
            "hero": hero_font,
            "heading": heading_font,
            "subtitle": subtitle_font,
            "button": button_font,
            "small": small_font,
        },
        {
            "step": welcome_step,
            "name": welcome_name_input,
            "profile_picture": save_data.get("profile_picture"),
            "started_at": welcome_started_at,
        },
        time.time(),
    )
    welcome_button = rects.get("action")
    welcome_picture_button = rects.get("picture")


def advance_welcome():
    global welcome_step, welcome_started_at

    if welcome_step == 2 and not welcome_name_input.strip():
        return
    if welcome_step >= onboarding.PAGE_COUNT - 1:
        confirm_welcome_name()
        return
    welcome_step += 1
    welcome_started_at = time.time()


def confirm_welcome_name():
    """Saves whatever name (or the "Player" fallback) and moves on to the
    title screen - shared by pressing Enter and clicking the button."""
    global current_screen

    chosen_name = welcome_name_input.strip() or "Player"
    save_manager.set_player_name(save_data, chosen_name)
    if chosen_name.casefold() == "alice":
        save_data["coins"] += 300
        queue_toasts(
            [{"title": "Alice's Welcome Gift", "icon": "trophy"}],
            kind="reward",
        )
    save_manager.save(save_data)
    current_screen = "title"


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

def draw_shared_sidebar():
    global nav_rects
    global logo_rect

    # get_content_rect() already keeps every page clear of the dock (see
    # ui.set_sidebar_mode, called once per frame below), so it never
    # sits on top of a page's own tab bar or "back" link.
    nav_rects, logo_rect = ui.draw_icon_dock(screen, current_screen, settings["sidebar_position"])



# --------------------------------------------------
# Unified Menu & Levels (The Dashboard)
# --------------------------------------------------

CATEGORY_CARD_RADIUS = 26


def category_caption(levels, completed, total):
    """The line under a tile's title: how far along it is, and - when it's
    worth saying - which puzzle to pick up next."""
    if total == 0:
        return ""
    if completed >= total:
        return "All complete"
    if total == 1:
        return "Ready to play"

    next_level = next(
        (level for level in levels
         if not save_manager.level_entry(save_data, level["name"])["completed"]),
        None
    )
    if next_level is not None:
        return f"{completed}/{total} \u00b7 Next: {next_level['name']}"
    return f"{completed}/{total} puzzles"


def draw_category_card(rect, category, is_hidden, unlocked, levels, completed, total, hovered):
    """Reference-style category card with rewards and a level description."""
    # Keep neighboring cards in their fixed slots while scrolling. Hover is
    # communicated by the border and shadow, never by changing card bounds.
    draw_rect = rect.copy()
    r = CATEGORY_CARD_RADIUS

    ui.draw_blurred_shadow(
        screen, draw_rect, border_radius=r,
        blur=9 if hovered else 6, alpha=48 if hovered else 24,
        color=ui.CARD_SHADOW, offset=(0, 3 if hovered else 2)
    )
    ui.draw_smooth_rect(screen, draw_rect, ui.CARD_BACKGROUND, radius=r)
    ui.draw_smooth_rect(screen, draw_rect, ui.CARD_BORDER, radius=r, width=1)

    photo_height = min(220, draw_rect.height - 24)
    card_layout = levels_layout.category_card_content_layout(draw_rect, photo_height, small_font)
    photo_rect = card_layout["photo"]

    ui.draw_image_rounded(screen, load_level_thumbnail(levels[0]["image"]), photo_rect, radius=18)

    ui.draw_bottom_scrim(screen, photo_rect, radius=18, color=(8, 12, 22), max_alpha=185, start=0.48)
    if is_hidden:
        if not unlocked:
            ui.draw_lock_icon(screen, (photo_rect.left + 54, photo_rect.centery), 44, (230, 234, 244))
            label = "???"
            caption = f"Finish all {len(REGULAR_LEVELS)} to unlock"
            ui.draw_text(screen, label, button_font, (255, 255, 255), photo_rect.left + 92, photo_rect.centery - 16, center=False)
            ui.draw_text(screen, caption, small_font, (230, 232, 238), photo_rect.left + 92, photo_rect.centery + 16, center=False)
        else:
            ui.draw_text(screen, "THE ULTIMATE PUZZLE", button_font, (255, 255, 255), photo_rect.left + 20, photo_rect.centery, center=False)
            play_rect = pygame.Rect(photo_rect.right - 164, photo_rect.centery - 24, 144, 48)
            ui.draw_gradient_rect(screen, play_rect, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=14)
            ui.draw_text(screen, "PLAY", button_font, ui.TEXT, play_rect.centerx, play_rect.centery)
    else:
        label = "The Ultimate Puzzle" if is_hidden else category["label"]
        caption = category_caption(levels, completed, total)
        title_rect = card_layout["title"]
        progress_rect = card_layout["progress"]
        ui.draw_text(screen, label, button_font, (255, 255, 255), title_rect.left, title_rect.top, center=False)
        ui.draw_text(screen, caption, small_font, (238, 240, 244), progress_rect.left, progress_rect.top, center=False)
        fraction = completed / total if total else 0

        ring_rect = card_layout["progress_ring"]
        supersample = 3
        ring_layer = pygame.Surface(
            (ring_rect.width * supersample, ring_rect.height * supersample),
            pygame.SRCALPHA,
        )
        ring_center = (ring_layer.get_width() // 2, ring_layer.get_height() // 2)
        ring_radius = ring_rect.width * supersample // 2 - 12
        stroke = 15
        pygame.draw.circle(ring_layer, (*ui.TRACK_BACKGROUND, 190), ring_center, ring_radius, width=stroke)
        if fraction > 0:
            progress_color = (*ui.GRADIENT_PRIMARY[1], 255)
            if fraction >= 1:
                pygame.draw.circle(ring_layer, progress_color, ring_center, ring_radius, width=stroke)
            else:
                pygame.draw.arc(
                    ring_layer,
                    progress_color,
                    ring_layer.get_rect().inflate(-24, -24),
                    -math.pi / 2,
                    -math.pi / 2 + 2 * math.pi * fraction,
                    stroke,
                )
        ring_layer = pygame.transform.smoothscale(ring_layer, ring_rect.size)
        screen.blit(ring_layer, ring_rect.topleft)

    if not is_hidden:
        section_top = card_layout["section_top"]
        reward_center = card_layout["rewards_center"]
        unlock_center = card_layout["unlockables_center"]
        ui.draw_text(
            screen, "REWARDS", small_font, ui.MUTED_TEXT,
            card_layout["rewards_left"], section_top + 14, center=False
        )

        reward_items = (("palette", "THEMES", "color_themes"), ("bulb", "HINTS", "hint_button"))
        for index, (icon, label, feature) in enumerate(reward_items):
            center = card_layout["reward_icon_centers"][index]
            badge = pygame.Rect(0, 0, 48, 48)
            badge.center = center
            ui.draw_smooth_rect(screen, badge, (*ui.WHITE, 245), radius=12)
            ui.draw_achievement_icon(screen, icon, center, 32)
            if not rewards.has_feature(save_data, feature):
                ui.draw_smooth_rect(screen, badge, (*ui.TRACK_BACKGROUND, 145), radius=12)
                ui.draw_lock_icon(screen, center, 20)
            ui.draw_text(screen, label, small_font, ui.MUTED_TEXT, center[0], card_layout["reward_label_y"])

        unlock_items = (("wheel", "TRAY", "tray_wheel"), ("mountain", "JOURNEY", "journey"))
        for index, (icon, label, feature) in enumerate(unlock_items):
            center = card_layout["unlock_icon_centers"][index]
            badge = pygame.Rect(0, 0, 48, 48)
            badge.center = center
            ui.draw_smooth_rect(screen, badge, (*ui.WHITE, 245), radius=12)
            ui.draw_achievement_icon(screen, icon, center, 32)
            if not rewards.has_feature(save_data, feature):
                ui.draw_smooth_rect(screen, badge, (*ui.TRACK_BACKGROUND, 145), radius=12)
                ui.draw_lock_icon(screen, center, 20)
            ui.draw_text(screen, label, small_font, ui.MUTED_TEXT, center[0], card_layout["unlock_label_y"])

        ui.draw_text(
            screen, "DESCRIPTION", small_font, ui.MUTED_TEXT,
            card_layout["description_left"], card_layout["description_title_y"], center=False
        )
        description = category.get("description", "A new collection of puzzles is waiting to be explored.")
        for line_index, line in enumerate(card_layout["description_lines"](description)):
            ui.draw_text(
                screen, line, small_font, ui.TEXT,
                card_layout["description_left"],
                card_layout["description_top"] + line_index * 20,
                center=False,
            )

        button = pygame.Rect(draw_rect.left + 18, draw_rect.bottom - 58, draw_rect.width - 36, 44)
        ui.draw_gradient_rect(screen, button, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=14)
        ui.draw_text(screen, "PLAY", button_font, ui.TEXT, button.centerx, button.centery)

    if hovered:
        ring_color = (*ui.GRADIENT_PRIMARY[1], 220) if unlocked else (200, 204, 220, 180)
        ui.draw_smooth_rect(
            screen, draw_rect, ring_color,
            radius=r, width=3
        )


def draw_menu():
    """The scrollable three-column Levels gallery and hidden finale card."""
    global resume_button, category_card_rects
    global levels_scroll_x, levels_scroll_max, levels_viewport_rect
    global tab_rects

    content = ui.get_content_rect()

    # Soft white-to-blue wash instead of flat white
    ui.draw_content_panel(screen, content)

    tab_rects = {}

    resumable_level, _resumable_entry = get_resumable_level()
    visible_categories = available_categories(save_data)
    layout = levels_layout.compute_layout(
        content, levels_scroll_x, item_count=len(visible_categories) + 1
    )
    levels_scroll_x = layout["scroll_x"]
    levels_scroll_max = layout["max_scroll"]
    levels_viewport_rect = layout["viewport"]
    category_card_rects = []
    mouse_position = pygame.mouse.get_pos()
    ultimate_unlocked = is_ultimate_unlocked(save_data)

    ui.draw_text(
        screen, "LEVELS", header_font, ui.TEXT,
        levels_viewport_rect.left, content.top + 32, center=False
    )
    if resumable_level is not None:
        resume_button = pygame.Rect(
            content.right - 300,
            content.bottom - 72,
            260,
            40,
        )
        draw_gradient_button(
            resume_button,
            ui.GRADIENT_PRIMARY[0],
            ui.GRADIENT_PRIMARY[1],
            f"RESUME {resumable_level['name'].upper()}",
            text_color=ui.TEXT,
        )
    else:
        resume_button = None

    previous_clip = screen.get_clip()
    screen.set_clip(levels_viewport_rect)

    for index, category in enumerate(visible_categories):
        rect = layout["cards"][index]
        category_card_rects.append((rect, category))

        if rect.colliderect(levels_viewport_rect):
            levels = category_levels(category["key"])
            completed = sum(
                1 for level in levels
                if save_manager.level_entry(save_data, level["name"])["completed"]
            )
            hovered = levels_layout.hover_rect(rect, levels_viewport_rect).collidepoint(mouse_position)
            draw_category_card(rect, category, False, True, levels, completed, len(levels), hovered)

    hidden_category = {"key": "ultimate", "label": "The Ultimate Puzzle", "hidden": True}
    hidden_rect = layout["hidden"]
    category_card_rects.append((hidden_rect, hidden_category))

    if hidden_rect.colliderect(levels_viewport_rect):
        ultimate_entry = save_manager.level_entry(save_data, ULTIMATE_LEVEL["name"])
        hovered = levels_layout.hover_rect(hidden_rect, levels_viewport_rect).collidepoint(mouse_position)
        draw_category_card(
            hidden_rect, hidden_category, True, ultimate_unlocked, [ULTIMATE_LEVEL],
            1 if ultimate_entry["completed"] else 0, 1, hovered
        )

    screen.set_clip(previous_clip)

    if levels_scroll_max > 0:
        track = layout["scrollbar"]
        thumb_width = max(48, int(track.width * layout["scrollable_width"] / layout["content_width"]))
        thumb_x = track.left + int(
            (track.width - thumb_width) * levels_scroll_x / levels_scroll_max
        )
        ui.draw_smooth_rect(screen, track, ui.TRACK_BACKGROUND, radius=3)
        ui.draw_smooth_rect(screen, pygame.Rect(thumb_x, track.top, thumb_width, track.height), ui.MUTED_TEXT, radius=3)


def draw_category_levels_screen():
    global current_screen, category_level_card_rects, category_level_back_rect

    content = ui.get_content_rect()
    ui.draw_content_panel(screen, content)

    category = next(
        (item for item in available_categories(save_data) if item["key"] == selected_category_key),
        None,
    )
    if category is None:
        current_screen = "menu"
        category_level_card_rects = []
        return

    levels = category_levels(category["key"])
    completed = sum(
        save_manager.level_entry(save_data, level["name"])["completed"]
        for level in levels
    )
    ui.draw_text(
        screen, category["label"].upper(), title_font, ui.TEXT,
        content.left + 40, content.top + 30, center=False
    )
    ui._blit_midright(
        screen, small_font, f"{completed}/{len(levels)} completed",
        ui.MUTED_TEXT, content.right - 40, content.top + 56
    )

    layout = levels_layout.compute_level_grid_layout(content, len(levels))
    category_level_back_rect = ui.get_page_back_rect()
    category_level_card_rects = []
    mouse_position = pygame.mouse.get_pos()
    previous_clip = screen.get_clip()
    screen.set_clip(layout["viewport"])

    for rect, level in zip(layout["cards"], levels):
        entry = save_manager.level_entry(save_data, level["name"])
        unlocked = is_level_unlocked(level)
        is_complete = entry["completed"]
        hovered = unlocked and rect.collidepoint(mouse_position)
        category_level_card_rects.append((rect, level))

        ui.draw_card(screen, rect, ui.CARD_BACKGROUND, ui.CARD_BORDER, border_radius=20)
        image_rect = pygame.Rect(
            rect.left + 10, rect.top + 10,
            rect.width - 20, min(210, rect.height - 112)
        )
        ui.draw_image_rounded(screen, load_level_thumbnail(level["image"]), image_rect, radius=16)

        if not unlocked:
            veil = pygame.Surface(image_rect.size, pygame.SRCALPHA)
            veil.fill((74, 83, 103, 112))
            screen.blit(veil, image_rect.topleft)
            ui.draw_lock_icon(screen, image_rect.center, 42, (245, 247, 252))

        ui.draw_text(
            screen, level["name"], button_font, ui.TEXT,
            rect.left + 14, image_rect.bottom + 22, center=False
        )
        piece_total = level["columns"] * level["rows"]
        ui.draw_text(
            screen, f"{piece_total} PIECES", small_font, ui.MUTED_TEXT,
            rect.left + 14, image_rect.bottom + 50, center=False
        )
        status = "COMPLETED" if is_complete else ("READY" if unlocked else "LOCKED")
        status_color = ui.ACCENT_BLUE if unlocked else ui.MUTED_TEXT
        ui._blit_midright(
            screen, small_font, status, status_color,
            rect.right - 14, image_rect.bottom + 50
        )

        if hovered:
            ui.draw_smooth_rect(screen, rect, (*ui.GRADIENT_PRIMARY[1], 230), radius=20, width=2)

    screen.set_clip(previous_clip)
    category_level_back_rect = ui.get_page_back_rect()
    ui.draw_page_back_button(screen, category_level_back_rect, button_font)


# --------------------------------------------------
# Journey - the tower map (a full-screen page, like Settings)
# --------------------------------------------------
# journey.py decides WHAT is on the map (the seven levels, which are
# locked, where each sits on the grid, the curve between them). This
# section only turns that into pixels.

JOURNEY_NODE_COLUMNS = 4
JOURNEY_NODE_SPACING = 270
# Node centres, left to right - centred on the canvas rather than a fixed
# list of x-positions, so this stays centred if WIDTH ever changes again.
JOURNEY_COLUMN_X = [
    (WIDTH - (JOURNEY_NODE_COLUMNS - 1) * JOURNEY_NODE_SPACING) // 2 + column * JOURNEY_NODE_SPACING
    for column in range(JOURNEY_NODE_COLUMNS)
]
JOURNEY_FIRST_ROW_Y = 330
JOURNEY_ROW_GAP = 310
JOURNEY_NODE_DIAMETER = 150
JOURNEY_PATH_WIDTH = 9
JOURNEY_PATH_LOCKED = (206, 214, 228)


def draw_journey_path(points, color, width):
    """A thick line with round joints (pygame's own thick lines leave
    little gaps at the corners)."""
    whole_points = [(int(x), int(y)) for x, y in points]
    pygame.draw.lines(screen, color, False, whole_points, width)
    for point in whole_points:
        pygame.draw.circle(screen, color, point, width // 2)


def draw_journey_node(rect, level, node_status, hovered):
    """One circular node on the map. `node_status` is "completed",
    "current" or "locked" (see journey.status)."""
    radius = rect.width // 2
    hidden_and_locked = bool(level.get("hidden")) and node_status == "locked"

    if node_status == "current":
        # A soft glow behind the level that's next to play. (A shadow on
        # a square rect with radius = half its width comes out round.)
        ui.draw_blurred_shadow(
            screen, rect, border_radius=radius, blur=16,
            alpha=150, color=ui.GRADIENT_PRIMARY[1], offset=(0, 0)
        )

    if hidden_and_locked:
        # The finale's picture stays a secret until it's earned.
        ui.draw_smooth_rect(screen, rect, (96, 104, 122, 255), radius=radius)
    else:
        ui.draw_image_rounded(screen, load_level_thumbnail(level["image"]), rect, radius=radius)

    if node_status == "locked":
        if not hidden_and_locked:
            # A grey veil that washes the picture out
            ui.draw_smooth_rect(screen, rect, (150, 158, 172, 190), radius=radius)
        ui.draw_lock_icon(screen, rect.center, int(radius * 0.7))

    elif node_status == "completed":
        ui.draw_smooth_rect(screen, rect, (*ui.GRADIENT_PRIMARY[1], 255), radius=radius, width=4)

        # A little check-mark badge, top-right of the node
        badge_radius = max(10, int(radius * 0.24))
        badge_center = (rect.right - badge_radius - 6, rect.top + badge_radius + 6)
        pygame.draw.circle(screen, (96, 190, 150), badge_center, badge_radius)
        pygame.draw.circle(screen, (255, 255, 255), badge_center, badge_radius, width=2)
        tick = [
            (badge_center[0] - badge_radius * 0.45, badge_center[1] + badge_radius * 0.05),
            (badge_center[0] - badge_radius * 0.10, badge_center[1] + badge_radius * 0.40),
            (badge_center[0] + badge_radius * 0.50, badge_center[1] - badge_radius * 0.35),
        ]
        pygame.draw.lines(screen, (255, 255, 255), False, tick, 3)

    else:  # current
        ui.draw_smooth_rect(screen, rect, (*ui.ACCENT_BLUE, 255), radius=radius, width=5)

        # The PLAY chip across the bottom of the node
        chip = pygame.Rect(0, 0, 108, 36)
        chip.center = (rect.centerx, rect.bottom - 32)
        ui.draw_blurred_shadow(
            screen, chip, border_radius=18, blur=10,
            alpha=90, color=(120, 150, 210), offset=(0, 4)
        )
        ui.draw_gradient_rect(
            screen, chip, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=18
        )
        ui.draw_text(screen, "PLAY", small_font, ui.TEXT, chip.centerx, chip.centery)

    if hovered:
        ui.draw_smooth_rect(
            screen, rect.inflate(10, 10), (255, 255, 255, 235),
            radius=radius + 5, width=4
        )


def draw_journey_screen():
    """The Journey: one winding tower of puzzles, gated in order. Levels
    can be replayed once finished; locked ones can't be opened."""
    global journey_node_rects, journey_back_rect, tab_rects

    # This page has no tab bar of its own - clear out whatever the last
    # page (Levels, say) left behind, so the sidebar-suppress check in
    # draw_shared_sidebar doesn't test the mouse against stale rects
    # from a completely different layout.
    tab_rects = {}

    if not rewards.has_feature(save_data, "journey"):
        # The whole mode is a reward in itself - locked until every
        # category is fully complete. Nothing to click here but BACK.
        journey_node_rects = []

        ui.draw_text(screen, "JOURNEY", title_font, ui.TEXT, 120, 60, center=False)
        ui.draw_lock_icon(screen, (WIDTH // 2, HEIGHT // 2 - 70), 96)
        ui.draw_text(
            screen, "Journey mode is locked", header_font, ui.TEXT,
            WIDTH // 2, HEIGHT // 2 + 20
        )
        ui.draw_text(
            screen, rewards.locked_hint("journey") or "Keep playing to unlock it",
            subtitle_font, ui.MUTED_TEXT, WIDTH // 2, HEIGHT // 2 + 56
        )

        journey_back_rect = ui.get_page_back_rect()
        ui.draw_page_back_button(screen, journey_back_rect, button_font)
        return

    levels = journey.JOURNEY_ALL
    completed, total = journey.progress(save_data)
    mouse_position = pygame.mouse.get_pos()

    ui.draw_text(screen, "JOURNEY", title_font, ui.TEXT, 120, 60, center=False)
    ui._blit_midright(
        screen, small_font, f"{completed} of {total} completed",
        ui.MUTED_TEXT, WIDTH - 120, 84
    )

    centers = [
        (JOURNEY_COLUMN_X[column], JOURNEY_FIRST_ROW_Y + row * JOURNEY_ROW_GAP)
        for column, row in journey.cells(len(levels))
    ]
    statuses = [journey.status(save_data, level) for level in levels]

    # The path first, so every node sits on top of it. Each stretch is
    # colored by whether the level it leads TO has been reached yet.
    for i in range(len(centers) - 1):
        reached = statuses[i + 1] != "locked"
        draw_journey_path(
            journey.hop_points(centers[i], centers[i + 1]),
            ui.GRADIENT_PRIMARY[1] if reached else JOURNEY_PATH_LOCKED,
            JOURNEY_PATH_WIDTH
        )

    journey_node_rects = []
    radius = JOURNEY_NODE_DIAMETER // 2

    for index, (center, level) in enumerate(zip(centers, levels)):
        node_status = statuses[index]
        rect = pygame.Rect(0, 0, JOURNEY_NODE_DIAMETER, JOURNEY_NODE_DIAMETER)
        rect.center = center

        hovered = (
            node_status != "locked"
            and math.hypot(mouse_position[0] - center[0], mouse_position[1] - center[1]) <= radius
        )
        draw_journey_node(rect, level, node_status, hovered)
        journey_node_rects.append((rect, level, node_status))

        hidden_and_locked = bool(level.get("hidden")) and node_status == "locked"

        # Above the node: "12 - PHOTOGRAPHY"
        heading = journey.heading(level, revealed=not hidden_and_locked)
        heading_font = button_font if button_font.size(heading)[0] <= 240 else small_font
        ui.draw_text(
            screen, heading, heading_font,
            ui.MUTED_TEXT if node_status == "locked" else ui.TEXT,
            rect.centerx, rect.top - 26
        )

        # Below it: how it's going
        entry = save_manager.level_entry(save_data, level["name"])
        if node_status == "completed":
            best = entry["best_time"]
            lines = ["Completed" if best is None else f"Completed \u00b7 {format_time(best)}"]
        elif node_status == "current":
            lines = [f"{entry['pieces_placed']}/{journey.piece_count(level)} pieces"]
        else:
            lines = ["LOCKED"]
            if hidden_and_locked:
                lines.append("(HIDDEN)")
            elif statuses[index - 1] == "current":
                lines.append(f"(Complete {journey.previous_level(level)['theme_label']})")

        for line_index, line in enumerate(lines):
            ui.draw_text(
                screen, line, small_font,
                ui.TEXT if node_status == "current" and line_index == 0 else ui.MUTED_TEXT,
                rect.centerx, rect.bottom + 24 + line_index * 23
            )

    journey_back_rect = ui.get_page_back_rect()
    ui.draw_page_back_button(screen, journey_back_rect, button_font)


# --------------------------------------------------
# Exit confirmation
# --------------------------------------------------

_exit_dim_surface = None


def draw_exit_confirm():
    """Dims everything and asks "are you sure?" before the game closes."""
    global exit_confirm_rects, _exit_dim_surface

    if _exit_dim_surface is None:
        _exit_dim_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        _exit_dim_surface.fill((36, 56, 76, 120))
    screen.blit(_exit_dim_surface, (0, 0))

    panel = pygame.Rect(0, 0, 440, 260)
    panel.center = (WIDTH // 2, HEIGHT // 2)
    ui.draw_frosted_panel(screen, panel, radius=28)

    ui.draw_tracked_text(
        screen, "EXIT?", title_font, ui.TEXT,
        panel.centerx, panel.top + 56, tracking=3
    )
    ui.draw_text(
        screen, "Are you sure you want to exit?", subtitle_font, ui.MUTED_TEXT,
        panel.centerx, panel.top + 116
    )

    gap = 14
    button_width = (panel.width - 48 - gap) // 2
    button_top = panel.bottom - 28 - 52

    stay_rect = pygame.Rect(panel.left + 24, button_top, button_width, 52)
    exit_rect = pygame.Rect(stay_rect.right + gap, button_top, button_width, 52)
    exit_confirm_rects = {"stay": stay_rect, "exit": exit_rect}

    # "Stay" is the highlighted (safe) choice
    draw_gradient_button(
        stay_rect, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1],
        "STAY", text_color=ui.TEXT
    )
    draw_glass_button(exit_rect, "EXIT")


# --------------------------------------------------
# Puzzle screen
# --------------------------------------------------

def draw_classic_puzzle_header(header, radius, icon_diameter, pill_radius, icon_corner_radius, glass_tint, gap):
    """The original header: back arrow, level-name pill, timer pill,
    progress pill, settings gear - each pill sized to fill the row
    exactly, with no dead space anywhere in the bar."""
    global back_button, gear_button

    # ---- Back button (top left) - a rounded square, same size as the
    # settings button on the far right ----
    back_center = (header.left + radius, header.centery)
    back_button = ui.draw_icon_button(
        screen, back_center, radius, tint=glass_tint, corner_radius=icon_corner_radius
    )
    ui.draw_chevron_icon(screen, back_center, int(radius * 1.1))

    # ---- Settings gear (top right) - mirrors the back button ----
    gear_center = (header.right - radius, header.centery)
    gear_button = ui.draw_icon_button(
        screen, gear_center, radius, tint=glass_tint, corner_radius=icon_corner_radius
    )
    ui.draw_gear_icon(screen, gear_center, int(radius * 1.3))

    # ---- Timer pill - fixed width (roughly two icon-buttons wide),
    # dead-centered on the whole header row ----
    timer_width = icon_diameter * 2
    timer_pill = pygame.Rect(0, 0, timer_width, icon_diameter)
    timer_pill.center = header.center
    ui.draw_glass(screen, timer_pill, radius=pill_radius, tint=glass_tint)
    ui.draw_text(
        screen, format_time(get_current_time()), header_font,
        ui.TEXT, timer_pill.centerx, timer_pill.centery
    )

    # ---- Level title + progress pills - mirrored, equal width, sized to
    # eat every remaining pixel of the row (back -> title -> timer ->
    # progress -> gear, each separated by exactly `gap`), so there's no
    # dead space anywhere in the bar. ----
    big_pill_width = int((header.width - icon_diameter * 2 - timer_width - gap * 4) / 2)

    title_text = current_level["name"]
    title_pill = pygame.Rect(0, 0, big_pill_width, icon_diameter)
    title_pill.midleft = (back_button.right + gap, header.centery)
    ui.draw_glass(screen, title_pill, radius=pill_radius, tint=glass_tint)
    ui.draw_text(screen, title_text, header_font, ui.TEXT, title_pill.centerx, title_pill.centery)

    piece_count = len(puzzle.pieces)
    fraction = puzzle.completed_count() / piece_count if piece_count else 0
    progress_pill = pygame.Rect(0, 0, big_pill_width, icon_diameter)
    progress_pill.midright = (gear_button.left - gap, header.centery)
    ui.draw_progress_pill(
        screen, progress_pill, fraction,
        f"{puzzle.completed_count()}/{piece_count}", header_font,
        radius=pill_radius, tint=glass_tint
    )


def draw_minimal_puzzle_header(header, radius, icon_diameter, pill_radius, icon_corner_radius, glass_tint, gap):
    """The alternate header, matching the newer reference design: a pause
    button (top left), a timer pill (clock icon + time) in the middle,
    and a coins pill (top right). The pause button opens the same pause
    menu as the Classic header's gear, so RESUME/RESTART/SETTINGS/QUIT
    are one click away."""
    global back_button, gear_button

    back_button = None

    pause_center = (header.left + radius, header.centery)
    gear_button = ui.draw_icon_button(
        screen, pause_center, radius, tint=glass_tint, corner_radius=icon_corner_radius
    )
    ui.draw_gear_icon(screen, pause_center, int(radius * 1.3))

    # ---- Timer pill: [clock] 00:00, sized to its own content ----
    time_text = format_time(get_current_time())
    time_w = header_font.size(time_text)[0]
    icon_size = int(icon_diameter * 0.52)
    pad, inner_gap = 24, 8

    pill = pygame.Rect(0, 0, pad * 2 + icon_size + inner_gap + time_w, icon_diameter)
    pill.center = header.center
    ui.draw_glass(screen, pill, radius=pill_radius, tint=glass_tint)

    x = pill.left + pad
    ui.draw_timer_icon(screen, (x + icon_size / 2, pill.centery), icon_size)
    x += icon_size + inner_gap
    ui._blit_midleft(screen, header_font, time_text, ui.TEXT, x, pill.centery)

    # ---- Coins pill, top right ----
    coin_text = str(save_data["coins"])
    label = "COINS: "
    coin_size = int(icon_diameter * 0.48)
    text_w = header_font.size(label + coin_text)[0]
    coin_pill = pygame.Rect(0, 0, pad * 2 + text_w + inner_gap + coin_size, icon_diameter)
    coin_pill.midright = (header.right, header.centery)
    ui.draw_glass(screen, coin_pill, radius=pill_radius, tint=glass_tint)

    x = coin_pill.left + pad
    ui._blit_midleft(screen, header_font, label + coin_text, ui.TEXT, x, coin_pill.centery)
    ui.draw_coin_icon(screen, (x + text_w + inner_gap + coin_size / 2, coin_pill.centery), coin_size)


def draw_puzzle():
    # The puzzle screen drops the sidebar for a full-bleed workspace (see
    # draw_shared_sidebar's call site at the bottom of the file), so every
    # rect here is measured against the whole window via the ui.PUZZLE_*
    # layout helpers rather than ui.get_content_rect().
    header = ui.get_puzzle_header_rect()
    radius = ui.PUZZLE_ICON_RADIUS
    icon_diameter = radius * 2
    pill_radius = ui.PUZZLE_PILL_RADIUS
    icon_corner_radius = ui.PUZZLE_ICON_CORNER_RADIUS
    glass_tint = ui.HEADER_GLASS_TINT
    gap = ui.PUZZLE_HEADER_GAP

    header_args = (header, radius, icon_diameter, pill_radius, icon_corner_radius, glass_tint, gap)
    if settings["header_style"] == "minimal":
        draw_minimal_puzzle_header(*header_args)
    else:
        draw_classic_puzzle_header(*header_args)

    # Pick-up animation (a grabbed piece grows and straightens out)
    if not puzzle_paused:
        puzzle.update(clock.get_time() / 1000, pygame.mouse.get_pos())

    # ---- Board: the rounded photo card, grid hint, and placed pieces ----
    puzzle.draw_board(screen, hint=hint_active)

    # ---- Tray ----
    piece_area = puzzle.piece_area

    # The Pile tray has no glassy dish under it - it's an invisible area
    # (pieces still lay out and clamp inside it), with nothing drawn
    # there. Wheel and Carousel keep the glass plate.
    if puzzle.tray_style != "pile":
        ui.draw_tray_card(screen, piece_area, carousel=(puzzle.tray_style == "carousel"))

    puzzle.draw_tray(screen)

    if puzzle.tray_style == "carousel":
        global carousel_shuffle_button
        carousel_shuffle_button = ui.draw_carousel_shuffle_button(screen, piece_area, button_font)
    else:
        carousel_shuffle_button = None

    draw_powerups_panel(piece_area, glass_tint)

    # Whatever's currently being dragged draws last, over both the board
    # and the tray, so it can be picked up and dropped anywhere.
    puzzle.draw_active(screen)

    if puzzle_paused:
        draw_pause_overlay(puzzle.board_rect)


def draw_powerup_card(rect, kind, label, cost_text, enabled, affordable, active, compact):
    """One square-ish card in the POWER-UPS panel: icon, name, price chip."""
    hovered = enabled and rect.collidepoint(pygame.mouse.get_pos())
    if ui.IS_DARK:
        base = ui.TRACK_BACKGROUND if (hovered or active) else ui.CARD_BACKGROUND
        tint = (*tuple(max(0, channel - (8 if hovered or active else 2)) for channel in base), 235)
    else:
        tint = (255, 255, 255, 235) if (hovered or active) else (255, 255, 255, 170)
    ui.draw_glass(screen, rect, radius=18, tint=tint, hovered=hovered)

    icon_color = ui.TEXT if enabled else ui.MUTED_TEXT
    icon_size = 24 if compact else 36
    icon_y = rect.top + (icon_size // 2 + 8 if compact else icon_size // 2 + 14)
    icon_center = (rect.centerx, icon_y)

    if kind == "hint":
        ui.draw_lightbulb_icon(screen, icon_center, icon_size, icon_color)
    elif kind == "shuffle":
        ui.draw_shuffle_icon(screen, icon_center, icon_size, icon_color)
    else:
        ui.draw_rotate_icon(screen, icon_center, icon_size, icon_color)

    if not compact:
        ui.draw_text(screen, label, small_font, ui.TEXT if enabled else ui.MUTED_TEXT,
                     rect.centerx, rect.top + 72)

    chip = pygame.Rect(0, 0, rect.width - 16, 22)
    chip.midbottom = (rect.centerx, rect.bottom - 8)
    if enabled and affordable:
        ui.draw_gradient_rect(screen, chip, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=11)
        chip_text_color = ui.TEXT
    else:
        chip_color = tuple(max(0, channel - 10) for channel in ui.CARD_BACKGROUND) if ui.IS_DARK else (206, 212, 224)
        ui.draw_smooth_rect(screen, chip, (*chip_color, 255), radius=11)
        chip_text_color = ui.MUTED_TEXT
    ui.draw_text(screen, cost_text, small_font, chip_text_color, chip.centerx, chip.centery)


def draw_powerups_panel(piece_area, glass_tint):
    """The POWER-UPS panel, bottom left, level with the tray: Hint,
    Shuffle and Rotate cards with their coin prices. Hint and Shuffle
    are live; Rotate is shown but disabled - there's no piece-rotation
    mechanic to power up yet."""
    global hint_button, shuffle_button

    panel = pygame.Rect(ui.PUZZLE_MARGIN, piece_area.top, ui.PUZZLE_POWERUPS_WIDTH, piece_area.height)
    compact = panel.height < 150
    panel_color = tuple(max(0, channel - 8) for channel in ui.CARD_BACKGROUND) if ui.IS_DARK else None
    panel_tint = (*panel_color, 240) if panel_color else glass_tint
    ui.draw_glass(screen, panel, radius=24, tint=panel_tint)

    ui._blit_midleft(screen, small_font, "POWER-UPS", ui.MUTED_TEXT, panel.left + 20, panel.top + 20)

    # In the Classic header there's no coins pill, so the balance lives here.
    if settings["header_style"] != "minimal":
        coin_text = str(save_data["coins"])
        text_w = small_font.size(coin_text)[0]
        ui.draw_coin_icon(screen, (panel.right - 22 - text_w - 16, panel.top + 20), 20)
        ui._blit_midleft(screen, small_font, coin_text, ui.TEXT, panel.right - 20 - text_w, panel.top + 20)

    inner_pad, card_gap = 14, 10
    card_w = (panel.width - inner_pad * 2 - card_gap * 2) // 3
    card_top = panel.top + 38
    card_h = panel.bottom - 12 - card_top

    hint_available = settings["show_hint"] and rewards.has_feature(save_data, "hint_button")
    coins = save_data["coins"]
    carousel_mode = puzzle is not None and getattr(puzzle, "tray_style", None) == "carousel"

    specs = [("hint", "HINT", hint_available, POWERUP_COSTS["hint"])]
    if not carousel_mode:
        specs.append(("shuffle", "SHUFFLE", True, POWERUP_COSTS["shuffle"]))
    specs.append(("rotate", "ROTATE", False, None))

    hint_button = None
    shuffle_button = None

    for index, (kind, label, enabled, cost) in enumerate(specs):
        rect = pygame.Rect(panel.left + inner_pad + index * (card_w + card_gap), card_top, card_w, card_h)

        if kind == "rotate":
            cost_text = "SOON"
        elif not enabled:
            cost_text = "LOCKED" if not rewards.has_feature(save_data, "hint_button") else "OFF"
        else:
            cost_text = f"{cost} COINS"
            if small_font.size(cost_text)[0] > rect.width - 20:
                cost_text = str(cost)

        draw_powerup_card(
            rect, kind, label, cost_text, enabled,
            affordable=(cost is not None and coins >= cost),
            active=(kind == "hint" and hint_active),
            compact=compact
        )

        if enabled and kind == "hint":
            hint_button = rect
        elif enabled and kind == "shuffle":
            shuffle_button = rect

    # A short-lived note (e.g. "Not enough coins") just above the panel.
    if powerup_notice and time.time() < powerup_notice[1]:
        ui._blit_midleft(screen, small_font, powerup_notice[0], ui.TEXT, panel.left + 4, panel.top - 14)


def draw_pause_overlay(board_rect):
    """The frosted PAUSE panel, floating over the right side of the
    board - matches the reference design's glassmorphic pause menu.
    """
    global pause_button_rects

    board_area = ui.get_puzzle_board(puzzle.piece_area.height)
    panel = ui.get_puzzle_pause_panel_rect(board_area, gear_button)

    ui.draw_frosted_panel(screen, panel, radius=28)

    ui.draw_tracked_text(
        screen, "PAUSE", title_font, ui.TEXT,
        panel.centerx, panel.top + 46, tracking=3
    )

    button_height = 52
    gap = 14
    start_y = panel.top + 92

    buttons = [
        ("resume", "RESUME", True),
        ("restart", "RESTART LEVEL", False),
        ("settings", "SETTINGS", False),
        ("quit", "QUIT TO MENU", False)
    ]

    pause_button_rects = {}
    for index, (key, label, primary) in enumerate(buttons):
        rect = pygame.Rect(
            panel.left + 24, start_y + index * (button_height + gap),
            panel.width - 48, button_height
        )
        pause_button_rects[key] = rect

        if primary:
            draw_gradient_button(
                rect, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1],
                label, text_color=ui.TEXT
            )
        else:
            draw_glass_button(rect, label)


# --------------------------------------------------
# Completion screen
# --------------------------------------------------

def _draw_completion_original():
    global play_again_button
    global menu_button
    global next_level_button
    global stars_earned, coins_awarded

    center_x = WIDTH // 2

    # A gentle entrance animation keeps the win screen feeling like a reward
    # without adding another dependency or changing the game's mechanics.
    elapsed = time.time() - (puzzle_end_time or time.time())
    reveal = min(1.0, elapsed / 0.45)
    ease = 1 - (1 - reveal) ** 3

    # Confetti sits behind the UI so the screen still feels clean.
    draw_confetti()

    # ---- Main reward card ----
    # Sized to fit the extra PRIZES row below the stats without crowding
    # the preview image or the buttons underneath.
    card_width = 820
    card_height = 480
    card = pygame.Rect(0, 0, card_width, card_height)
    card.center = (center_x, 415 + int((1 - ease) * 18))

    # Soft celebratory glow behind the hero card.
    ui.draw_glow(
        screen,
        card.center,
        int(340 + 30 * ease),
        (178, 235, 222),
        alpha=int(55 * ease)
    )

    # ---- Small corner branding ----
    ui.draw_piece_icon(screen, (56, 46), 30, ui.NAV_GRADIENT[1])
    ui.draw_text(screen, "PUZZLESCAPE", button_font, ui.TEXT, 84, 46, center=False)

    # ---- Hero heading ----
    ui.draw_tracked_text(
        screen,
        "YOU DID IT!",
        hero_font,
        ui.TEXT,
        center_x,
        105 - int((1 - ease) * 14),
        tracking=3
    )
    ui.draw_text(
        screen,
        "You made every piece fit.",
        subtitle_font,
        ui.MUTED_TEXT,
        center_x,
        144 - int((1 - ease) * 8)
    )

    ui.draw_card(screen, card, ui.CARD_BACKGROUND, ui.CARD_BORDER, border_radius=30)

    # Finished puzzle preview.
    preview_rect = pygame.Rect(card.left + 28, card.top + 28, 360, card_height - 56)
    solved_image = ui.scale_cover(
        load_level_image(current_level["image"]),
        preview_rect.width,
        preview_rect.height
    )
    preview_surface = pygame.Surface(preview_rect.size, pygame.SRCALPHA)
    preview_surface.blit(solved_image, (0, 0))
    mask = ui.get_rounded_mask(preview_rect.size, 24)
    preview_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    screen.blit(preview_surface, preview_rect.topleft)
    ui.draw_smooth_rect(screen, preview_rect, (255, 255, 255, 90), radius=24, width=1)

    # Right-side result panel.
    right_x = card.left + 430
    right_width = card.right - 28 - right_x

    ui.draw_text(
        screen,
        current_level.get("category_label", "PUZZLE").upper(),
        small_font,
        ui.ACCENT_BLUE,
        right_x,
        card.top + 40,
        center=False
    )
    ui.draw_text(
        screen,
        current_level["name"].upper(),
        header_font,
        ui.TEXT,
        right_x,
        card.top + 70,
        center=False
    )

    # Big time pill: this is the main achievement statistic. Tall enough
    # for the large digits so they no longer spill past the bottom edge.
    time_pill = pygame.Rect(right_x, card.top + 112, right_width, 110)
    ui.draw_glass(
        screen,
        time_pill,
        radius=22,
        tint=(*ui.WHITE, 210),
        hovered=False
    )
    ui.draw_text(screen, "TIME", small_font, ui.MUTED_TEXT, right_x + 24, time_pill.top + 16, center=False)
    ui.draw_text(
        screen,
        format_time(final_time),
        hero_font,
        ui.TEXT,
        right_x + 24,
        time_pill.top + 42,
        center=False
    )

    # Small stats below the time.
    stat_y = time_pill.bottom + 22
    ui.draw_text(screen, "PUZZLE", small_font, ui.MUTED_TEXT, right_x, stat_y, center=False)
    ui.draw_text(screen, current_level["name"], button_font, ui.TEXT, right_x, stat_y + 27, center=False)

    # The PIECES column sits to the right of the puzzle's name, however
    # long that is ("Final Scene", "The Ultimate Puzzle").
    pieces_x = right_x + max(165, button_font.size(current_level["name"])[0] + 36)
    ui.draw_text(screen, "PIECES", small_font, ui.MUTED_TEXT, pieces_x, stat_y, center=False)
    ui.draw_text(screen, str(len(puzzle.pieces)), button_font, ui.TEXT, pieces_x, stat_y + 27, center=False)

    # ---- Results row: stars earned this run, and what they paid ----
    divider_y = stat_y + 27 + 34
    pygame.draw.line(
        screen, ui.CARD_BORDER,
        (right_x, divider_y), (right_x + right_width, divider_y), 1
    )

    ui.draw_text(screen, "RESULTS", small_font, ui.MUTED_TEXT, right_x, divider_y + 14, center=False)

    results_top = divider_y + 44
    star_size = 30
    stars_width = int(star_size * 1.15 * 2 + star_size)
    ui.draw_rating_stars(
        screen, (right_x + stars_width / 2, results_top), 3, stars_earned, star_size,
        filled_color=ui.YELLOW
    )

    coin_y = results_top + 34
    coin_size = 26
    if coins_awarded > 0:
        coin_text = f"+{coins_awarded} COINS"
        coin_color = ui.TEXT
    else:
        coin_text = "NO NEW COINS"
        coin_color = ui.MUTED_TEXT
    coin_text_w = small_font.size(coin_text)[0]
    coin_row_w = coin_size + 8 + coin_text_w
    coin_x = right_x + (stars_width - coin_row_w) / 2
    if coins_awarded > 0:
        ui.draw_coin_icon(screen, (int(coin_x + coin_size / 2), coin_y), coin_size)
    ui._blit_midleft(screen, small_font, coin_text, coin_color, coin_x + coin_size + 8, coin_y)

    # ---- Actions ----
    upcoming = next_level_after(current_level)
    has_next = upcoming is not None

    if not has_next:
        primary_label = "PLAY AGAIN"
    elif upcoming.get("hidden"):
        # just earned it!
        primary_label = "THE HIDDEN PUZZLE" if "journey_index" in upcoming else "THE ULTIMATE PUZZLE"
    else:
        primary_label = "NEXT PUZZLE"
    primary_width = 300
    play_again_button = pygame.Rect(0, 0, primary_width, 58)
    play_again_button.center = (center_x, 715)

    next_level_button = play_again_button if has_next else None

    draw_gradient_button(
        play_again_button,
        ui.GRADIENT_PRIMARY[0],
        ui.GRADIENT_PRIMARY[1],
        primary_label
    )

    menu_button = pygame.Rect(0, 0, 210, 48)
    menu_button.center = (center_x, 785)
    draw_glass_button(
        menu_button,
        "BACK TO JOURNEY" if "journey_index" in current_level else ("BACK TO PACK" if puzzle_origin == "category" else "BACK TO LEVELS"),
        radius=18
    )




# ======================================================================
# WIN SCREEN PATCH - the new win screen (see apply_win_screen_patch.py)
# ======================================================================
# Everything the new win screen needs lives in this block, so it keeps
# working when other parts of the file change. The old draw_completion
# is kept above as _draw_completion_original and is used automatically
# if anything in here ever raises an error.

expand_image_button = None
wallpaper_button = None
completion_image_expanded = False   # showing the pure, unobstructed picture?
completion_coins = 0                # coins THIS clear paid out (0 on a replay)
completion_unlocks = []             # [("achievement"|"reward", definition), ...]
_completion_snapshot = None         # what the save looked like before this clear
_completion_patch_warned = False


def begin_completion_state():
    """Called the moment a puzzle is finished, BEFORE coins and unlocks
    are handed out: remembers what the save looked like so the win
    screen can show exactly what this clear added."""
    global completion_image_expanded, completion_coins
    global completion_unlocks, _completion_snapshot

    completion_image_expanded = False
    completion_coins = 0
    completion_unlocks = []

    try:
        _completion_snapshot = (
            set(save_data.get("unlocked", {})),
            set(save_data.get("rewards_unlocked", {})),
            save_data.get("coins", 0),
        )
    except Exception:
        _completion_snapshot = None


def _resolve_completion_results():
    """Works out what this clear earned (once, on the first win-screen
    frame, by which time coins and unlocks have been handed out)."""
    global completion_coins, completion_unlocks, _completion_snapshot

    snapshot = _completion_snapshot
    if snapshot is None:
        return
    _completion_snapshot = None

    old_achievements, old_rewards, old_coins = snapshot

    # Rewards used to be re-checked only at startup, so finishing a puzzle
    # never unlocked one until the next launch. Check now - refresh() only
    # ever reports a reward the first time it unlocks, so this can't
    # double up with any check the game already makes.
    try:
        import rewards as _rewards_module
        just_unlocked = _rewards_module.refresh(save_data)
        if just_unlocked:
            if "queue_toasts" in globals():
                try:
                    queue_toasts(just_unlocked, kind="reward")
                except TypeError:
                    queue_toasts(just_unlocked)
            save_manager.save(save_data)
    except Exception:
        pass

    try:
        completion_coins = max(0, save_data.get("coins", 0) - old_coins)
    except Exception:
        completion_coins = 0

    unlocks = []
    try:
        import achievements as _achievements_module
        by_key = {d["key"]: d for d in _achievements_module.definitions()}
        for key in save_data.get("unlocked", {}):
            if key not in old_achievements and key in by_key:
                unlocks.append(("achievement", by_key[key]))
    except Exception:
        pass

    try:
        import rewards as _rewards_module
        by_key = {d["key"]: d for d in _rewards_module.definitions()}
        for key in save_data.get("rewards_unlocked", {}):
            if key not in old_rewards and key in by_key:
                unlocks.append(("reward", by_key[key]))
    except Exception:
        pass

    completion_unlocks = unlocks


def handle_completion_click(pos):
    """Returns True if the click was used by the win screen's picture
    view (opening it, or closing it again)."""
    global completion_image_expanded

    if completion_image_expanded:
        completion_image_expanded = False
        return True

    if expand_image_button is not None and expand_image_button.collidepoint(pos):
        completion_image_expanded = True
        return True

    if wallpaper_button is not None and wallpaper_button.collidepoint(pos):
        toggle_completion_wallpaper()
        return True

    return False


def close_completion_image():
    global completion_image_expanded
    completion_image_expanded = False


def _win_icon(kind, center, size):
    """One icon for the PRIZES row: a coin, or an achievement/reward icon."""
    if kind == "coin" and hasattr(ui, "draw_coin_icon"):
        ui.draw_coin_icon(screen, center, size, ui.YELLOW)
        return

    if hasattr(ui, "draw_achievement_icon"):
        try:
            ui.draw_achievement_icon(screen, "gem" if kind == "coin" else kind, center, size + 2)
            return
        except Exception:
            pass

    pygame.draw.circle(screen, ui.YELLOW, center, size // 2)


def toggle_completion_wallpaper():
    """Sets (or clears) the just-solved puzzle as the menu background."""
    name = current_level["name"]
    settings["wallpaper"] = None if settings.get("wallpaper") == name else name
    save_settings()


def _draw_completion_new():
    global play_again_button, menu_button, next_level_button
    global expand_image_button, wallpaper_button

    _resolve_completion_results()

    center_x = WIDTH // 2

    solved_image = ui.scale_cover(
        load_level_image(current_level["image"]), WIDTH, HEIGHT
    )

    # ---- Pure picture view: nothing but the finished picture ----
    if completion_image_expanded:
        expand_image_button = None
        screen.blit(solved_image, (0, 0))
        close_center = (44, 44)
        ui.draw_icon_button(screen, close_center, 22, tint=(20, 24, 30, 130))
        ui.draw_close_icon(screen, close_center, 18)
        return

    elapsed = time.time() - (puzzle_end_time or time.time())
    reveal = min(1.0, elapsed / 0.45)
    ease = 1 - (1 - reveal) ** 3

    # ---- Full-screen background: the solved picture, blurred + dimmed
    # so white text stays readable whatever the picture looks like ----
    screen.blit(ui.blur_surface(solved_image, 9), (0, 0))
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((16, 20, 28, 90))
    screen.blit(dim, (0, 0))

    draw_confetti()

    # ---- Heading, with the player's name ----
    player_name = save_data.get("player_name") or "Puzzler"
    ui.draw_tracked_text(
        screen, f"AMAZING, {player_name.upper()}!", hero_font, ui.WHITE,
        center_x, 96 - int((1 - ease) * 14), tracking=2
    )
    ui.draw_text(
        screen, "YOU SOLVED IT!", hero_font, ui.WHITE,
        center_x, 140 - int((1 - ease) * 10)
    )

    # ---- Frosted panel ----
    panel = pygame.Rect(0, 0, 640, 300)
    panel.center = (center_x, 400 + int((1 - ease) * 18))
    ui.draw_frosted_panel(screen, panel, radius=28)

    stat_y = panel.top + 34
    col_w = panel.width / 3
    stats = [
        ("PUZZLE", current_level["name"]),
        ("TIME", format_time(final_time)),
        ("PIECES", str(len(puzzle.pieces))),
    ]
    for index, (label, value) in enumerate(stats):
        col_center = panel.left + col_w * (index + 0.5)
        ui.draw_text(screen, label, small_font, ui.MUTED_TEXT, col_center, stat_y)
        ui.draw_text(screen, value, header_font, ui.TEXT, col_center, stat_y + 28)

    divider_y = stat_y + 64
    pygame.draw.line(
        screen, ui.CARD_BORDER,
        (panel.left + 32, divider_y), (panel.right - 32, divider_y), 1
    )

    # ---- PRIZES: what this clear really earned ----
    ui.draw_text(screen, "PRIZES", small_font, ui.MUTED_TEXT, panel.left + 32, divider_y + 18, center=False)

    prizes = []
    if completion_coins > 0:
        prizes.append(("coin", f"+{completion_coins} COINS"))

    for _kind, definition in completion_unlocks[:3 if completion_coins <= 0 else 2]:
        prizes.append((definition.get("icon", "trophy"), str(definition["title"]).upper()))

    if not prizes:
        prizes.append(("trophy", "LEVEL COMPLETE!"))

    hidden_count = len(completion_unlocks) - (len(prizes) - (1 if completion_coins > 0 else 0))
    if hidden_count > 0:
        ui.draw_text(
            screen, f"+{hidden_count} more unlocked", small_font, ui.ACCENT_BLUE,
            panel.right - 110, divider_y + 18
        )

    prize_top = divider_y + 46
    slot_width = panel.width / len(prizes)
    for index, (icon_kind, caption) in enumerate(prizes):
        slot_center_x = panel.left + slot_width * (index + 0.5)
        _win_icon(icon_kind, (int(slot_center_x), prize_top + 17), 34)

        words = caption.split(" ")
        midpoint = (len(words) + 1) // 2
        lines = [" ".join(words[:midpoint]), " ".join(words[midpoint:])]
        for line_index, line in enumerate(lines):
            if not line:
                continue
            ui.draw_text(
                screen, line, small_font, ui.MUTED_TEXT,
                int(slot_center_x), prize_top + 42 + line_index * 18
            )

    # ---- Expand button (badge on the panel's top-right corner) ----
    expand_center = (panel.right - 20, panel.top + 20)
    expand_image_button = ui.draw_icon_button(screen, expand_center, 18, tint=(255, 255, 255, 205))
    ui.draw_expand_icon(screen, expand_center, 16)

    # ---- SET AS WALLPAPER (added by apply_wallpaper_patch.py) ----
    wallpaper_is_active = settings.get("wallpaper") == current_level["name"]
    wallpaper_button = pygame.Rect(0, 0, 210, 44)
    wallpaper_button.midtop = (center_x, panel.bottom + 176)
    if wallpaper_is_active:
        draw_gradient_button(
            wallpaper_button, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], "WALLPAPER SET"
        )
    else:
        draw_glass_button(wallpaper_button, "SET AS WALLPAPER", radius=18)

    # ---- Buttons ----
    upcoming = next_level_after(current_level)
    has_next = upcoming is not None

    if not has_next:
        primary_label = "PLAY AGAIN"
    elif upcoming.get("hidden"):
        primary_label = "THE HIDDEN PUZZLE" if "journey_index" in upcoming else "THE ULTIMATE PUZZLE"
    else:
        primary_label = "NEXT PUZZLE"

    play_again_button = pygame.Rect(0, 0, 300, 58)
    play_again_button.center = (center_x, panel.bottom + 56)
    next_level_button = play_again_button if has_next else None

    draw_gradient_button(
        play_again_button,
        ui.GRADIENT_PRIMARY[0],
        ui.GRADIENT_PRIMARY[1],
        primary_label
    )

    menu_button = pygame.Rect(0, 0, 210, 48)
    menu_button.center = (center_x, panel.bottom + 118)
    draw_glass_button(
        menu_button,
        "BACK TO JOURNEY" if "journey_index" in current_level else ("BACK TO PACK" if puzzle_origin == "category" else "BACK TO LEVELS"),
        radius=18
    )


def draw_completion():
    """The win screen. Falls back to the previous version if the new one
    ever raises, so a problem here can never crash the game."""
    global _completion_patch_warned

    try:
        _draw_completion_new()
    except Exception as error:
        if not _completion_patch_warned:
            print("New win screen failed, using the old one:", repr(error))
            _completion_patch_warned = True
        _draw_completion_original()


# --------------------------------------------------
# Content pages: Daily Challenge / Gallery / Achievements
# (each one is opened from the PLAY / COLLECTION groups in the sidebar)
# --------------------------------------------------

# --- Data hooks -------------------------------------------------
# Filled in from save.json right after this block (see "Load saved
# progress" below). The achievements themselves live in achievements.py.

daily_stats = {"streak": 0, "best": 0, "completed": 0}

# Levels that have been finished (by level name) - used by the Gallery.
completed_level_names = set()

# The wallpaper picker: a modal opened by clicking a started category in
# the Gallery (see draw_wallpaper_picker).
gallery_card_rects = []             # (rect, category) for every clickable Gallery card
wallpaper_picker_open = False
wallpaper_picker_category = None    # the category the picker is showing
wallpaper_picker_tile_rects = []    # (rect, level_name_or_None) - None means "Default look"
wallpaper_picker_close_rect = None
wallpaper_picker_panel_rect = None


# --------------------------------------------------
# "Achievement unlocked" banner
# --------------------------------------------------
# Unlocks are queued here and shown one after another: the banner slides
# down from the top edge, stays a few seconds, then slides back up.

TOAST_SLIDE_SECONDS = 0.35
TOAST_HOLD_SECONDS = 3.6

toast_queue = []        # (definition, kind) waiting to be shown - see queue_toasts
toast_current = None    # (definition, kind, time it started showing) or None
toast_click_rect = None

TOAST_LABELS = {
    "achievement": "ACHIEVEMENT UNLOCKED",
    "reward": "NEW UNLOCK",
    "cheat": "DEV CHEAT",
}


def queue_toasts(unlocked_definitions, kind="achievement"):
    toast_queue.extend((definition, kind) for definition in unlocked_definitions)


def draw_toast():
    global toast_current, toast_click_rect

    if toast_current is None:
        toast_click_rect = None
        if not toast_queue:
            return
        definition, kind = toast_queue.pop(0)
        toast_current = (definition, kind, time.time())

    definition, kind, started_at = toast_current
    age = time.time() - started_at
    total = TOAST_SLIDE_SECONDS * 2 + TOAST_HOLD_SECONDS

    if age >= total:
        toast_current = None
        return

    # 0 = fully hidden above the screen, 1 = fully shown (eased)
    if age < TOAST_SLIDE_SECONDS:
        t = age / TOAST_SLIDE_SECONDS
    elif age > total - TOAST_SLIDE_SECONDS:
        t = (total - age) / TOAST_SLIDE_SECONDS
    else:
        t = 1.0
    slide = 1 - (1 - t) ** 3

    panel = pygame.Rect(0, 0, 480, 84)
    panel.centerx = WIDTH // 2
    panel.top = int(-panel.height + (panel.height + 16) * slide)
    toast_click_rect = panel.copy()

    ui.draw_glass(screen, panel, radius=26, tint=(*ui.WHITE, 240))
    ui.draw_achievement_icon(screen, definition["icon"], (panel.left + 54, panel.centery), 56)
    ui.draw_text(
        screen, TOAST_LABELS.get(kind, TOAST_LABELS["achievement"]), small_font, ui.ACCENT_BLUE,
        panel.left + 100, panel.top + 20, center=False
    )
    ui.draw_text(
        screen, definition["title"], button_font, ui.TEXT,
        panel.left + 100, panel.top + 44, center=False
    )


# --------------------------------------------------
# Load saved progress (save.json) - fills in everything above from disk,
# so a fresh launch shows real numbers instead of the placeholder zeros.
# --------------------------------------------------

save_data = save_manager.load()
_save_names_changed = save_manager.migrate_level_names(save_data, LEGACY_LEVEL_NAME_MAP)
_valid_level_names = {level["name"] for level in LEVELS + journey.JOURNEY_ALL}
if save_data.get("last_level") is not None and save_data["last_level"] not in _valid_level_names:
    save_data["last_level"] = None
    _save_names_changed = True
if _save_names_changed:
    save_manager.save(save_data)

if not save_data.get("player_name"):
    current_screen = "welcome"

# If a level's grid size was ever changed, its old saved pieces would land
# in the wrong places - this clears those and tidies the counts.
for _level in LEVELS + journey.JOURNEY_ALL:
    save_manager.sync_grid(save_data, _level["name"], _level["columns"], _level["rows"])

for _level_name, _entry in save_data["levels"].items():
    if _entry["completed"]:
        completed_level_names.add(_level_name)

daily_stats["streak"] = save_data["daily"]["streak"]
daily_stats["best"] = save_data["daily"]["best"]
daily_stats["completed"] = save_data["daily"]["completed"]

# Tell the achievement system what the game contains, then let it look at
# the loaded save: progress made before achievements existed unlocks
# whatever it has already earned. (Recording the current color theme here
# is also what starts the "try every theme" count.)
category_defs = [
    {
        "key": category["key"],
        "label": category["label"],
        "levels": [level["name"] for level in category_levels(category["key"])],
    }
    for category in CATEGORIES
]

achievements.setup(
    categories=category_defs,
    all_level_names=[level["name"] for level in LEVELS],
    journey_level_names=[level["name"] for level in journey.JOURNEY_ALL],
    theme_keys=ui.THEME_ORDER,
    level_piece_counts={
        level["name"]: level["columns"] * level["rows"] for level in REGULAR_LEVELS
    },
)
queue_toasts(achievements.on_theme_selected(save_data, settings["theme"]))

# Same idea as achievements.setup() above, but for what's UNLOCKED rather
# than what's tracked: tell rewards.py each category's key and level
# names, and Journey's level names, then let it look at the save so a
# reward already earned before this system existed (or just now, from a
# save made elsewhere) is picked up immediately rather than waiting for
# the next level completion.
rewards.setup(
    categories=[category for category in category_defs if category["key"] not in LEVEL_PACK_KEYS],
    journey_level_names=[level["name"] for level in journey.JOURNEY_ALL],
)
queue_toasts(rewards.refresh(save_data), kind="reward")


def normalize_settings_for_rewards():
    """A setting that points at something no longer unlocked - an old
    save from before this system existed, or Reset Progress just having
    re-locked it - falls back to the always-available default instead of
    staying pointed at something the player can no longer reach through
    the Settings screen. Called once at startup and again after Reset
    Progress; saves the correction if it changes anything."""
    changed = False

    if settings["dark_mode"] and not rewards.has_feature(save_data, "dark_mode"):
        settings["dark_mode"] = False
        changed = True

    if settings["theme"] != DEFAULT_THEME and not rewards.has_feature(save_data, "color_themes"):
        settings["theme"] = DEFAULT_THEME
        changed = True

    if settings["tray_style"] != DEFAULT_TRAY_STYLE and not rewards.has_feature(save_data, f"tray_{settings['tray_style']}"):
        settings["tray_style"] = DEFAULT_TRAY_STYLE
        changed = True

    if settings["header_style"] != DEFAULT_HEADER_STYLE and not rewards.has_feature(save_data, "minimal_header"):
        settings["header_style"] = DEFAULT_HEADER_STYLE
        changed = True

    if settings["board_opacity"] != DEFAULT_BOARD_OPACITY and not rewards.has_feature(save_data, "board_opacity"):
        settings["board_opacity"] = DEFAULT_BOARD_OPACITY
        changed = True

    if settings["show_hint"] and not rewards.has_feature(save_data, "hint_button"):
        settings["show_hint"] = False
        changed = True

    ui.apply_theme(settings["theme"])
    ui.apply_appearance(settings["dark_mode"])

    if changed:
        save_settings()


normalize_settings_for_rewards()

# Tell the console which of the 91 level pictures still need adding
report_missing_images()
resolve_journey_pictures()


def get_resumable_level():
    """The level the RESUME button should reopen: whichever one was last
    played, as long as it isn't finished and actually has something
    placed on the board already. Returns (level, entry) or (None, None).
    Works across restarts too, since it's read straight from save_data.
    """
    name = save_data.get("last_level")
    if not name:
        return None, None

    level = next(
        (candidate for candidate in LEVELS + journey.JOURNEY_ALL if candidate["name"] == name),
        None
    )
    if level is None:
        return None, None

    entry = save_manager.level_entry(save_data, name)
    if entry["completed"] or entry["pieces_placed"] <= 0:
        return None, None

    return level, entry


def activate_unlock_all_cheat():
    """Debug shortcut: make every progression-gated feature available."""
    unlocked_date = date.today().isoformat()

    for level in LEVELS + journey.JOURNEY_ALL:
        entry = save_manager.level_entry(save_data, level["name"])
        entry["completed"] = True
        entry["pieces_placed"] = level["columns"] * level["rows"]
        entry["best_stars"] = 3

    for definition in rewards.definitions():
        save_data["rewards_unlocked"][definition["key"]] = unlocked_date
        save_data["rewards_claimed"][definition["key"]] = unlocked_date

    for definition in achievements.definitions():
        save_data["achievements"][definition["key"]] = definition["goal"]
        save_data["unlocked"][definition["key"]] = unlocked_date

    save_data["shop"]["owned"] = {
        item["key"]: True for item in shop.SHOP_ITEMS if item["key"] != "mint"
    }
    save_data["shop"]["owned"][shop.SHOP_BUNDLE["key"]] = True
    save_data["coins"] = max(save_data.get("coins", 0), 10**15)
    save_manager.save(save_data)
    save_settings()
    queue_toasts(
        [{"title": "THE HIDDEN REWARD", "icon": "trophy"}],
        kind="cheat",
    )


def persist_puzzle_progress():
    """Snapshots the in-progress puzzle (which pieces are placed, how
    long the clock has run) into save_data and writes it to disk. Called
    after every piece drop, so progress can never be more than one piece
    behind what's on screen.
    """
    if puzzle is None or current_level is None:
        return

    entry = save_manager.level_entry(save_data, current_level["name"])
    entry["pieces_placed"] = puzzle.completed_count()
    entry["snapped_cells"] = [(piece.col, piece.row) for piece in puzzle.pieces if piece.is_snapped]
    entry["elapsed"] = get_current_time()
    entry["hint_used"] = hint_used_this_level
    entry["grid"] = [puzzle.columns, puzzle.rows]

    save_data["last_level"] = current_level["name"]
    save_manager.save(save_data)


def save_everything():
    """Last-chance save. Registered with atexit below, so it runs however
    the game ends - the window's X button, the EXIT dialog, even a crash -
    and the time since the last piece drop is never lost."""
    # Covers every place an unfinished puzzle can be waiting: on screen,
    # behind the pause panel, or behind Settings / the level menu (where
    # the clock is already frozen, so this just rewrites the same time).
    if puzzle is not None and not puzzle.is_complete():
        persist_puzzle_progress()

    save_settings()
    save_manager.save(save_data)


atexit.register(save_everything)


def wrap_text(text, font, max_width):
    """Splits text into lines that each fit within max_width pixels."""
    lines = []
    line = ""

    for word in text.split():
        candidate = word if not line else line + " " + word
        if font.size(candidate)[0] <= max_width or not line:
            line = candidate
        else:
            lines.append(line)
            line = word

    if line:
        lines.append(line)

    return lines


def draw_caption(text, center_x, y, max_width, color=None, max_lines=2, line_height=18):
    """Small centred text that wraps onto a second line, instead of running
    out past the edge of its card."""
    for index, line in enumerate(wrap_text(text, small_font, max_width)[:max_lines]):
        ui.draw_text(
            screen, line, small_font, color or ui.MUTED_TEXT,
            center_x, y + index * line_height
        )


# The tabs along the top of each space's page: (label, screen name)
PLAY_TABS = [("Levels", "menu"), ("Journey", "journey"), ("Daily Challenge", "daily")]
COLLECTION_TABS = [("Gallery", "collection")]


def draw_tabs(content, tabs, note=None):
    """The tab bar at the top of a space's page, with an optional note on
    the right. The rectangles are remembered so clicks can find them."""
    global tab_rects

    tab_rects = {}
    mouse_position = pygame.mouse.get_pos()
    height = 42
    x = content.left + 40
    y = 22

    for label, target in tabs:
        rect = pygame.Rect(x, y, button_font.size(label)[0] + 48, height)
        tab_rects[target] = rect

        is_current = current_screen == target or (
            target == "menu" and current_screen in ("levels", "category")
        )
        hovered = rect.collidepoint(mouse_position)

        if is_current:
            ui.draw_blurred_shadow(
                screen, rect, border_radius=height // 2, blur=10,
                alpha=70, color=(120, 150, 210), offset=(0, 4)
            )
            ui.draw_gradient_rect(
                screen, rect, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1],
                border_radius=height // 2
            )
            text_color = ui.TEXT
        else:
            ui.draw_smooth_rect(screen, rect, (*ui.WHITE, 235 if hovered else 170), radius=height // 2)
            ui.draw_smooth_rect(screen, rect, ui.CARD_BORDER, radius=height // 2, width=1)
            text_color = ui.TEXT if hovered else ui.MUTED_TEXT

        ui.draw_text(screen, label, button_font, text_color, rect.centerx, rect.centery)
        x = rect.right + 12

    if note:
        surface = small_font.render(note, True, ui.MUTED_TEXT)
        screen.blit(surface, surface.get_rect(midright=(content.right - 40, y + height // 2)))


def get_daily_level():
    """Today's puzzle: the same level all day, a different one tomorrow.
    Drawn only from puzzles the player has actually unlocked (see
    is_level_unlocked) - never something they haven't earned access to
    yet, and never the hidden Ultimate puzzle either.
    """
    pool = [level for level in REGULAR_LEVELS if is_level_unlocked(level)]
    if not pool:
        pool = REGULAR_LEVELS   # never happens - puzzle 1 of every category is always open

    today = time.localtime()
    index = (today.tm_year * 366 + today.tm_yday) % len(pool)
    return pool[index], index


# ---------------- Daily Challenge ----------------

def draw_daily_screen():
    global daily_play_button

    content = ui.get_content_rect()
    ui.draw_content_panel(screen, content)
    draw_tabs(content, PLAY_TABS)

    left = content.left + 40
    width = content.width - 80

    level, level_index = get_daily_level()
    pieces = level["columns"] * level["rows"]

    # ---- Hero card: today's picture on the left, details on the right ----
    hero = pygame.Rect(left, 80, width, 340)
    ui.draw_card(screen, hero, ui.CARD_BACKGROUND, ui.CARD_BORDER)

    image_rect = pygame.Rect(hero.left + 20, hero.top + 20, int(hero.width * 0.44), hero.height - 40)
    ui.draw_image_rounded(screen, load_level_thumbnail(level["image"]), image_rect, radius=20)

    text_left = image_rect.right + 32
    text_width = hero.right - 28 - text_left

    ui.draw_text(screen, "TODAY'S PUZZLE", small_font, ui.MUTED_TEXT, text_left, hero.top + 34, center=False)
    ui.draw_text(screen, time.strftime("%A, %d %B"), heading_font, ui.TEXT, text_left, hero.top + 58, center=False)
    ui.draw_text(screen, level["name"], button_font, ui.TEXT, text_left, hero.top + 108, center=False)
    ui.draw_text(screen, f"{pieces} pieces", subtitle_font, ui.MUTED_TEXT, text_left, hero.top + 136, center=False)

    # This week: one dot per day, today highlighted
    ui.draw_text(screen, "THIS WEEK", small_font, ui.MUTED_TEXT, text_left, hero.top + 176, center=False)

    dot = 34
    dot_gap = max(8, (text_width - 7 * dot) // 6)
    strip_center_y = hero.top + 226
    today_index = time.localtime().tm_wday

    for index, letter in enumerate("MTWTFSS"):
        rect = pygame.Rect(0, 0, dot, dot)
        rect.center = (text_left + dot // 2 + index * (dot + dot_gap), strip_center_y)

        if index == today_index:
            ui.draw_gradient_rect(screen, rect, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=dot // 2)
            letter_color = ui.TEXT
        else:
            ui.draw_smooth_rect(screen, rect, ui.TRACK_BACKGROUND, radius=dot // 2)
            letter_color = ui.MUTED_TEXT

        ui.draw_text(screen, letter, small_font, letter_color, rect.centerx, rect.centery)

    daily_play_button = pygame.Rect(text_left, hero.bottom - 20 - 56, text_width, 56)
    draw_gradient_button(
        daily_play_button,
        ui.GRADIENT_PRIMARY[0],
        ui.GRADIENT_PRIMARY[1],
        "PLAY TODAY'S PUZZLE",
        text_color=ui.TEXT
    )

    # ---- Stats row ----
    stats = [
        ("CURRENT STREAK", f"{save_manager.current_streak(save_data)} days"),
        ("BEST STREAK", f"{daily_stats['best']} days"),
        ("COMPLETED", f"{daily_stats['completed']}"),
    ]
    gap = 20
    stat_width = (width - gap * (len(stats) - 1)) // len(stats)

    for index, (label, value) in enumerate(stats):
        rect = pygame.Rect(left + index * (stat_width + gap), hero.bottom + 20, stat_width, 110)
        ui.draw_card(screen, rect, ui.CARD_BACKGROUND, ui.CARD_BORDER)
        ui.draw_text(screen, label, small_font, ui.MUTED_TEXT, rect.centerx, rect.top + 32)
        ui.draw_text(screen, value, heading_font, ui.TEXT, rect.centerx, rect.top + 72)


# ---------------- Gallery (finished puzzles) ----------------

def draw_gallery_screen():
    """One stamp per category (plus the hidden Ultimate), each showing a
    frosted, locked veil until at least one of its puzzles is finished.
    A started category can be clicked to pick one of its unlocked
    pictures as the menu background (see draw_wallpaper_picker)."""
    global gallery_card_rects, gallery_back_rect
    gallery_card_rects = []

    content = ui.get_content_rect()
    ui.draw_content_panel(screen, content)
    gallery_back_rect = ui.get_page_back_rect()

    collection_levels = available_regular_levels(save_data) + [ULTIMATE_LEVEL]
    collected = sum(1 for level in collection_levels if level["name"] in completed_level_names)
    draw_tabs(content, COLLECTION_TABS, f"{collected} of {len(collection_levels)} puzzles collected")
    ui.draw_page_back_button(screen, gallery_back_rect, button_font)

    columns = 5
    gap = 20
    card_width = (content.width - 80 - gap * (columns - 1)) / columns
    thumb_height = 122
    card_height = 194
    grid_top = 80

    cards = available_categories(save_data) + [{"key": "ultimate", "label": "The Ultimate Puzzle", "hidden": True}]
    mouse_position = pygame.mouse.get_pos()

    for index, category in enumerate(cards):
        row = index // columns
        column = index % columns

        rect = pygame.Rect(
            content.left + 40 + column * (card_width + gap),
            grid_top + row * (card_height + gap),
            card_width,
            card_height
        )

        is_hidden = category.get("hidden", False)
        levels = [ULTIMATE_LEVEL] if is_hidden else category_levels(category["key"])
        completed_here = sum(1 for level in levels if level["name"] in completed_level_names)
        total = len(levels)
        started = completed_here > 0

        if started:
            gallery_card_rects.append((rect, category))

        ui.draw_card(screen, rect, ui.CARD_BACKGROUND, ui.CARD_BORDER)

        thumb_rect = pygame.Rect(rect.left, rect.top, rect.width, thumb_height)

        if is_hidden and not started:
            # The Ultimate's artwork stays a complete secret until it's
            # earned: a plain tile, not a veiled picture (a veil would
            # still let the picture show through faintly).
            ui.draw_smooth_rect(
                screen, thumb_rect, (223, 229, 240, 255),
                radius=24, corners=(True, True, False, False)
            )
            ui.draw_lock_icon(screen, thumb_rect.center, 42)
        else:
            ui.draw_image_top_rounded(screen, load_level_thumbnail(levels[0]["image"]), thumb_rect, radius=24)

            if not started:
                # A frosted veil and a padlock until at least one puzzle
                # from this category has been finished.
                ui.draw_smooth_rect(
                    screen, thumb_rect, (244, 248, 253, 200),
                    radius=24, corners=(True, True, False, False)
                )
                ui.draw_lock_icon(screen, thumb_rect.center, 42)

        if started and not wallpaper_picker_open and rect.collidepoint(mouse_position):
            # A started card is clickable - a soft ring is all the hint
            # it needs.
            ui.draw_smooth_rect(screen, rect, (255, 255, 255, 235), radius=24, width=3)

        ui.draw_text(
            screen, category["label"] if started else "???", small_font,
            ui.TEXT if started else ui.MUTED_TEXT, rect.centerx, thumb_rect.bottom + 22
        )

        if completed_here >= total and total:
            caption = "Collected - tap to set as background"
        elif started:
            caption = f"{completed_here}/{total} collected - tap for background"
        elif is_hidden:
            caption = f"Finish all {len(REGULAR_LEVELS)} to unlock"
        else:
            caption = "Finish a puzzle to unlock"
        draw_caption(caption, rect.centerx, thumb_rect.bottom + 42, rect.width - 24)


_wallpaper_picker_dim_surface = None


def draw_wallpaper_picker():
    """A modal over the Gallery: choose one already-unlocked picture from
    a category (or "Default", to go back to the plain theme look) to use
    as the background on the menu pages."""
    global wallpaper_picker_tile_rects, wallpaper_picker_close_rect
    global wallpaper_picker_panel_rect, _wallpaper_picker_dim_surface

    if _wallpaper_picker_dim_surface is None:
        _wallpaper_picker_dim_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        _wallpaper_picker_dim_surface.fill((20, 24, 34, 140))
    screen.blit(_wallpaper_picker_dim_surface, (0, 0))

    category = wallpaper_picker_category
    is_hidden = category.get("hidden", False)
    levels = [ULTIMATE_LEVEL] if is_hidden else category_levels(category["key"])

    columns = 6
    tile_size = 118
    tile_gap = 18
    tiles = [{"is_default": True}] + levels
    rows = math.ceil(len(tiles) / columns)

    grid_width = columns * tile_size + (columns - 1) * tile_gap
    grid_height = rows * tile_size + (rows - 1) * (tile_gap + 30) + 30

    panel = pygame.Rect(0, 0, grid_width + 80, grid_height + 156)
    panel.center = (WIDTH // 2, HEIGHT // 2)
    wallpaper_picker_panel_rect = panel
    ui.draw_frosted_panel(screen, panel, radius=28)

    ui.draw_tracked_text(
        screen, "SET AS BACKGROUND", title_font, ui.TEXT,
        panel.centerx, panel.top + 44, tracking=2
    )
    ui.draw_text(
        screen, category["label"], subtitle_font, ui.MUTED_TEXT,
        panel.centerx, panel.top + 82
    )

    # ---- Close (X) ----
    mouse_position = pygame.mouse.get_pos()
    close_size = 36
    wallpaper_picker_close_rect = pygame.Rect(0, 0, close_size, close_size)
    wallpaper_picker_close_rect.topright = (panel.right - 20, panel.top + 20)
    close_hovered = wallpaper_picker_close_rect.collidepoint(mouse_position)
    ui.draw_smooth_rect(
        screen, wallpaper_picker_close_rect,
        (255, 255, 255, 235 if close_hovered else 170), radius=close_size // 2
    )
    ui.draw_text(
        screen, "X", button_font, ui.TEXT,
        wallpaper_picker_close_rect.centerx, wallpaper_picker_close_rect.centery - 1
    )

    # ---- The picture grid ----
    grid_left = panel.centerx - grid_width // 2
    grid_top = panel.top + 118
    wallpaper_picker_tile_rects = []

    for index, tile in enumerate(tiles):
        row = index // columns
        column = index % columns
        rect = pygame.Rect(
            grid_left + column * (tile_size + tile_gap),
            grid_top + row * (tile_size + tile_gap + 30),
            tile_size, tile_size
        )

        is_default = tile.get("is_default", False)
        unlocked = True if is_default else tile["name"] in completed_level_names
        is_current = (
            (is_default and not settings.get("wallpaper"))
            or (not is_default and settings.get("wallpaper") == tile.get("name"))
        )

        if unlocked:
            wallpaper_picker_tile_rects.append((rect, None if is_default else tile["name"]))

        if is_default:
            ui.draw_smooth_rect(screen, rect, ui.CARD_BACKGROUND, radius=16)
            ui.draw_smooth_rect(screen, rect, ui.CARD_BORDER, radius=16, width=1)
            ui.draw_piece_icon(screen, rect.center, 30, ui.ACCENT_BLUE)
        elif unlocked:
            ui.draw_image_rounded(screen, load_level_thumbnail(tile["image"]), rect, radius=16)
        else:
            ui.draw_smooth_rect(screen, rect, (223, 229, 240, 255), radius=16)
            ui.draw_lock_icon(screen, rect.center, 26)

        if is_current:
            ui.draw_smooth_rect(screen, rect, ui.ACCENT_BLUE, radius=16, width=3)
        elif unlocked and rect.collidepoint(mouse_position):
            ui.draw_smooth_rect(screen, rect, (255, 255, 255, 220), radius=16, width=2)

        label = "Default" if is_default else ("Locked" if not unlocked else f"#{tile['index_in_category']}")
        ui.draw_text(
            screen, label, small_font,
            ui.TEXT if unlocked else ui.MUTED_TEXT,
            rect.centerx, rect.bottom + 16
        )


# ---------------- Achievements ----------------

# A small, deliberately sparse set of links from an achievement to the
# real reward it corresponds to in rewards.py - only where the two
# conditions genuinely match (same threshold, same puzzle(s)), so a card
# never claims a reward it doesn't actually grant. Most achievements have
# no entry here and show a "more rewards coming" placeholder - add a line
# as rewards.py grows and another match becomes exact.
ACHIEVEMENT_REWARD_LINKS = {
    "milestone_1": "dark_theme",           # both: finish your first puzzle
    "category_photography": "color_themes", # both: complete every Photography puzzle
}


# >>> ACHIEVEMENTS PAGE PATCH - start (safe to re-run; edit only via the patch)
# A small, deliberately sparse set of links from an achievement to the
# real reward it corresponds to in rewards.py - only where the two
# conditions genuinely match, so a card never claims a reward it doesn't
# grant. Most achievements have no entry and show a "more rewards coming"
# placeholder. Add a line here as rewards.py grows.
ACHIEVEMENT_REWARD_LINKS = {
    "milestone_1": "dark_theme",           # both: finish your first puzzle
    "category_abstract": "color_themes",   # both: complete every Abstract puzzle
}

# Kept if main.py already defined them earlier (so scroll position and the
# BACK rectangle survive), created otherwise.
achievements_scroll_y = globals().get("achievements_scroll_y", 0)
achievements_back_rect = globals().get("achievements_back_rect", None)

# True only when the patcher could not add a BACK hook to the event loop;
# the page then watches the mouse itself.
_ACH_BACK_POLLING = False
_ach_mouse_was_down = False


def _ach_wrap_text(text, font, max_width):
    """Word-wrap `text` to `max_width` pixels (own copy, so this page does
    not depend on main.py having a helper with a particular name)."""
    lines, line = [], ""
    for word in str(text).split():
        attempt = (line + " " + word).strip()
        if not line or font.size(attempt)[0] <= max_width:
            line = attempt
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _ach_draw_category_badge(screen, definition, rect):
    key = definition.get("key", "")
    if not key.startswith("category_"):
        return False

    category_key = key[len("category_"):]
    level = next(
        (item for item in REGULAR_LEVELS if item["category"] == category_key),
        None,
    )
    if level is None or find_level_image_file(level["image"]) is None:
        return False

    ui.draw_image_rounded(screen, load_level_thumbnail(level["image"]), rect, radius=20)

    trophy_badge = pygame.Rect(0, 0, 34, 34)
    trophy_badge.center = (rect.right - 12, rect.bottom - 12)
    ui.draw_blurred_shadow(
        screen, trophy_badge, border_radius=17, blur=4, alpha=35,
        color=(40, 44, 56), offset=(0, 2)
    )
    ui.draw_smooth_rect(screen, trophy_badge, (*ui.WHITE, 245), radius=17)
    ui.draw_achievement_icon(screen, "trophy", trophy_badge.center, 22)
    return True


# Reward keys this page knows how to draw as a real little PREVIEW of what
# they unlock (a dark tile, the game's actual theme colours) rather than a
# generic icon - add a key here as rewards.py grows and it's worth it.
_ACH_SWATCH_KEYS = {"dark_theme", "color_themes"}


def _ach_draw_swatch(screen, ui, rect, reward_key):
    """A small square that looks like the reward itself, not a generic
    icon: a near-black tile with a soft diagonal highlight for the dark
    theme, or a 2x2 grid of the game's own theme colours for the theme
    picker. Returns True if it drew something, False if `reward_key`
    isn't one this page knows how to preview (caller falls back to the
    plain icon chip)."""
    radius = 16

    if reward_key == "dark_theme":
        ui.draw_smooth_rect(screen, rect, (32, 34, 44), radius=radius)
        try:
            stripe = pygame.Surface(rect.size, pygame.SRCALPHA)
            w, h = rect.size
            pygame.draw.polygon(
                stripe, (255, 255, 255, 22),
                [(0, h * 0.55), (w * 0.55, 0), (w * 0.75, 0), (0, h * 0.78)]
            )
            get_mask = getattr(ui, "get_rounded_mask", None)
            if get_mask is not None:
                stripe.blit(get_mask(rect.size, radius), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(stripe, rect.topleft)
        except Exception:
            pass
        return True

    if reward_key == "color_themes":
        ui.draw_smooth_rect(screen, rect, ui.CARD_BACKGROUND, radius=radius)
        themes = getattr(ui, "THEMES", None)
        order = getattr(ui, "THEME_ORDER", None)
        accents = (
            [themes[key]["accent"] for key in order] if themes and order else
            [(94, 142, 214), (224, 112, 112), (176, 108, 214), (66, 118, 200)]
        )
        half_w, half_h = rect.width // 2, rect.height // 2
        quadrants = [
            pygame.Rect(rect.left, rect.top, half_w, half_h),
            pygame.Rect(rect.left + half_w, rect.top, rect.width - half_w, half_h),
            pygame.Rect(rect.left, rect.top + half_h, half_w, rect.height - half_h),
            pygame.Rect(rect.left + half_w, rect.top + half_h, rect.width - half_w, rect.height - half_h),
        ]
        for quadrant, color in zip(quadrants, accents[:4]):
            pygame.draw.rect(screen, color, quadrant)
        get_mask = getattr(ui, "get_rounded_mask", None)
        if get_mask is not None:
            try:
                layer = pygame.Surface(rect.size, pygame.SRCALPHA)
                layer.blit(screen, (0, 0), area=rect)
                layer.blit(get_mask(rect.size, radius), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                ui.draw_smooth_rect(screen, rect, ui.CARD_BACKGROUND, radius=radius)
                screen.blit(layer, rect.topleft)
            except Exception:
                pass
        return True

    return False


def draw_achievements_screen():
    """The full achievement list: one wide, two-panel card per achievement
    (progress on the left, its linked reward on the right), scrollable.
    The mouse wheel (or the Up/Down keys) scrolls it. Every colour comes
    from the ui.* theme values, so it follows dark mode and the accent
    theme, and get_content_rect() already keeps clear of the sidebar/dock
    on whichever side it is."""
    global achievements_scroll_y, achievements_back_rect, tab_rects, achievement_reward_rects, rewards_entry_rect
    global current_screen, _ach_mouse_was_down

    g = globals()
    small = g.get("small_font") or g.get("button_font")
    title_font_ = g.get("heading_font") or g.get("header_font") or g.get("button_font") or small
    body_font = g.get("subtitle_font") or small
    reward_font = g.get("button_font") or small
    progress_font = g.get("header_font") or reward_font
    page_title_font = g.get("title_font") or title_font_

    content = ui.get_content_rect()
    ui.draw_content_panel(screen, content)
    tab_rects = {}
    achievement_reward_rects = []
    ui.draw_text(
        screen, "ACHIEVEMENTS", page_title_font, ui.TEXT,
        content.left + 126, content.top + 36, center=False
    )

    rewards_module = g.get("rewards")
    rewards_by_key = {}
    if rewards_module is not None:
        try:
            rewards_by_key = {d["key"]: d for d in rewards_module.definitions()}
        except Exception:
            rewards_by_key = {}

    columns = 2
    gap = 30
    side_margin = 112
    card_radius = 24
    left = content.left + side_margin
    card_width = (content.width - side_margin * 2 - gap) // columns
    grid_top = 116
    achievements_back_rect = ui.get_page_back_rect()
    rewards_entry_rect = pygame.Rect(
        content.right - 244, achievements_back_rect.top,
        200, achievements_back_rect.height
    )

    viewport = pygame.Rect(
        content.left, content.top + grid_top,
        content.width, max(1, achievements_back_rect.top - 24 - (content.top + grid_top))
    )
    card_height = min(300, max(230, (viewport.height - gap) // 2))

    all_definitions = achievements.definitions()
    row_count = -(-len(all_definitions) // columns)   # ceil division
    total_height = row_count * card_height + max(0, row_count - 1) * gap
    max_scroll = max(0, total_height - viewport.height)

    # Up/Down keys scroll too (the wheel is handled in the event loop)
    try:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_DOWN]:
            achievements_scroll_y += 14
        if keys[pygame.K_UP]:
            achievements_scroll_y -= 14
    except Exception:
        pass

    achievements_scroll_y = max(0, min(achievements_scroll_y, max_scroll))

    previous_clip = screen.get_clip()
    screen.set_clip(viewport)

    for index, definition in enumerate(all_definitions):
        row, column = divmod(index, columns)
        rect = pygame.Rect(
            left + column * (card_width + gap),
            viewport.top + row * (card_height + gap) - achievements_scroll_y,
            card_width,
            card_height
        )

        if rect.bottom < viewport.top or rect.top > viewport.bottom:
            continue   # scrolled out of view - skip the work of drawing it

        unlocked = achievements.is_unlocked(save_data, definition["key"])
        coming_soon = definition.get("coming_soon", False)

        try:
            ui.draw_card(screen, rect, ui.WHITE, ui.CARD_BORDER, border_radius=card_radius)
        except TypeError:
            ui.draw_card(screen, rect, ui.WHITE, ui.CARD_BORDER)

        # Progress panel on the left, reward panel on the right - the
        # reward side a shade darker so they read as two zones.
        reward_width = int(card_width * 0.30)
        left_rect = pygame.Rect(rect.left, rect.top, card_width - reward_width, card_height)
        reward_rect = pygame.Rect(left_rect.right, rect.top, reward_width, card_height)

        try:
            ui.draw_smooth_rect(
                screen, reward_rect, ui.TRACK_BACKGROUND,
                radius=card_radius, corners=(False, True, False, True)
            )
        except TypeError:
            ui.draw_smooth_rect(screen, reward_rect, ui.TRACK_BACKGROUND, radius=card_radius)
        pygame.draw.line(
            screen, ui.CARD_BORDER,
            (reward_rect.left, rect.top + 16), (reward_rect.left, rect.bottom - 16)
        )
        reward_hit_rect = reward_rect.clip(viewport)
        if reward_hit_rect.width and reward_hit_rect.height:
            achievement_reward_rects.append((reward_hit_rect, None))

        # ---- Left panel: icon chip, title, description, progress ----
        # A plain near-white "chip" - like the reference's icon tiles -
        # with its own soft shadow, rather than an accent-tinted square,
        # so the icon glyph itself carries the colour.
        chip = pygame.Rect(left_rect.left + 24, left_rect.top + 28, 88, 88)
        try:
            ui.draw_blurred_shadow(screen, chip, border_radius=16, blur=6, alpha=35, color=(40, 44, 56), offset=(0, 3))
        except Exception:
            pass
        ui.draw_smooth_rect(screen, chip, (*ui.WHITE, 235), radius=20)
        if not _ach_draw_category_badge(screen, definition, chip):
            ui.draw_achievement_icon(screen, definition["icon"], chip.center, 50)
        if not unlocked:
            ui.draw_smooth_rect(screen, chip, (*ui.WHITE, 150), radius=20)

        title_lines = _ach_wrap_text(
            definition["title"], title_font_, left_rect.right - chip.right - 36
        )[:2]
        title_line_height = title_font_.get_linesize()
        title_top = chip.centery - len(title_lines) * title_line_height // 2
        for line_index, line in enumerate(title_lines):
            ui.draw_text(
                screen, line, title_font_,
                ui.MUTED_TEXT if coming_soon else ui.TEXT,
                chip.right + 16, title_top + line_index * title_line_height, center=False
            )

        for line_index, line in enumerate(_ach_wrap_text(definition["text"], body_font, left_rect.width - 48)[:2]):
            ui.draw_text(
                screen, line, body_font, ui.TEXT,
                left_rect.left + 24, chip.bottom + 16 + line_index * body_font.get_linesize(), center=False
            )

        goal = max(1, definition["goal"])
        current = achievements.progress(save_data, definition)
        if unlocked:
            current = goal
        track = pygame.Rect(left_rect.left + 24, left_rect.bottom - 38, left_rect.width - 48, 12)
        ui.draw_smooth_rect(screen, track, ui.TRACK_BACKGROUND, radius=5)
        if current > 0 and not coming_soon:
            fill = pygame.Rect(
                track.left, track.top,
                max(track.height, int(track.width * current / goal)), track.height
            )
            ui.draw_gradient_rect(screen, fill, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=5)

        fraction_label = "Coming soon" if coming_soon else f"{current}/{goal}"
        ui.draw_text(
            screen, fraction_label, progress_font, ui.TEXT,
            track.right - progress_font.size(fraction_label)[0], track.top - 26, center=False
        )

        # ---- Right panel: the linked reward, if there is one yet -
        # otherwise a plain placeholder rather than pretending every card
        # already grants something real. ----
        ui.draw_text(screen, "Reward", reward_font, ui.MUTED_TEXT, reward_rect.centerx, reward_rect.top + 32)

        reward_def = rewards_by_key.get(ACHIEVEMENT_REWARD_LINKS.get(definition["key"]))

        # The reward icon always sits in the same white chip as the
        # achievement icon on the left - a real reward or, for now, a
        # lock - so the two sides read as one consistent design instead
        # of the right side looking unfinished.
        reward_chip = pygame.Rect(0, 0, 88, 88)
        reward_chip.center = (reward_rect.centerx, reward_rect.top + 124)
        try:
            ui.draw_blurred_shadow(screen, reward_chip, border_radius=16, blur=6, alpha=35, color=(40, 44, 56), offset=(0, 3))
        except Exception:
            pass
        ui.draw_smooth_rect(screen, reward_chip, (*ui.WHITE, 235), radius=20)

        if reward_def is not None:
            achievement_reward_rects.append((reward_chip, reward_def["key"]))
            reward_unlocked = rewards_module.is_unlocked(save_data, reward_def["key"])
            reward_claimed = rewards_module.is_claimed(save_data, reward_def["key"])
            drew_swatch = (
                reward_def["key"] in _ACH_SWATCH_KEYS
                and _ach_draw_swatch(screen, ui, reward_chip, reward_def["key"])
            )
            if not drew_swatch:
                ui.draw_achievement_icon(screen, reward_def["icon"], reward_chip.center, 50)
            if not reward_unlocked:
                ui.draw_smooth_rect(screen, reward_chip, (*ui.WHITE, 150), radius=20)

            for line_index, line in enumerate(_ach_wrap_text(reward_def["title"], reward_font, reward_width - 24)[:2]):
                ui.draw_text(screen, line, reward_font, ui.TEXT, reward_rect.centerx, reward_chip.bottom + 20 + line_index * reward_font.get_linesize())

            status_label = (
                "COLLECTED" if reward_claimed
                else "READY TO COLLECT" if reward_unlocked
                else "UNLOCKABLE"
            )
            status_color = ui.ACCENT_BLUE if reward_unlocked else ui.MUTED_TEXT
            ui.draw_text(screen, status_label, reward_font, status_color, reward_rect.centerx, reward_rect.bottom - 30)
        else:
            ui.draw_lock_icon(screen, reward_chip.center, 34)
            ui.draw_text(screen, "More rewards", reward_font, ui.MUTED_TEXT, reward_rect.centerx, reward_chip.bottom + 20)
            ui.draw_text(screen, "coming soon", reward_font, ui.MUTED_TEXT, reward_rect.centerx, reward_chip.bottom + 20 + reward_font.get_linesize())

    screen.set_clip(previous_clip)

    # A thin scrollbar down the right edge - only when there's more to see
    if max_scroll > 0:
        bar = pygame.Rect(content.right - 14, viewport.top, 5, viewport.height)
        ui.draw_smooth_rect(screen, bar, ui.TRACK_BACKGROUND, radius=3)

        thumb_height = max(36, int(viewport.height * viewport.height / total_height))
        thumb_travel = viewport.height - thumb_height
        thumb_y = viewport.top + int(thumb_travel * (achievements_scroll_y / max_scroll))
        ui.draw_smooth_rect(screen, pygame.Rect(bar.left, thumb_y, bar.width, thumb_height), ui.MUTED_TEXT, radius=3)

    ui.draw_page_back_button(screen, achievements_back_rect, button_font)
    draw_gradient_button(
        rewards_entry_rect, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], "REWARDS"
    )

    # Only used when the event loop has no BACK hook (see _ACH_BACK_POLLING)
    if _ACH_BACK_POLLING:
        down = pygame.mouse.get_pressed()[0]
        if down and not _ach_mouse_was_down and achievements_back_rect.collidepoint(pygame.mouse.get_pos()):
            current_screen = "menu"
        _ach_mouse_was_down = down
# <<< ACHIEVEMENTS PAGE PATCH - end


def draw_rewards_screen():
    """A dedicated collection page for unlocked and claimable rewards."""
    global rewards_back_rect, reward_card_rects

    content = ui.get_content_rect()
    ui.draw_content_panel(screen, content)
    ui.draw_text(screen, "REWARDS", title_font, ui.TEXT, content.left + 40, content.top + 34, center=False)
    ui._blit_midright(
        screen, small_font,
        f"{rewards.unlocked_count(save_data)} unlocked",
        ui.MUTED_TEXT, content.right - 40, content.top + 54
    )

    definitions = rewards.definitions()
    columns = 2
    gap = 24
    margin = 40
    card_width = (content.width - margin * 2 - gap) // columns
    card_height = 184
    top = content.top + 108
    reward_card_rects = []

    for index, definition in enumerate(definitions):
        row, column = divmod(index, columns)
        rect = pygame.Rect(
            content.left + margin + column * (card_width + gap),
            top + row * (card_height + gap),
            card_width,
            card_height,
        )
        unlocked = rewards.is_unlocked(save_data, definition["key"])
        claimed = rewards.is_claimed(save_data, definition["key"])
        ui.draw_card(screen, rect, ui.CARD_BACKGROUND, ui.CARD_BORDER)

        chip = pygame.Rect(rect.left + 22, rect.top + 22, 58, 58)
        ui.draw_smooth_rect(screen, chip, (*ui.WHITE, 235), radius=18)
        ui.draw_achievement_icon(screen, definition["icon"], chip.center, 36)
        ui.draw_text(screen, definition["title"], heading_font, ui.TEXT, chip.right + 18, chip.top + 8, center=False)
        for line_index, line in enumerate(wrap_text(definition["text"], small_font, rect.width - 120)[:2]):
            ui.draw_text(screen, line, small_font, ui.MUTED_TEXT, chip.right + 18, chip.top + 38 + line_index * 20, center=False)

        if claimed:
            status = "COLLECTED"
            action = None
        elif unlocked:
            status = "READY TO COLLECT"
            collect_button = pygame.Rect(rect.left + 22, rect.bottom - 52, rect.width - 44, 36)
            draw_gradient_button(collect_button, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], "COLLECT")
            action = rect
        else:
            status = "LOCKED"
            action = None
        ui.draw_text(screen, status, small_font, ui.ACCENT_BLUE if unlocked else ui.MUTED_TEXT, rect.left + 22, rect.bottom - 26, center=False)
        reward_card_rects.append((rect, definition["key"], action))

    rewards_back_rect = ui.get_page_back_rect()
    ui.draw_page_back_button(screen, rewards_back_rect, button_font)


def draw_compact_achievements_screen():
    """Three-column achievement tiles matching the compact reference layout."""
    global achievements_scroll_y, achievements_back_rect, achievement_reward_rects, rewards_entry_rect

    content = ui.get_content_rect()
    ui.draw_content_panel(screen, content)
    achievement_reward_rects = []

    title_left = content.left + 80
    ui.draw_text(screen, "ACHIEVEMENTS", title_font, ui.TEXT, title_left, content.top + 34, center=False)
    ui._blit_midright(
        screen, small_font,
        f"{achievements.unlocked_count(save_data)} of {achievements.available_count()} unlocked",
        ui.MUTED_TEXT, content.right - 40, content.top + 82
    )
    rewards_entry_rect = pygame.Rect(content.right - 220, content.top + 20, 160, 40)
    draw_gradient_button(rewards_entry_rect, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], "REWARDS")

    side_margin = 75
    gap = 24
    columns = 3
    card_width = (content.width - side_margin * 2 - gap * (columns - 1)) // columns
    card_height = 210
    grid_top = content.top + 112
    footer_top = ui.get_page_back_rect().top - 24
    viewport = pygame.Rect(content.left, grid_top, content.width, max(1, footer_top - grid_top))
    definitions = achievements.definitions()
    rows = (len(definitions) + columns - 1) // columns
    total_height = rows * card_height + max(0, rows - 1) * gap
    max_scroll = max(0, total_height - viewport.height)
    achievements_scroll_y = max(0, min(achievements_scroll_y, max_scroll))

    previous_clip = screen.get_clip()
    screen.set_clip(viewport)
    for index, definition in enumerate(definitions):
        row, column = divmod(index, columns)
        rect = pygame.Rect(
            content.left + side_margin + column * (card_width + gap),
            grid_top + row * (card_height + gap) - achievements_scroll_y,
            card_width,
            card_height,
        )
        if rect.bottom < viewport.top or rect.top > viewport.bottom:
            continue

        unlocked = achievements.is_unlocked(save_data, definition["key"])
        coming_soon = definition.get("coming_soon", False)
        ui.draw_card(screen, rect, ui.CARD_BACKGROUND, ui.CARD_BORDER)

        chip = pygame.Rect(0, 0, 58, 58)
        chip.center = (rect.centerx, rect.top + 48)
        ui.draw_smooth_rect(screen, chip, (*ui.WHITE, 235), radius=20)
        ui.draw_achievement_icon(screen, definition["icon"], chip.center, 36)

        ui.draw_text(
            screen, definition["title"], heading_font,
            ui.MUTED_TEXT if coming_soon else ui.TEXT,
            rect.centerx, rect.top + 98
        )
        description_lines = wrap_text(definition["text"], small_font, rect.width - 34)[:2]
        for line_index, line in enumerate(description_lines):
            ui.draw_text(screen, line, small_font, ui.TEXT if not coming_soon else ui.MUTED_TEXT, rect.centerx, rect.top + 128 + line_index * 20)

        goal = max(1, definition["goal"])
        current = achievements.progress(save_data, definition)
        track = pygame.Rect(rect.left + 20, rect.bottom - 40, rect.width - 40, 10)
        ui.draw_smooth_rect(screen, track, ui.TRACK_BACKGROUND, radius=5)
        if current > 0 and not coming_soon:
            fill = pygame.Rect(track.left, track.top, max(track.height, int(track.width * current / goal)), track.height)
            ui.draw_gradient_rect(screen, fill, ui.GRADIENT_PRIMARY[0], ui.GRADIENT_PRIMARY[1], border_radius=5)
        label = "Coming soon" if coming_soon else ("Unlocked" if unlocked else f"{current} / {goal}")
        ui.draw_text(screen, label, small_font, ui.TEXT, rect.centerx, track.centery)
        achievement_reward_rects.append((rect, definition["key"]))

    screen.set_clip(previous_clip)
    if max_scroll > 0:
        bar = pygame.Rect(content.right - 14, viewport.top, 5, viewport.height)
        thumb_height = max(36, int(viewport.height * viewport.height / total_height))
        thumb_y = viewport.top + int((viewport.height - thumb_height) * achievements_scroll_y / max_scroll)
        ui.draw_smooth_rect(screen, bar, ui.TRACK_BACKGROUND, radius=3)
        ui.draw_smooth_rect(screen, pygame.Rect(bar.left, thumb_y, bar.width, thumb_height), ui.MUTED_TEXT, radius=3)

    achievements_back_rect = ui.get_page_back_rect()
    ui.draw_page_back_button(screen, achievements_back_rect, button_font)


# --------------------------------------------------
# Simple screen
# --------------------------------------------------

def draw_simple_screen(
    title
):
    content = ui.get_content_rect()

    ui.draw_text(
        screen,
        title,
        title_font,
        ui.TEXT,
        content.centerx,
        200
    )

    ui.draw_text(
        screen,
        "Coming soon...",
        subtitle_font,
        ui.MUTED_TEXT,
        content.centerx,
        245
    )

    ui.draw_piece_icon(
        screen,
        (
            content.centerx,
            330
        ),
        70,
        ui.BLUE
    )


# --------------------------------------------------
# Settings screen
# (full-bleed like the title screen - no sidebar)
# --------------------------------------------------

def set_slider_value_from_mouse(track_rect, mouse_x):
    value = (mouse_x - track_rect.left) / track_rect.width
    return max(0.0, min(1.0, value))


def open_settings(from_screen):
    """Go to the settings screen and remember where BACK should return."""
    global current_screen, settings_return_screen
    global settings_dropdown_open, reset_progress_armed, profile_name_editing

    settings_return_screen = from_screen
    settings_dropdown_open = False
    reset_progress_armed = False
    profile_name_editing = False
    current_screen = "settings"


def close_settings():
    global current_screen, settings_dropdown_open, reset_progress_armed, profile_name_editing

    settings_dropdown_open = False
    reset_progress_armed = False
    profile_name_editing = False
    save_settings()

    target = settings_return_screen
    # If the puzzle was wiped by "Reset Progress" there is nothing to
    # go back to, so land on the level menu instead.
    if target == "puzzle" and puzzle is None:
        target = "menu"
    current_screen = target


def begin_profile_name_edit():
    global profile_name_editing, profile_name_draft
    profile_name_draft = save_data.get("player_name") or ""
    profile_name_editing = True
    pygame.key.start_text_input()


def commit_profile_name_edit():
    global profile_name_editing
    save_manager.set_player_name(save_data, profile_name_draft)
    save_manager.save(save_data)
    profile_name_editing = False
    pygame.key.stop_text_input()


# The category buttons down the left side of the settings panel, top to
# bottom. Each one owns a row of controls; clicking it moves the
# highlight. (Add a new (key, label) here + a row in draw_settings_screen
# to add another section.)
SETTINGS_SECTIONS = [
    ("audio", "Audio"),
    ("graphics", "Graphics"),
    ("theme", "Theme"),
    ("tray", "Piece Tray"),
    ("header", "Puzzle Header"),
    ("sidebar", "Sidebar"),
    ("hint", "Hint"),
    ("account", "Account"),
]
TRAY_LABELS = {"pile": "Pile", "wheel": "Wheel", "carousel": "Carousel"}
HEADER_STYLE_LABELS = {"classic": "Classic", "minimal": "Minimal"}
SIDEBAR_POSITION_LABELS = {"left": "Left", "right": "Right"}


def draw_settings_screen():
    global settings_rects, settings_dropdown_rects

    # Everything settings_page.draw() needs to lay out and draw the four
    # cards - see settings_page.py's draw() docstring for what each key
    # is for. It hands back rects under the same names the click handling
    # below already expects (music_slider, tray_buttons, reset_button,
    # ...), so that code works unchanged.
    ctx = {
        "settings": settings,
        "fonts": {
            "title": title_font,
            "heading": heading_font,
            "label": header_font,
            "small": small_font,
            "button": button_font,
        },
        "tray_styles": TRAY_STYLES,
        "tray_labels": TRAY_LABELS,
        "header_styles": HEADER_STYLES,
        "header_labels": HEADER_STYLE_LABELS,
        "sidebar_positions": SIDEBAR_POSITIONS,
        "position_labels": SIDEBAR_POSITION_LABELS,
        "available_resolutions": available_resolutions,
        "resolution_label": resolution_label,
        "has_feature": lambda name: rewards.has_feature(save_data, name),
        "locked_hint": rewards.locked_hint,
        "reset_armed": reset_progress_armed,
        "reset_flash": time.time() < reset_flash_until,
        "show_version": settings_show_version,
        "version": VERSION,
        "dropdown_open": settings_dropdown_open,
        "player_name": profile_name_draft if profile_name_editing else save_data.get("player_name"),
        "profile_name_editing": profile_name_editing,
        "coins": save_data.get("coins"),
        "draw_back": lambda rect: ui.draw_page_back_button(screen, rect, button_font),
    }

    settings_rects, settings_dropdown_rects = settings_page.draw(screen, ctx)


# --------------------------------------------------
# Main loop
# --------------------------------------------------

running = True

while running:

    for event in pygame.event.get():
        # Mouse positions arrive in window pixels; the rest of the game
        # works in canvas pixels.
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            event.pos = window_to_canvas(event.pos)

        if event.type == pygame.QUIT:
            running = False

        # The window can end up resized by the OS even though it isn't
        # created with pygame.RESIZABLE (Windows' own snap/maximize
        # affordances can still do this) - without this, the rendered
        # frame stays the OLD window size and present_frame() only
        # blits into the top-left corner, leaving whatever's newly
        # exposed on the right/bottom permanently black. Re-run the
        # same canvas -> window scaling setup used on startup/resolution
        # changes so the frame always matches the window's real size.
        if event.type == pygame.VIDEORESIZE or event.type == getattr(pygame, "WINDOWRESIZED", -1):
            update_view()

        # ------------------------------------------
        # Key down (Esc pauses/resumes the puzzle screen)
        # ------------------------------------------

        if event.type == pygame.KEYDOWN:
            typed_character = getattr(event, "unicode", "").lower()
            if typed_character.isalpha():
                unlock_code_buffer = (unlock_code_buffer + typed_character)[-9:]
                if unlock_code_buffer == "unlockall":
                    activate_unlock_all_cheat()
                    unlock_code_buffer = ""
            elif event.key not in {
                getattr(pygame, key_name)
                for key_name in (
                    "K_LSHIFT", "K_RSHIFT", "K_LCTRL", "K_RCTRL",
                    "K_LALT", "K_RALT", "K_CAPSLOCK", "K_NUMLOCK",
                )
                if hasattr(pygame, key_name)
            }:
                unlock_code_buffer = ""

            # F11 works on every screen, even over the exit dialog
            if event.key == pygame.K_F11:
                set_fullscreen(not settings["fullscreen"])

            if exit_confirm_open:
                if event.key == pygame.K_ESCAPE:
                    exit_confirm_open = False

            elif event.key == pygame.K_ESCAPE and current_screen == "complete" and completion_image_expanded:
                close_completion_image()

            elif current_screen == "settings" and profile_name_editing:
                if event.key == pygame.K_RETURN:
                    commit_profile_name_edit()
                elif event.key == pygame.K_ESCAPE:
                    profile_name_editing = False
                    pygame.key.stop_text_input()
                elif event.key == pygame.K_BACKSPACE:
                    profile_name_draft = profile_name_draft[:-1]

            elif event.key == pygame.K_ESCAPE and current_screen == "settings":
                if settings_dropdown_open:
                    settings_dropdown_open = False
                else:
                    close_settings()

            elif event.key == pygame.K_ESCAPE and current_screen == "puzzle":
                if puzzle_paused:
                    resume_puzzle_clock()
                else:
                    puzzle_paused = True
                    pause_started_at = time.time()

            elif event.key == pygame.K_ESCAPE and current_screen == "menu":
                current_screen = "main_menu"

            elif event.key == pygame.K_ESCAPE and current_screen in ("category", "journey"):
                current_screen = "menu"

            elif current_screen == "welcome":
                if event.key == pygame.K_RETURN:
                    advance_welcome()
                elif event.key == pygame.K_BACKSPACE:
                    if welcome_step == 2:
                        welcome_name_input = welcome_name_input[:-1]
                elif event.key == pygame.K_ESCAPE and welcome_step > 0:
                    welcome_step -= 1
                    welcome_started_at = time.time()

        if event.type == pygame.TEXTINPUT:
            if current_screen == "welcome":
                if welcome_step == 2 and len(welcome_name_input) < 24:
                    welcome_name_input += event.text
            elif current_screen == "settings" and profile_name_editing:
                if len(profile_name_draft) < 24:
                    profile_name_draft += event.text

        # ------------------------------------------
        # Mouse down
        # ------------------------------------------

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:

                if exit_confirm_open:
                    if exit_confirm_rects.get("exit") and exit_confirm_rects["exit"].collidepoint(event.pos):
                        save_settings()
                        save_manager.save(save_data)
                        running = False
                    elif exit_confirm_rects.get("stay") and exit_confirm_rects["stay"].collidepoint(event.pos):
                        exit_confirm_open = False
                    continue

                if toast_click_rect and toast_click_rect.collidepoint(event.pos):
                    current_screen = "achievements"
                    toast_current = None
                    toast_click_rect = None
                    continue

                if wallpaper_picker_open and current_screen == "collection":
                    # A modal: every click belongs to it until it closes.
                    if wallpaper_picker_close_rect and wallpaper_picker_close_rect.collidepoint(event.pos):
                        wallpaper_picker_open = False
                    else:
                        picked = False
                        for tile_rect, level_name in wallpaper_picker_tile_rects:
                            if tile_rect.collidepoint(event.pos):
                                settings["wallpaper"] = level_name   # None = back to the default look
                                save_settings()
                                wallpaper_picker_open = False
                                picked = True
                                break
                        if not picked and wallpaper_picker_panel_rect and not wallpaper_picker_panel_rect.collidepoint(event.pos):
                            wallpaper_picker_open = False   # clicked outside the panel
                    continue

                if current_screen == "title":
                    rects = get_title_button_rects()
                    if rects["play"].collidepoint(event.pos):
                        current_screen = "main_menu"
                    elif rects["collection"].collidepoint(event.pos):
                        current_screen = "collection"
                    elif rects["achievements"].collidepoint(event.pos):
                        current_screen = "achievements"
                    elif rects["settings"].collidepoint(event.pos):
                        open_settings("title")
                    elif rects["exit"].collidepoint(event.pos):
                        exit_confirm_open = True
                    continue

                if current_screen == "welcome":
                    if welcome_picture_button and welcome_picture_button.collidepoint(event.pos):
                        if choose_profile_picture():
                            welcome_step = 5
                            welcome_started_at = time.time()
                    elif welcome_button and welcome_button.collidepoint(event.pos):
                        if welcome_step == 4:
                            if choose_profile_picture():
                                welcome_step = 5
                                welcome_started_at = time.time()
                        else:
                            advance_welcome()
                    continue

                sidebar_handled = False

                # Only the puzzle-solving and completion screens stay fully
                # sidebar-free now (deliberately distraction-free) - every
                # other page can reveal it on hover, so its nav rects are
                # always live to click on.
                if current_screen not in ("puzzle", "complete"):
                    if logo_rect and logo_rect.collidepoint(event.pos):
                        current_screen = "menu"
                        sidebar_handled = True

                    else:
                        for key, rect in nav_rects.items():
                            if not rect.collidepoint(event.pos):
                                continue

                            sidebar_handled = True

                            if key == "play":
                                current_screen = main_menu.sidebar_target(key, space_last_screen)
                            elif key in space_last_screen:
                                # PLAY / COLLECTION: open that space, on
                                # the tab you were last looking at
                                target = space_last_screen[key]
                                if target == "daily" and not is_daily_unlocked():
                                    target = "main_menu"
                                elif target == "journey" and "journey" not in visible_play_actions():
                                    target = "main_menu"
                                current_screen = target
                            elif key == "achievements":
                                current_screen = "achievements"
                            elif key == "shop":
                                current_screen = "shop"
                            elif key == "menu_home":
                                current_screen = "title"
                            elif key == "settings":
                                open_settings(current_screen)
                            elif key == "exit":
                                exit_confirm_open = True
                            break

                # ----------------------------------
                # TABS at the top of PLAY / COLLECTION pages
                # ----------------------------------
                if not sidebar_handled and current_screen in SPACE_OF_SCREEN:
                    for target, rect in tab_rects.items():
                        if rect.collidepoint(event.pos):
                            current_screen = target
                            sidebar_handled = True
                            break

                if not sidebar_handled and current_screen == "main_menu":
                    _hub_action = main_menu.hit_test(event.pos)
                    if _hub_action == "back":
                        current_screen = "title"
                    elif _hub_action == "levels":
                        current_screen = "menu"
                        levels_scroll_x = 0
                    elif _hub_action == "journey":
                        if "journey" in visible_play_actions():
                            current_screen = "journey"
                    elif _hub_action == "daily":
                        if is_daily_unlocked():
                            current_screen = "daily"

                # ----------------------------------
                # MENU / LEVELS (the category grid)
                # ----------------------------------
                if not sidebar_handled and current_screen in ["menu", "levels"]:
                    if resume_button and resume_button.collidepoint(event.pos):
                        resumable_level, _resumable_entry = get_resumable_level()
                        if resumable_level is not None:
                            open_level(resumable_level)
                    elif levels_viewport_rect and levels_viewport_rect.collidepoint(event.pos):
                        for rect, category in category_card_rects:
                            hit_rect = levels_layout.hover_rect(rect, levels_viewport_rect)
                            if hit_rect.collidepoint(event.pos):
                                if category.get("hidden"):
                                    # Only playable once every other
                                    # category is fully finished - and
                                    # it's a single puzzle, so it opens
                                    # straight away rather than into a
                                    # category detail page.
                                    if is_ultimate_unlocked(save_data):
                                        open_level(ULTIMATE_LEVEL)
                                else:
                                    selected_category_key = category["key"]
                                    current_screen = "category"
                                break

                elif not sidebar_handled and current_screen == "category":
                    if category_level_back_rect and category_level_back_rect.collidepoint(event.pos):
                        current_screen = "menu"
                    else:
                        for rect, level in category_level_card_rects:
                            if rect.collidepoint(event.pos):
                                if is_level_unlocked(level):
                                    open_level(level)
                                break

                # ----------------------------------
                # JOURNEY (the tower map - a full-screen page)
                # ----------------------------------
                elif not sidebar_handled and current_screen == "journey":
                    if journey_back_rect and journey_back_rect.collidepoint(event.pos):
                        current_screen = "menu"
                    else:
                        for rect, level, node_status in journey_node_rects:
                            # The nodes are circles, so test the distance
                            # from the centre, not the square around it
                            distance = math.hypot(
                                event.pos[0] - rect.centerx, event.pos[1] - rect.centery
                            )
                            if distance <= rect.width / 2:
                                if node_status != "locked":
                                    open_level(level)
                                break

                # ----------------------------------
                # DAILY CHALLENGE
                # ----------------------------------
                elif not sidebar_handled and current_screen == "daily":
                    if daily_play_button and daily_play_button.collidepoint(event.pos):
                        open_level(get_daily_level()[0])

                # ----------------------------------
                # PUZZLE
                # ----------------------------------
                elif not sidebar_handled and current_screen == "puzzle":
                    if puzzle_paused:
                        # Only the pause panel's own buttons are live while
                        # paused - the board and tray underneath ignore
                        # clicks until the player resumes.
                        if pause_button_rects.get("resume") and pause_button_rects["resume"].collidepoint(event.pos):
                            resume_puzzle_clock()
                        elif pause_button_rects.get("restart") and pause_button_rects["restart"].collidepoint(event.pos):
                            start_level(current_level, fresh=True)
                            selected_piece = None
                        elif pause_button_rects.get("settings") and pause_button_rects["settings"].collidepoint(event.pos):
                            # Stay paused while in settings, so the timer
                            # doesn't run and BACK returns to the pause menu.
                            open_settings("puzzle")
                        elif pause_button_rects.get("quit") and pause_button_rects["quit"].collidepoint(event.pos):
                            leave_puzzle()

                    elif back_button and back_button.collidepoint(event.pos):
                        leave_puzzle()

                    elif gear_button and gear_button.collidepoint(event.pos):
                        puzzle_paused = True
                        pause_started_at = time.time()

                    elif hint_button and hint_button.collidepoint(event.pos):
                        if try_spend_powerup("hint"):
                            hint_active = True
                            hint_used_this_level = True
                            persist_puzzle_progress()

                    elif carousel_shuffle_button and carousel_shuffle_button.collidepoint(event.pos):
                        puzzle.shuffle_tray()

                    elif shuffle_button and shuffle_button.collidepoint(event.pos):
                        if try_spend_powerup("shuffle"):
                            puzzle.shuffle_tray()

                    else:
                        # selection.press() handles three cases of its own: the click
                        # landed on an existing multi-piece selection (picks the whole
                        # thing up, returning the piece to drag), it started a new
                        # selection box on empty space (returns True), or neither, in
                        # which case it returns None and everything below runs exactly
                        # as it always has.
                        picked_up = selection.press(puzzle, event.pos)
                        if picked_up is True:
                            pass
                        elif picked_up is not None:
                            selected_piece = picked_up
                        else:
                            hit = puzzle.piece_at(event.pos)
                            if hit:
                                selected_piece = hit
                                puzzle.bring_to_front(hit)
                                hit.start_drag(event.pos)
                            elif (
                                puzzle.tray_style == "carousel"
                                and puzzle.piece_area.collidepoint(event.pos)
                            ):
                                # Pulling the empty tray space scrolls the
                                # carousel instead of picking anything up.
                                tray_scroll_dragging = True
                                tray_scroll_last_x = event.pos[0]

                # ----------------------------------
                # COMPLETE
                # ----------------------------------
                elif not sidebar_handled and current_screen == "complete" and handle_completion_click(event.pos):
                    pass

                elif not sidebar_handled and current_screen == "complete":
                    if play_again_button and play_again_button.collidepoint(event.pos):
                        # play_again_button IS next_level_button when there's
                        # a next level (draw_completion makes them the same
                        # rect) - so one check covers both button labels.
                        upcoming = next_level_after(current_level)
                        if upcoming is not None:
                            puzzle_origin = origin_for(upcoming)
                            start_level(upcoming)
                        else:
                            start_level(current_level, fresh=True)
                    elif menu_button and menu_button.collidepoint(event.pos):
                        # Back to the page this puzzle came from - its
                        # category (or the grid, for the Ultimate)
                        show_level_list_for(current_level)
                        selected_piece = None

                # ----------------------------------
                # COLLECTION / GALLERY (a started category opens the wallpaper picker)
                # ----------------------------------
                elif not sidebar_handled and current_screen == "collection":
                    if gallery_back_rect and gallery_back_rect.collidepoint(event.pos):
                        current_screen = "main_menu"
                    else:
                        for card_rect, card_category in gallery_card_rects:
                            if card_rect.collidepoint(event.pos):
                                wallpaper_picker_category = card_category
                                wallpaper_picker_open = True
                                break

                # ----------------------------------
                # ACHIEVEMENTS (its BACK pill; the tabs are handled above)
                # ----------------------------------
                elif not sidebar_handled and current_screen == "achievements":
                    if rewards_entry_rect and rewards_entry_rect.collidepoint(event.pos):
                        current_screen = "rewards"
                    elif achievements_back_rect and achievements_back_rect.collidepoint(event.pos):
                        current_screen = "menu"
                    else:
                        for reward_rect, _reward_key in achievement_reward_rects:
                            if reward_rect.collidepoint(event.pos):
                                current_screen = "rewards"
                                break

                elif not sidebar_handled and current_screen == "rewards":
                    if rewards_back_rect and rewards_back_rect.collidepoint(event.pos):
                        current_screen = "achievements"
                    else:
                        for _card_rect, reward_key, action_rect in reward_card_rects:
                            if action_rect and action_rect.collidepoint(event.pos):
                                if rewards.claim(save_data, reward_key):
                                    save_manager.save(save_data)
                                break

                elif not sidebar_handled and current_screen == "shop":
                    action = shop.hit_test(event.pos)
                    if action == "back":
                        current_screen = "main_menu"
                    elif action and action.startswith("tab:"):
                        shop.set_tab(action[4:])
                    elif action and action.startswith("theme:"):
                        theme_key = action[6:]
                        item = shop.get_item(theme_key)
                        if item and (
                            shop.is_owned(save_data, theme_key)
                            or shop.purchase_item(save_data, theme_key)
                        ):
                            settings["theme"] = theme_key
                            ui.apply_theme(theme_key)
                            save_settings()
                            save_manager.save(save_data)
                    elif action and action.startswith("wallpaper:"):
                        wallpaper_name = action[9:]
                        settings["wallpaper"] = (
                            None if settings.get("wallpaper") == wallpaper_name else wallpaper_name
                        )
                        save_settings()
                    elif action == "bundle:theme_bundle":
                        if shop.purchase_bundle(save_data):
                            save_manager.save(save_data)
                    elif action and action.startswith("level:"):
                        pack_key = action[6:]
                        if shop.is_level_pack_owned(save_data, pack_key):
                            current_screen = "menu"
                            levels_scroll_x = 10**9
                        elif shop.purchase_level_pack(save_data, pack_key):
                            save_manager.save(save_data)

                # ----------------------------------
                # SETTINGS
                # ----------------------------------
                elif not sidebar_handled and current_screen == "settings":
                    r = settings_rects

                    if settings_dropdown_open:
                        # While the option list is open, any click either
                        # picks an option or just closes the list.
                        for option_rect, option in zip(settings_dropdown_rects, available_resolutions()):
                            if option_rect.collidepoint(event.pos):
                                settings["resolution"] = option
                                apply_resolution()
                                save_settings()
                                break
                        settings_dropdown_open = False

                    elif r.get("back_button") and r["back_button"].collidepoint(event.pos):
                        close_settings()

                    elif r.get("profile_name_button") and r["profile_name_button"].collidepoint(event.pos):
                        begin_profile_name_edit()
                        reset_progress_armed = False

                    elif r.get("profile_picture_button") and r["profile_picture_button"].collidepoint(event.pos):
                        choose_profile_picture()
                        reset_progress_armed = False

                    elif r.get("resolution_dropdown") and r["resolution_dropdown"].collidepoint(event.pos):
                        settings_dropdown_open = True
                        reset_progress_armed = False

                    elif r.get("fullscreen_toggle") and r["fullscreen_toggle"].collidepoint(event.pos):
                        set_fullscreen(not settings["fullscreen"])
                        reset_progress_armed = False

                    elif r.get("mute_toggle") and r["mute_toggle"].collidepoint(event.pos):
                        settings["mute_all"] = not settings["mute_all"]
                        save_settings()

                    elif r.get("quality_toggle") and r["quality_toggle"].collidepoint(event.pos):
                        settings["quality"] = not settings["quality"]
                        save_settings()

                    elif r.get("darkmode_toggle") and r["darkmode_toggle"].collidepoint(event.pos):
                        settings["dark_mode"] = not settings["dark_mode"]
                        ui.apply_appearance(settings["dark_mode"])
                        save_settings()

                    elif r.get("music_slider") and r["music_slider"].inflate(30, 30).collidepoint(event.pos):
                        settings_dragging_slider = "music_volume"
                        settings["music_volume"] = set_slider_value_from_mouse(r["music_slider"], event.pos[0])

                    elif r.get("sfx_slider") and r["sfx_slider"].inflate(30, 30).collidepoint(event.pos):
                        settings_dragging_slider = "sfx_volume"
                        settings["sfx_volume"] = set_slider_value_from_mouse(r["sfx_slider"], event.pos[0])

                    elif r.get("board_opacity_slider") and r["board_opacity_slider"].inflate(30, 30).collidepoint(event.pos):
                        settings_dragging_slider = "board_opacity"
                        settings["board_opacity"] = set_slider_value_from_mouse(r["board_opacity_slider"], event.pos[0])
                        apply_board_opacity()

                    elif r.get("reset_button") and r["reset_button"].collidepoint(event.pos):
                        if reset_progress_armed:
                            puzzle = None
                            selected_piece = None
                            puzzle_paused = False
                            pause_started_at = None
                            current_level = LEVELS[0]
                            hint_used_this_level = False
                            reset_progress_armed = False
                            reset_flash_until = time.time() + 1.6
                            if settings_return_screen == "puzzle":
                                settings_return_screen = "menu"

                            # Wipe saved progress too - completed levels,
                            # the daily streak, achievements, all of it.
                            save_manager.reset(save_data)
                            settings["wallpaper"] = None
                            settings["header_style"] = DEFAULT_HEADER_STYLE
                            settings["board_opacity"] = DEFAULT_BOARD_OPACITY
                            normalize_settings_for_rewards()
                            save_settings()
                            save_manager.save(save_data)
                            completed_level_names.clear()
                            toast_queue.clear()
                            toast_current = None
                            # the theme in use right now counts as tried
                            achievements.on_theme_selected(save_data, settings["theme"])
                            save_manager.save(save_data)
                            daily_stats["streak"] = 0
                            daily_stats["best"] = 0
                            daily_stats["completed"] = 0
                            welcome_name_input = ""
                            welcome_started_at = time.time()
                            welcome_step = 0
                            current_screen = "welcome"
                        else:
                            reset_progress_armed = True

                    elif r.get("version_button") and r["version_button"].collidepoint(event.pos):
                        settings_show_version = not settings_show_version
                        reset_progress_armed = False

                    elif r.get("hint_toggle") and r["hint_toggle"].collidepoint(event.pos):
                        settings["show_hint"] = not settings["show_hint"]
                        reset_progress_armed = False
                        save_settings()

                    elif any(rect.collidepoint(event.pos) for _, rect in r.get("theme_swatches", [])):
                        for theme_key, rect in r["theme_swatches"]:
                            if rect.collidepoint(event.pos):
                                settings["theme"] = theme_key
                                ui.apply_theme(theme_key)
                                queue_toasts(achievements.on_theme_selected(save_data, theme_key))
                        reset_progress_armed = False
                        save_settings()
                        save_manager.save(save_data)

                    elif any(rect.collidepoint(event.pos) for _, rect in r.get("tray_buttons", [])):
                        for style, rect in r["tray_buttons"]:
                            if rect.collidepoint(event.pos):
                                settings["tray_style"] = style
                        reset_progress_armed = False
                        save_settings()

                    elif any(rect.collidepoint(event.pos) for _, rect in r.get("header_style_buttons", [])):
                        for style, rect in r["header_style_buttons"]:
                            if rect.collidepoint(event.pos):
                                settings["header_style"] = style
                        reset_progress_armed = False
                        save_settings()

                    elif any(rect.collidepoint(event.pos) for _, rect in r.get("sidebar_position_buttons", [])):
                        for position, rect in r["sidebar_position_buttons"]:
                            if rect.collidepoint(event.pos):
                                settings["sidebar_position"] = position
                        reset_progress_armed = False
                        save_settings()

                    else:
                        # Category buttons (Audio / Graphics / Account)
                        # just move the mint highlight for now.
                        for key, _label in SETTINGS_SECTIONS:
                            if r.get("section_" + key) and r["section_" + key].collidepoint(event.pos):
                                settings_section = key
                        reset_progress_armed = False

        # ------------------------------------------
        # Mouse wheel - spins the wheel tray or scrolls the carousel,
        # whichever is the active style
        # ------------------------------------------
        if event.type == pygame.MOUSEWHEEL:
            if (
                current_screen == "puzzle"
                and not puzzle_paused
                and puzzle is not None
                and puzzle.piece_area.collidepoint(pygame.mouse.get_pos())
            ):
                if puzzle.tray_style == "wheel":
                    puzzle.rotate_wheel_by(-event.y * 0.35)
                elif puzzle.tray_style == "carousel":
                    puzzle.scroll_carousel_by(-event.y * 60)
            elif current_screen == "achievements":
                achievements_scroll_y -= event.y * 60
            elif current_screen == "shop":
                shop.scroll_by(-event.y * 60)
            elif current_screen in ("menu", "levels") and levels_scroll_max > 0:
                wheel_delta = event.x * 60 if event.x else -event.y * 60
                levels_scroll_x = levels_layout.scroll_by(
                    levels_scroll_x, wheel_delta, levels_scroll_max
                )

        # ------------------------------------------
        # Mouse movement
        # ------------------------------------------
        if event.type == pygame.MOUSEMOTION:
            if puzzle_paused:
                pass
            elif selected_piece is not None and selected_piece.dragging:
                selected_piece.drag_to(event.pos)
            elif tray_scroll_dragging and puzzle is not None:
                dx = event.pos[0] - tray_scroll_last_x
                tray_scroll_last_x = event.pos[0]
                puzzle.scroll_carousel_by(-dx)
            elif puzzle is not None and current_screen == "puzzle":
                selection.motion(puzzle, event.pos)

            if settings_dragging_slider is not None:
                slider_rect_names = {
                    "music_volume": "music_slider",
                    "sfx_volume": "sfx_slider",
                    "board_opacity": "board_opacity_slider",
                }
                track_rect = settings_rects.get(slider_rect_names[settings_dragging_slider])
                if track_rect:
                    settings[settings_dragging_slider] = set_slider_value_from_mouse(track_rect, event.pos[0])
                    if settings_dragging_slider == "board_opacity":
                        apply_board_opacity()

        # ------------------------------------------
        # Mouse release
        # ------------------------------------------
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if selected_piece:
                    puzzle.release_piece(selected_piece, event.pos)
                    selected_piece = None
                    persist_puzzle_progress()
                elif puzzle is not None:
                    selection.release(puzzle, event.pos)
                hint_active = False
                tray_scroll_dragging = False
                if settings_dragging_slider is not None:
                    settings_dragging_slider = None
                    save_settings()

    # ----------------------------------------------
    # Completion check
    # ----------------------------------------------
    if (
        current_screen == "puzzle"
        and puzzle is not None
        and puzzle.is_complete()
    ):
        puzzle_end_time = time.time()
        final_time = (
            puzzle_end_time
            - puzzle_start_time
        )
        current_screen = "complete"
        begin_completion_state()
        init_confetti()

        # Finished pictures unlock in the Gallery, and stay unlocked -
        # this is now backed by save.json, not just this session.
        completed_level_names.add(current_level["name"])

        entry = save_manager.level_entry(save_data, current_level["name"])
        entry["completed"] = True
        entry["pieces_placed"] = len(puzzle.pieces)
        entry["snapped_cells"] = [(piece.col, piece.row) for piece in puzzle.pieces]
        entry["elapsed"] = 0.0
        entry["hint_used"] = False
        if entry["best_time"] is None or final_time < entry["best_time"]:
            entry["best_time"] = final_time

        # ---- Stars + coins. Coins pay out only the difference between
        # this attempt's stars and the level's previous best, so a
        # first clear (previous best 0) pays in full, a replay that
        # matches or falls short of the existing best pays nothing (no
        # grinding an easy level for repeat coins), and a replay that
        # improves the rating tops up exactly the difference rather
        # than paying the full value all over again. ----
        piece_count = current_level["columns"] * current_level["rows"]
        stars_earned = star_rating(current_level, final_time, hint_used_this_level)
        previous_best_stars = entry["best_stars"]
        coins_awarded = max(0, coins_for_completion(piece_count, stars_earned) - coins_for_completion(piece_count, previous_best_stars))
        if coins_awarded > 0:
            save_manager.add_coins(save_data, coins_awarded)
        entry["best_stars"] = max(previous_best_stars, stars_earned)

        # ---- Daily Challenge streak (only if today's daily puzzle) ----
        daily_level, _daily_index = get_daily_level()
        if current_level["name"] == daily_level["name"]:
            save_manager.record_daily_completion(save_data)
            daily_stats["streak"] = save_data["daily"]["streak"]
            daily_stats["best"] = save_data["daily"]["best"]
            daily_stats["completed"] = save_data["daily"]["completed"]

        # ---- Achievements (after the streak above, which "Daily Streak"
        # reads). Anything that unlocks pops up as a banner. ----
        queue_toasts(achievements.on_level_completed(
            save_data, final_time, hint_used_this_level,
            piece_count=current_level["columns"] * current_level["rows"]
        ))

        save_manager.save(save_data)

    # ----------------------------------------------
    # Confetti animation
    # ----------------------------------------------
    if current_screen == "complete":
        update_confetti(1 / 60)

    # ----------------------------------------------
    # Title screen hover animation
    # ----------------------------------------------
    if current_screen == "title":
        mouse_position = pygame.mouse.get_pos()
        for key, rect in get_title_button_rects().items():
            target = 1.14 if rect.collidepoint(mouse_position) else 1.0
            title_button_scale[key] += (target - title_button_scale[key]) * 0.2

    # Remember which tab each space (PLAY / COLLECTION) was last showing
    if current_screen in SPACE_OF_SCREEN:
        space_last_screen[SPACE_OF_SCREEN[current_screen]] = current_screen

    # ----------------------------------------------
    # Draw
    # ----------------------------------------------
    # Tells get_content_rect() (read by every page below) and the dock
    # itself whether the icon dock is on screen right now, and which
    # edge - same on/off condition draw_shared_sidebar() uses below, so
    # a page's own layout and what's actually drawn over it always agree.
    ui.set_sidebar_mode(
        current_screen not in ("title", "welcome", "puzzle", "complete"),
        settings["sidebar_position"]
    )

    if current_screen != "collection":
        # The wallpaper picker only exists on the Gallery - never leave it
        # "open" (and swallowing clicks) behind some other screen.
        wallpaper_picker_open = False

    ui.set_active_wallpaper(active_wallpaper_path())
    ui.draw_background(screen)

    if current_screen == "title":
        draw_title_screen()
    elif current_screen == "main_menu":
        draw_main_menu_hub()
    elif current_screen == "shop":
        draw_shop_screen()
    elif current_screen == "welcome":
        draw_welcome_screen()
    # Both "menu" and "levels" now use the unified dashboard
    elif current_screen in ["menu", "levels"]:
        draw_menu()
    elif current_screen == "category":
        draw_category_levels_screen()
    elif current_screen == "journey":
        draw_journey_screen()
    elif current_screen == "puzzle":
        draw_puzzle()
    elif current_screen == "complete":
        draw_completion()
    elif current_screen == "daily":
        draw_daily_screen()
    elif current_screen == "collection":
        draw_gallery_screen()
    elif current_screen == "achievements":
        draw_achievements_screen()
    elif current_screen == "rewards":
        draw_rewards_screen()
    elif current_screen == "settings":
        draw_settings_screen()

    if current_screen not in ("title", "welcome", "puzzle", "complete"):
        draw_shared_sidebar()

    if wallpaper_picker_open and current_screen == "collection":
        draw_wallpaper_picker()

    draw_toast()

    if exit_confirm_open:
        draw_exit_confirm()

    present_frame()
    clock.tick(60)

pygame.quit()
sys.exit()

# Safe UI Redirection for Settings Screen
def draw_settings_screen(*args, **kwargs):
    return clean_settings_ui.draw_settings_screen(*args, **kwargs)
