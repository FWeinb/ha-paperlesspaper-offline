"""Slideshow ordering (pure logic)."""

from __future__ import annotations

import random

from .const import ORDER_SHUFFLE


def next_sequential(enabled: list[str], current: str | None) -> str | None:
    """Return the photo after ``current`` in ``enabled``, wrapping around."""
    if not enabled:
        return None
    if current in enabled:
        return enabled[(enabled.index(current) + 1) % len(enabled)]
    return enabled[0]


def refill_bag(
    enabled: list[str], current: str | None, rng: random.Random | None = None
) -> list[str]:
    """Return a shuffled bag of all enabled photos, not starting with ``current``."""
    bag = list(enabled)
    (rng or random).shuffle(bag)
    if len(bag) > 1 and bag[0] == current:
        bag[0], bag[-1] = bag[-1], bag[0]
    return bag


def clean_bag(bag: list[str], enabled: list[str]) -> list[str]:
    """Drop photos that are no longer enabled."""
    allowed = set(enabled)
    return [photo_id for photo_id in bag if photo_id in allowed]


def peek(
    order: str,
    enabled: list[str],
    current: str | None,
    queued: str | None,
    bag: list[str],
) -> tuple[str | None, list[str]]:
    """Return (photo to show next, possibly refilled bag) without consuming it."""
    if queued in enabled:
        return queued, bag
    if order != ORDER_SHUFFLE:
        return next_sequential(enabled, current), bag
    bag = clean_bag(bag, enabled)
    if not bag:
        bag = refill_bag(enabled, current)
    return (bag[0] if bag else None), bag
