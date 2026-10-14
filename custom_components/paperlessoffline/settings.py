"""Layered render settings: global default -> frame default -> photo override."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.helpers import config_validation as cv
import probatio as vol

from .const import (
    GLOBAL_RENDER_DEFAULTS,
    PALETTES,
    RENDER_KEYS_FRAME_ONLY,
    RENDER_KEYS_PHOTO_ONLY,
    RENDER_KEYS_SHARED,
    ROTATIONS,
)
from .render import DITHER_METHODS, FIT_MODES, RenderOptions
from .render.pipeline import BACKGROUNDS

_FACTOR = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=3.0))
_UNIT = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0))


def _crop(value: Any) -> tuple[float, float, float, float]:
    """Validate a crop box given as [x, y, w, h] fractions."""
    if isinstance(value, Mapping):
        value = [value.get("x"), value.get("y"), value.get("width"), value.get("height")]
    box = tuple(_UNIT(v) for v in value)
    if len(box) != 4 or box[2] <= 0 or box[3] <= 0:
        raise vol.Invalid("crop must be [x, y, width, height] with positive size")
    return box


SHARED_FIELDS: dict[str, Any] = {
    "dither": vol.In(DITHER_METHODS),
    "serpentine": cv.boolean,
    "fit": vol.In(FIT_MODES),
    "brightness": _FACTOR,
    "contrast": _FACTOR,
    "saturation": _FACTOR,
    "background": vol.In(tuple(BACKGROUNDS)),
}
FRAME_FIELDS: dict[str, Any] = {**SHARED_FIELDS, "palette": vol.In(PALETTES)}
PHOTO_FIELDS: dict[str, Any] = {
    **SHARED_FIELDS,
    "rotation": vol.All(vol.Coerce(int), vol.In(ROTATIONS)),
    "focal_x": _UNIT,
    "focal_y": _UNIT,
    "crop": _crop,
}

GLOBAL_DEFAULTS_SCHEMA = vol.Schema({vol.Optional(k): v for k, v in FRAME_FIELDS.items()})
FRAME_DEFAULTS_SCHEMA = GLOBAL_DEFAULTS_SCHEMA
PHOTO_OVERRIDES_SCHEMA = vol.Schema({vol.Optional(k): v for k, v in PHOTO_FIELDS.items()})


def _pick(source: Mapping[str, Any] | None, keys: tuple[str, ...]) -> dict[str, Any]:
    if not source:
        return {}
    return {k: source[k] for k in keys if source.get(k) is not None}


def resolve(
    global_defaults: Mapping[str, Any] | None,
    frame_defaults: Mapping[str, Any] | None,
    photo_overrides: Mapping[str, Any] | None,
) -> RenderOptions:
    """Merge the three layers into fully resolved render options."""
    frame_keys = RENDER_KEYS_SHARED + RENDER_KEYS_FRAME_ONLY
    merged: dict[str, Any] = dict(GLOBAL_RENDER_DEFAULTS)
    merged.update(_pick(global_defaults, frame_keys))
    merged.update(_pick(frame_defaults, frame_keys))
    merged.update(_pick(photo_overrides, RENDER_KEYS_SHARED + RENDER_KEYS_PHOTO_ONLY))
    if (crop := merged.get("crop")) is not None:
        merged["crop"] = tuple(crop)
    return RenderOptions(**merged)
