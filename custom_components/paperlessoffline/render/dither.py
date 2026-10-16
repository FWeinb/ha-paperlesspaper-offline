"""Dithering of RGB images onto a small fixed palette.

All functions take an ``(H, W, 3)`` float32 RGB array in the 0..255 range and a
``(N, 3)`` palette and return an ``(H, W)`` uint8 array of palette positions.

Error diffusion without serpentine scanning is computed on anti-diagonal
wavefronts (``t = x + 3y``): every kernel used here only pushes error to the
right in the current row and at most two pixels left in later rows, so all
pixels on one wavefront are independent and can be processed as one numpy
batch. The result is identical to a plain raster scan. Serpentine scanning
breaks that independence and falls back to a scalar raster loop.
"""

from __future__ import annotations

import numpy as np

# (dx, dy, weight) entries and divisor.
KERNELS: dict[str, tuple[tuple[tuple[int, int, int], ...], int]] = {
    "floyd_steinberg": (((1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)), 16),
    "atkinson": (
        ((1, 0, 1), (2, 0, 1), (-1, 1, 1), (0, 1, 1), (1, 1, 1), (0, 2, 1)),
        8,
    ),
    "jarvis_judice_ninke": (
        (
            (1, 0, 7),
            (2, 0, 5),
            (-2, 1, 3),
            (-1, 1, 5),
            (0, 1, 7),
            (1, 1, 5),
            (2, 1, 3),
            (-2, 2, 1),
            (-1, 2, 3),
            (0, 2, 5),
            (1, 2, 3),
            (2, 2, 1),
        ),
        48,
    ),
    "sierra2": (
        (
            (1, 0, 4),
            (2, 0, 3),
            (-2, 1, 1),
            (-1, 1, 2),
            (0, 1, 3),
            (1, 1, 2),
            (2, 1, 1),
        ),
        16,
    ),
}

DITHER_METHODS = (*KERNELS, "bayer", "none")

_PAD = 2  # max |dx| / dy of any kernel
_WAVE = 3  # wavefront slope; must exceed the largest leftward dx in later rows

BAYER_8 = np.array(
    [
        [0, 32, 8, 40, 2, 34, 10, 42],
        [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44, 4, 36, 14, 46, 6, 38],
        [60, 28, 52, 20, 62, 30, 54, 22],
        [3, 35, 11, 43, 1, 33, 9, 41],
        [51, 19, 59, 27, 49, 17, 57, 25],
        [15, 47, 7, 39, 13, 45, 5, 37],
        [63, 31, 55, 23, 61, 29, 53, 21],
    ],
    dtype=np.float32,
)
BAYER_SPREAD = 96.0


def dither(
    image: np.ndarray, palette: np.ndarray, method: str, serpentine: bool = False
) -> np.ndarray:
    """Dither ``image`` onto ``palette`` with the named method."""
    image = np.asarray(image, dtype=np.float32)
    palette = np.asarray(palette, dtype=np.float32)
    if method == "none":
        return nearest(image, palette)
    if method == "bayer":
        return ordered(image, palette)
    if method not in KERNELS:
        raise ValueError(f"Unknown dither method: {method}")
    if serpentine:
        return error_diffusion_scalar(image, palette, method, serpentine=True)
    return error_diffusion_wavefront(image, palette, method)


def nearest(image: np.ndarray, palette: np.ndarray) -> np.ndarray:
    """Map every pixel to its nearest palette colour."""
    h, w, _ = image.shape
    flat = np.clip(image.reshape(-1, 3), 0, 255)
    return _nearest_flat(flat, palette).reshape(h, w)


def ordered(image: np.ndarray, palette: np.ndarray) -> np.ndarray:
    """Ordered (8x8 Bayer) dithering."""
    h, w, _ = image.shape
    reps = (-(-h // 8), -(-w // 8))
    threshold = np.tile(BAYER_8, reps)[:h, :w]
    offset = (threshold / 64.0 - 0.5) * BAYER_SPREAD
    return nearest(image + offset[:, :, None], palette)


def _nearest_flat(pixels: np.ndarray, palette: np.ndarray) -> np.ndarray:
    dist = ((pixels[:, None, :] - palette[None, :, :]) ** 2).sum(axis=2)
    return dist.argmin(axis=1).astype(np.uint8)


def error_diffusion_wavefront(image: np.ndarray, palette: np.ndarray, method: str) -> np.ndarray:
    """Raster-order error diffusion, batched along anti-diagonal wavefronts.

    Slow hosts are limited by numpy calls per wavefront and by cache misses, so
    each wavefront uses only plain slices: its pixels are ``w - _WAVE`` apart in
    the flat image, and the error waiting for them lives in a small ring buffer
    indexed by (wavefront, row), where every kernel tap is one contiguous slice
    a few wavefronts ahead. The nearest colour is one matrix product (|v|^2 is
    the same for every colour, so it is left out).
    """
    entries, divisor = KERNELS[method]
    h, w, _ = image.shape
    if w <= _WAVE:
        return error_diffusion_scalar(image, palette, method)
    pixels = np.ascontiguousarray(image, dtype=np.float32).reshape(-1, 3)
    out = np.zeros(h * w, dtype=np.uint8)
    # Every tap lands on a later wavefront: (wavefronts ahead, rows down, weight).
    taps = [(dx + _WAVE * dy, dy, np.float32(wt / divisor)) for dx, dy, wt in entries]
    ring = max(lead for lead, _, _ in taps) + 1
    max_dy = max(dy for _, dy, _ in taps)
    # err[t % ring, y]: error waiting for pixel (t - _WAVE * y, y). Taps that leave
    # the image land on cells no wavefront reads.
    err = np.zeros((ring, h + max_dy, 3), dtype=np.float32)
    pal = np.asarray(palette, dtype=np.float64)
    pal32 = pal.astype(np.float32)
    minus_2p = -2 * pal.T
    p_squared = (pal**2).sum(axis=1)
    step = w - _WAVE

    for t in range(w + _WAVE * (h - 1)):
        y_lo = max(0, -(-(t - w + 1) // _WAVE))
        y_hi = min(h - 1, t // _WAVE)
        on_wave = slice(t + y_lo * step, t + y_hi * step + 1, step)
        waiting = err[t % ring]
        vals = pixels[on_wave] + waiting[y_lo : y_hi + 1]
        np.clip(vals, 0, 255, out=vals)
        idx = (vals @ minus_2p + p_squared).argmin(axis=1)
        out[on_wave] = idx
        e = vals - pal32[idx]
        for lead, dy, wt in taps:
            err[(t + lead) % ring, y_lo + dy : y_hi + 1 + dy] += e * wt
        waiting[:] = 0
    return out.reshape(h, w)


def error_diffusion_scalar(
    image: np.ndarray, palette: np.ndarray, method: str, serpentine: bool = False
) -> np.ndarray:
    """Plain raster error diffusion (optionally serpentine), one pixel at a time."""
    entries, divisor = KERNELS[method]
    h, w, _ = image.shape
    pal = [tuple(float(c) for c in row) for row in palette]
    n_pal = len(pal)
    pal_range = range(n_pal)
    weights = [(dx, dy, wt / divisor) for dx, dy, wt in entries]
    max_dy = max(dy for _, dy, _ in entries)
    stride = w + 2 * _PAD
    # Rolling error rows: err_rows[k] holds row y+k, as flat [r, g, b, r, g, b, ...].
    err_rows = [[0.0] * (stride * 3) for _ in range(max_dy + 1)]
    src = image.tolist()
    out = np.zeros((h, w), dtype=np.uint8)

    for y in range(h):
        reverse = serpentine and (y & 1)
        row = src[y]
        out_row = [0] * w
        cur = err_rows[0]
        xs = range(w - 1, -1, -1) if reverse else range(w)
        sign = -1 if reverse else 1
        for x in xs:
            base = (x + _PAD) * 3
            r = row[x][0] + cur[base]
            g = row[x][1] + cur[base + 1]
            b = row[x][2] + cur[base + 2]
            r = 0.0 if r < 0 else 255.0 if r > 255 else r
            g = 0.0 if g < 0 else 255.0 if g > 255 else g
            b = 0.0 if b < 0 else 255.0 if b > 255 else b
            best = 0
            best_d = 1e18
            for i in pal_range:
                pr, pg, pb = pal[i]
                d = (r - pr) * (r - pr) + (g - pg) * (g - pg) + (b - pb) * (b - pb)
                if d < best_d:
                    best_d = d
                    best = i
            out_row[x] = best
            pr, pg, pb = pal[best]
            er, eg, eb = r - pr, g - pg, b - pb
            for dx, dy, wt in weights:
                target = err_rows[dy]
                tb = (x + sign * dx + _PAD) * 3
                target[tb] += er * wt
                target[tb + 1] += eg * wt
                target[tb + 2] += eb * wt
        out[y] = out_row
        err_rows.pop(0)
        err_rows.append([0.0] * (stride * 3))
    return out
