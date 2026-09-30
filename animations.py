"""Small reusable animation helpers for Puzzlescape UI."""

import math


def ease_out_cubic(progress):
    """Ease a 0..1 progress value into a soft, responsive arrival."""
    progress = max(0.0, min(1.0, progress))
    return 1.0 - (1.0 - progress) ** 3


def fade_in(started_at, duration, now):
    """Return a clamped eased fade value for a UI element."""
    if duration <= 0:
        return 1.0
    return ease_out_cubic((now - started_at) / duration)


def slide_offset(started_at, duration, now, distance=28):
    """Return a small upward slide offset as an element enters."""
    return round((1.0 - fade_in(started_at, duration, now)) * distance)


def stagger_delay(index, amount=0.08):
    """Return a predictable delay for staggered onboarding elements."""
    return max(0.0, index * amount)


def breathe(now, speed=1.6, amount=0.025):
    """Return a subtle looping scale value for a calm ambient pulse."""
    return 1.0 + math.sin(now * speed) * amount
