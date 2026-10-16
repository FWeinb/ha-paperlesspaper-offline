"""Turn a source image into a frame-ready, pre-dithered BMP."""

from __future__ import annotations

from dataclasses import dataclass, field
import io
import math
import os
from pathlib import Path
import re
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance

from .bmp import encode_bmp4
from .dither import dither, nearest
from .overlay import SENTINEL, OverlayStyle, draw_overlay, new_layer
from .palette import DEVICE_INDICES, PERCEIVED, PURE, get_palette, nibble_lut
from .placeholder import PlaceholderText, draw_placeholder

try:  # HEIC support is optional at import time; the manifest requires it.
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover
    pass

FIT_MODES = ("cover", "contain", "stretch")
MOUNTINGS = ("landscape", "portrait", "landscape_flipped", "portrait_flipped")
BACKGROUNDS = {"white": (255, 255, 255), "black": (0, 0, 0)}


@dataclass(frozen=True)
class RenderOptions:
    """Fully resolved options for one render."""

    dither: str = "floyd_steinberg"
    serpentine: bool = False
    fit: str = "cover"
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    palette: str = "perceived"
    background: str = "white"
    rotation: int = 0  # clockwise degrees: 0, 90, 180, 270
    focal_x: float = 0.5
    focal_y: float = 0.5
    crop: tuple[float, float, float, float] | None = None  # x, y, w, h (0..1)

    def cache_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation used for cache keys."""
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass(frozen=True)
class Canvas:
    """Where to render: the upright canvas and how it maps onto the panel buffer."""

    width: int
    height: int
    rot90: int  # native_buffer = np.rot90(canvas, rot90)


@dataclass
class RenderResult:
    """A finished render."""

    bmp: bytes
    preview_png: bytes
    canvas: Canvas = field(repr=False)


def canvas_for(native_width: int, native_height: int, mounting: str) -> Canvas:
    """Return the canvas for a panel mounted in the given orientation.

    When the mounting has the panel's native aspect, the buffer is shown as-is
    ("_flipped" adds 180 degrees). For the other aspect, the frame shows the
    native buffer rotated 90 degrees counter-clockwise (verified on a 7" frame
    held in portrait: buffer top on the left, buffer left at the bottom), so the
    canvas is rotated clockwise into the buffer; "_flipped" is the opposite way.
    """
    native_landscape = native_width >= native_height
    wants_landscape = mounting.startswith("landscape")
    flipped = mounting.endswith("_flipped")
    if wants_landscape == native_landscape:
        return Canvas(native_width, native_height, 2 if flipped else 0)
    return Canvas(native_height, native_width, 1 if flipped else 3)


Box = tuple[float, float, float, float]  # x0, y0, x1, y1 in pixels

_T = Image.Transpose
_EXIF_TRANSPOSE = {
    2: _T.FLIP_LEFT_RIGHT,
    3: _T.ROTATE_180,
    4: _T.FLIP_TOP_BOTTOM,
    5: _T.TRANSPOSE,
    6: _T.ROTATE_270,
    7: _T.TRANSVERSE,
    8: _T.ROTATE_90,
}
_ROTATION_TRANSPOSE = {90: _T.ROTATE_270, 180: _T.ROTATE_180, 270: _T.ROTATE_90}  # clockwise
_INVERSE = {_T.ROTATE_90: _T.ROTATE_270, _T.ROTATE_270: _T.ROTATE_90}  # others undo themselves
_SWAPS_AXES = {_T.ROTATE_90, _T.ROTATE_270, _T.TRANSPOSE, _T.TRANSVERSE}
# Shrink the decoded image to at least this many times the output size before
# the final Lanczos resize, which keeps it free of visible quality loss.
SHRINK_MARGIN = 2


def open_image(data: bytes) -> Image.Image:
    """Open image bytes without decoding the pixels yet."""
    return Image.open(io.BytesIO(data))


def _transposes(img: Image.Image, rotation: int) -> list[Image.Transpose]:
    """EXIF orientation, then a clockwise rotation, as lossless transposes."""
    ops = []
    if (op := _EXIF_TRANSPOSE.get(img.getexif().get(0x0112, 1))) is not None:
        ops.append(op)
    if (op := _ROTATION_TRANSPOSE.get(rotation % 360)) is not None:
        ops.append(op)
    return ops


def _transpose_box(box: Box, size: tuple[int, int], op: Image.Transpose) -> Box:
    """Where ``box`` of an image of ``size`` ends up after transposing it."""
    x0, y0, x1, y1 = box
    w, h = size
    return {
        _T.FLIP_LEFT_RIGHT: (w - x1, y0, w - x0, y1),
        _T.FLIP_TOP_BOTTOM: (x0, h - y1, x1, h - y0),
        _T.ROTATE_180: (w - x1, h - y1, w - x0, h - y0),
        _T.ROTATE_90: (y0, w - x1, y1, w - x0),
        _T.ROTATE_270: (h - y1, x0, h - y0, x1),
        _T.TRANSPOSE: (y0, x0, y1, x1),
        _T.TRANSVERSE: (h - y1, w - x1, h - y0, w - x0),
    }[op]


def _transposed_size(size: tuple[int, int], op: Image.Transpose) -> tuple[int, int]:
    return (size[1], size[0]) if op in _SWAPS_AXES else size


def upright_size(img: Image.Image, rotation: int = 0) -> tuple[int, int]:
    """Size after EXIF orientation and a clockwise rotation."""
    size = img.size
    for op in _transposes(img, rotation):
        size = _transposed_size(size, op)
    return size


def _shrink_factor(box: Box, out: tuple[int, int]) -> int:
    """Largest integer factor that keeps ``box`` at least SHRINK_MARGIN x ``out``."""
    return max(
        1,
        math.floor(min((box[2] - box[0]) / out[0], (box[3] - box[1]) / out[1]) / SHRINK_MARGIN),
    )


def load_region(
    img: Image.Image,
    rotation: int,
    box: Box,
    out: tuple[int, int],
    background: tuple[int, int, int],
) -> tuple[Image.Image, Box]:
    """Decode just enough of ``img`` to resize its ``box`` to ``out``.

    ``box`` and ``out`` are upright (after EXIF orientation and the clockwise
    ``rotation``). The image is shrunk while decoding (JPEG DCT scaling), cut
    down to the box and shrunk by pixel averaging, but stays at least
    SHRINK_MARGIN times ``out``; only then is it turned upright. Returns the
    upright RGB image and where ``box`` lies in it.
    """
    ops = _transposes(img, rotation)
    sizes = [img.size]
    for op in ops:
        sizes.append(_transposed_size(sizes[-1], op))
    for op, size in zip(reversed(ops), reversed(sizes[1:]), strict=True):
        box = _transpose_box(box, size, _INVERSE.get(op, op))
    if sum(op in _SWAPS_AXES for op in ops) % 2:
        out = (out[1], out[0])

    if (factor := _shrink_factor(box, out)) > 1:
        width, height = img.size
        # Returns where the full image lies in the scaled decode (None if not supported).
        if drafted := img.draft(None, (-(-width // factor), -(-height // factor))):
            scale = width / drafted[1][2]
            box = (box[0] / scale, box[1] / scale, box[2] / scale, box[3] / scale)
    img.load()
    img = to_rgb(img, background)
    # Keep only the box and the pixels Lanczos reads around it (3 per output
    # pixel), shrunk by pixel averaging when there is room.
    factor = _shrink_factor(box, out)
    ratio = max((box[2] - box[0]) / out[0], (box[3] - box[1]) / out[1])
    margin = math.ceil(3 * ratio) + factor
    region = (
        max(0, math.floor(box[0]) - margin),
        max(0, math.floor(box[1]) - margin),
        min(img.size[0], math.ceil(box[2]) + margin),
        min(img.size[1], math.ceil(box[3]) + margin),
    )
    if factor > 1:
        img = img.reduce(factor, region)
    elif region != (0, 0, *img.size):
        img = img.crop(region)
    box = (
        (box[0] - region[0]) / factor,
        (box[1] - region[1]) / factor,
        (box[2] - region[0]) / factor,
        (box[3] - region[1]) / factor,
    )
    for op in ops:
        box = _transpose_box(box, img.size, op)
        img = img.transpose(op)
    return img, box


def to_rgb(img: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    """Convert to RGB, compositing any transparency over the background."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        base = Image.new("RGBA", rgba.size, (*background, 255))
        base.alpha_composite(rgba)
        return base.convert("RGB")
    return img if img.mode == "RGB" else img.convert("RGB")


def fit_plan(
    size: tuple[int, int], opts: RenderOptions, width: int, height: int
) -> tuple[Box, tuple[int, int], tuple[int, int] | None]:
    """Crop and fit an upright image of ``size`` onto a width x height canvas.

    Returns the source box, the size it is resized to and, for "contain", where
    the result is pasted onto the background.
    """
    iw, ih = size
    box: Box = (0, 0, iw, ih)
    if opts.crop:
        cx, cy, cw, ch = opts.crop
        crop = (
            round(max(0.0, cx) * iw),
            round(max(0.0, cy) * ih),
            round(min(1.0, cx + cw) * iw),
            round(min(1.0, cy + ch) * ih),
        )
        if crop[2] - crop[0] >= 1 and crop[3] - crop[1] >= 1:
            box = crop
    bw, bh = box[2] - box[0], box[3] - box[1]
    if opts.fit == "stretch":
        return box, (width, height), None
    if opts.fit == "contain":
        scale = min(width / bw, height / bh)
        nw, nh = max(1, round(bw * scale)), max(1, round(bh * scale))
        return box, (nw, nh), ((width - nw) // 2, (height - nh) // 2)
    # cover: scale up to cover the canvas, then cut out around the focal point
    scale = max(width / bw, height / bh)
    nw, nh = max(width, round(bw * scale)), max(height, round(bh * scale))
    left = round(min(max(opts.focal_x * nw - width / 2, 0), nw - width))
    top = round(min(max(opts.focal_y * nh - height / 2, 0), nh - height))
    sx, sy = nw / bw, nh / bh
    return (
        (
            box[0] + left / sx,
            box[1] + top / sy,
            box[0] + (left + width) / sx,
            box[1] + (top + height) / sy,
        ),
        (width, height),
        None,
    )


def fit_image(data: bytes, opts: RenderOptions, width: int, height: int) -> Image.Image:
    """Decode, rotate, crop and fit image bytes onto a width x height RGB canvas."""
    background = BACKGROUNDS.get(opts.background, BACKGROUNDS["white"])
    img = open_image(data)
    box, out, paste = fit_plan(upright_size(img, opts.rotation), opts, width, height)
    img, box = load_region(img, opts.rotation, box, out, background)
    resized = img.resize(out, Image.Resampling.LANCZOS, box=box, reducing_gap=3.0)
    if paste is None:
        return resized
    canvas = Image.new("RGB", (width, height), background)
    canvas.paste(resized, paste)
    return canvas


def enhance(img: Image.Image, opts: RenderOptions) -> Image.Image:
    """Apply brightness, contrast and saturation."""
    if opts.brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(opts.brightness)
    if opts.contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(opts.contrast)
    if opts.saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(opts.saturation)
    return img


def finish(positions: np.ndarray, canvas: Canvas) -> RenderResult:
    """Encode palette positions (canvas orientation) into BMP + preview."""
    native = np.rot90(positions, canvas.rot90)
    bmp = encode_bmp4(DEVICE_INDICES[native])
    preview = Image.fromarray(PERCEIVED[positions].astype(np.uint8), "RGB")
    buf = io.BytesIO()
    preview.save(buf, format="PNG", optimize=False, compress_level=3)
    return RenderResult(bmp=bmp, preview_png=buf.getvalue(), canvas=canvas)


def render_preview(data: bytes, opts: RenderOptions, canvas: Canvas) -> bytes:
    """Render only the preview PNG (no BMP). Blocking; run in an executor."""
    return render(data, opts, canvas).preview_png


def render(data: bytes, opts: RenderOptions, canvas: Canvas) -> RenderResult:
    """Render encoded image bytes for a canvas. Blocking; run in an executor."""
    img = enhance(fit_image(data, opts, canvas.width, canvas.height), opts)
    rgb = np.asarray(img, dtype=np.float32)
    positions = dither(rgb, get_palette(opts.palette), opts.dither, opts.serpentine)
    return finish(positions, canvas)


def render_placeholder(text: PlaceholderText, canvas: Canvas) -> RenderResult:
    """Render the "no photos yet" screen. Blocking; run in an executor."""
    img = draw_placeholder(canvas.width, canvas.height, text)
    positions = dither(np.asarray(img, dtype=np.float32), get_palette("pure"), "none")
    return finish(positions, canvas)


class TooManyPixelsError(ValueError):
    """The image has more pixels than allowed."""

    def __init__(self, pixels: int) -> None:
        """Initialise."""
        super().__init__(f"{pixels} pixels")
        self.pixels = pixels


def validate_image(data: bytes, max_pixels: int) -> tuple[str, int, int]:
    """Check that bytes decode as an image; return (format, width, height).

    Raises TooManyPixelsError above ``max_pixels``, including for images Pillow
    itself refuses as too large (decompression bombs).
    """
    try:
        img = Image.open(io.BytesIO(data))
    except Image.DecompressionBombError as err:
        match = re.search(r"\((\d+) pixels\)", str(err))
        raise TooManyPixelsError(int(match[1]) if match else 0) from err
    if img.width * img.height > max_pixels:
        raise TooManyPixelsError(img.width * img.height)
    img.verify()
    img = Image.open(io.BytesIO(data))
    return (img.format or "unknown", img.width, img.height)


def make_thumbnail(source: Path, target: Path, size: int = 320, rotation: int = 0) -> bytes:
    """Create (or read) a cached JPEG of an original, optionally rotated clockwise."""
    if target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
        data = target.read_bytes()
        os.utime(target)  # mtime is the last use, for eviction
        return data
    img = open_image(source.read_bytes())
    iw, ih = upright_size(img, rotation)
    scale = min(size / iw, size / ih, 1.0)
    out = (max(1, round(iw * scale)), max(1, round(ih * scale)))
    img, box = load_region(img, rotation, (0, 0, iw, ih), out, BACKGROUNDS["white"])
    img = img.resize(out, Image.Resampling.LANCZOS, box=box)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(buf.getvalue())
    return buf.getvalue()


def positions_from_bmp(bmp: bytes, canvas: Canvas) -> np.ndarray:
    """Decode one of our 4-bit BMPs back into palette positions on the canvas."""
    offset = int.from_bytes(bmp[10:14], "little")
    width = int.from_bytes(bmp[18:22], "little", signed=True)
    height = abs(int.from_bytes(bmp[22:26], "little", signed=True))
    packed = np.frombuffer(bmp, dtype=np.uint8, count=width * height // 2, offset=offset)
    nibbles = np.empty(packed.size * 2, dtype=np.uint8)
    nibbles[0::2] = packed >> 4
    nibbles[1::2] = packed & 0x0F
    native = nibble_lut()[nibbles].reshape(height, width)
    return np.rot90(native, -canvas.rot90)


def composite(
    base_bmp: bytes, overlays: list[tuple[str, OverlayStyle]], canvas: Canvas
) -> RenderResult:
    """Draw text boxes over an already dithered image. Blocking; run in an executor."""
    positions = np.ascontiguousarray(positions_from_bmp(base_bmp, canvas))
    layer = new_layer(canvas.width, canvas.height)
    for text, style in overlays:
        draw_overlay(layer, text, style)
    rgb = np.asarray(layer)
    drawn = ~(rgb == SENTINEL).all(axis=2)
    if drawn.any():
        positions[drawn] = nearest(rgb[drawn].astype(np.float32)[None, :, :], PURE)[0]
    return finish(positions, canvas)
