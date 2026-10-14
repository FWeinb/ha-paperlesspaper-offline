"""Spectra 6 palettes and device colour indices."""

from __future__ import annotations

import numpy as np

# Device nibble values, in palette order: black, blue, green, red, yellow, white.
DEVICE_INDICES = np.array([0, 1, 2, 3, 5, 6], dtype=np.uint8)
WHITE_INDEX = 6

# Pure RGB primaries the firmware itself dithers against.
PURE = np.array(
    [
        (0x00, 0x00, 0x00),
        (0x00, 0x00, 0xFF),
        (0x00, 0xFF, 0x00),
        (0xFF, 0x00, 0x00),
        (0xFF, 0xFF, 0x00),
        (0xFF, 0xFF, 0xFF),
    ],
    dtype=np.float32,
)

# Colours as they are perceived on the physical Spectra 6 panel.
PERCEIVED = np.array(
    [
        (0x1F, 0x22, 0x26),
        (0x41, 0x6C, 0xE1),
        (0x06, 0x74, 0x06),
        (0xEA, 0x48, 0x43),
        (0xDB, 0xD5, 0x29),
        (0xD6, 0xD6, 0xD6),
    ],
    dtype=np.float32,
)

PALETTES: dict[str, np.ndarray] = {"perceived": PERCEIVED, "pure": PURE}


def get_palette(name: str) -> np.ndarray:
    """Return the RGB palette (6x3 float32) for a palette name."""
    return PALETTES.get(name, PERCEIVED)


def nibble_lut() -> np.ndarray:
    """Map device nibble value -> palette position (unused nibbles map to white)."""
    lut = np.full(16, len(DEVICE_INDICES) - 1, dtype=np.uint8)
    for pos, nibble in enumerate(DEVICE_INDICES):
        lut[nibble] = pos
    return lut
