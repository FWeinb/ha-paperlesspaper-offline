"""Encoders for the frame's pre-dithered image formats.

The firmware reads 4-bit pixel data starting at ``bfOffBits`` as top-down rows
of ``width / 2`` bytes (high nibble = left pixel) and ignores the colour table,
so every nibble must be a device colour index. We write a negative height so
the file is also a valid top-down BMP for ordinary viewers.
"""

from __future__ import annotations

import struct

import numpy as np

from .palette import DEVICE_INDICES, PURE

_FILE_HEADER = 14
_INFO_HEADER = 40
_COLOURS = 16


def pack_nibbles(indices: np.ndarray) -> bytes:
    """Pack an (H, W) array of device nibbles (W even) into bytes."""
    h, w = indices.shape
    if w % 2:
        raise ValueError("Width must be even")
    pairs = indices.astype(np.uint8).reshape(h, w // 2, 2)
    return ((pairs[:, :, 0] << 4) | pairs[:, :, 1]).astype(np.uint8).tobytes()


def encode_bmp4(indices: np.ndarray) -> bytes:
    """Encode an (H, W) array of device nibbles as a top-down 4-bit BMP."""
    h, w = indices.shape
    row_bytes = w // 2
    if w % 8:
        # Rows must be 4-byte aligned without padding, as the firmware doesn't skip any.
        raise ValueError("Width must be a multiple of 8")
    pixel_data = pack_nibbles(indices)
    colour_table = bytearray(_COLOURS * 4)
    for pos, nibble in enumerate(DEVICE_INDICES):
        r, g, b = (int(c) for c in PURE[pos])
        colour_table[nibble * 4 : nibble * 4 + 4] = bytes((b, g, r, 0))
    offset = _FILE_HEADER + _INFO_HEADER + len(colour_table)
    size = offset + len(pixel_data)
    file_header = struct.pack("<2sIHHI", b"BM", size, 0, 0, offset)
    info_header = struct.pack(
        "<IiiHHIIiiII",
        _INFO_HEADER,
        w,
        -h,
        1,
        4,
        0,
        row_bytes * h,
        2835,
        2835,
        _COLOURS,
        0,
    )
    return file_header + info_header + bytes(colour_table) + pixel_data


def encode_raw4(indices: np.ndarray) -> bytes:
    """Encode as the firmware's raw packed format (must start with 0x66 0x66).

    The firmware only recognises raw data when the first four pixels are white,
    so they are forced to white.
    """
    data = indices.copy()
    data[0, :4] = 6
    return pack_nibbles(data)
