"""Text cards: backgrounds and the presets a new card starts from."""

from __future__ import annotations

import secrets

from .render.overlay import COLORS
from .store import OverlayDef

BACKGROUND_PHOTO = "photo"
BACKGROUND_IMAGE = "image"  # a picture from a camera or image entity, or a URL
CARD_BACKGROUNDS = (*COLORS, BACKGROUND_PHOTO, BACKGROUND_IMAGE)
# How a picture background fits the frame; "default" (stored as None) is the frame's fit.
FIT_DEFAULT = "default"
BACKGROUND_FITS = (FIT_DEFAULT, "cover", "contain")
# Space around a picture background that fits with borders, in percent of the short side.
MAX_BACKGROUND_PADDING = 25
PRESETS = ("blank", "info", "notice")
# Backgrounds on which black text is hard to read.
_DARK = ("black", "blue", "red", "green")

_TEXTS = {
    "en": {
        "blank": "Card",
        "info": "Info",
        "notice": "Notice",
        "title": "Title",
        "values": "Values",
        "example": "Add your values here",
    },
    "de": {
        "blank": "Karte",
        "info": "Info",
        "notice": "Hinweis",
        "title": "Titel",
        "values": "Werte",
        "example": "Hier eigene Werte eintragen",
    },
}


def text_color_on(background: str) -> str:
    """Readable text colour on a plain background."""
    return "white" if background in _DARK else "black"


def _texts(language: str | None) -> dict[str, str]:
    return _TEXTS["de"] if (language or "").startswith("de") else _TEXTS["en"]


def preset_name(preset: str, language: str | None) -> str:
    """Default name of a card made from a preset, in HA's language."""
    return _texts(language)[preset]


def preset_overlays(preset: str, background: str, language: str | None) -> list[OverlayDef]:
    """The overlays a new card starts with, in HA's language."""
    texts = _texts(language)
    if preset == "info":
        return [
            OverlayDef(
                id=secrets.token_hex(6),
                name=texts["title"],
                template="# {{ frame.name }}",
                anchor="top_center",
                align="center",
                size="l",
            ),
            OverlayDef(
                id=secrets.token_hex(6),
                name=texts["values"],
                template="{{ date_local(now(), 'long') }}\n" + texts["example"],
                anchor="center",
                align="center",
                size="m",
            ),
        ]
    if preset == "notice":
        return [
            OverlayDef(
                id=secrets.token_hex(6),
                name=texts["notice"],
                template=texts["notice"],
                anchor="center",
                align="center",
                size="xxl",
                text_color=text_color_on(background),
                backing="none",
            )
        ]
    return []


def copy_overlays(overlays: list[OverlayDef]) -> list[OverlayDef]:
    """Copies of overlays with new ids."""
    return [OverlayDef.from_dict({**o.as_dict(), "id": secrets.token_hex(6)}) for o in overlays]
