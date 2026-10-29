"""Validation for overlay definitions (shared by actions and the websocket API)."""

from __future__ import annotations

import secrets
from typing import Any

from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
import probatio as vol

from .const import DOMAIN
from .render.overlay import ALIGNS, ANCHORS, BACKINGS, COLORS, KINDS, SIZES
from .store import OverlayDef

REDRAWS = ("change", "photo")


def _width(value: Any) -> int | None:
    if value in (None, "", "auto", 0):
        return None
    return int(vol.All(vol.Coerce(int), vol.Range(min=5, max=100))(value))


def _optional_text(value: Any) -> str | None:
    text = cv.string(value) if value is not None else ""
    return text if text.strip() else None


OVERLAY_FIELDS: dict[str, Any] = {
    "name": cv.string,
    "template": cv.string,
    "kind": vol.In(KINDS),
    "image": cv.string,
    "enabled": cv.boolean,
    "show_if": vol.Any(None, _optional_text),
    "anchor": vol.In(ANCHORS),
    "margin": vol.All(vol.Coerce(float), vol.Range(min=0.0, max=0.3)),
    "width": _width,
    "align": vol.In(ALIGNS),
    "size": vol.In(tuple(SIZES)),
    "text_color": vol.In(tuple(COLORS)),
    "backing": vol.In(BACKINGS),
    "backing_color": vol.In(tuple(COLORS)),
    "redraw": vol.In(REDRAWS),
}
OVERLAY_SCHEMA = vol.Schema(
    {vol.Optional("id"): cv.string, **{vol.Optional(k): v for k, v in OVERLAY_FIELDS.items()}}
)


def build_overlay(data: dict[str, Any], existing: OverlayDef | None = None) -> OverlayDef:
    """A new overlay from validated fields, merged over an existing one if given.

    An overlay's kind can't change: refused with ``overlay_kind_fixed``.
    """
    if existing:
        if data.get("kind", existing.kind) != existing.kind:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="overlay_kind_fixed"
            )
        base = existing.as_dict()
    else:
        # A caller-supplied id is kept (e.g. "draft" in previews); otherwise a new one.
        base = {"id": data.get("id") or secrets.token_hex(6), "name": "Overlay"}
    merged = {**base, **{k: v for k, v in data.items() if k in OVERLAY_FIELDS}}
    merged.setdefault("template", "")
    return OverlayDef.from_dict(merged)
