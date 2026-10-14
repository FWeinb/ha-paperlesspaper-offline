"""Turn a source image into a frame-ready, pre-dithered BMP."""

from __future__ import annotations

from dataclasses import dataclass, field
import io
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from .bmp import encode_bmp4
from .dither import dither
from .palette import DEVICE_INDICES, PERCEIVED, get_palette

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


def load_image(data: bytes) -> Image.Image:
    """Decode image bytes, apply EXIF orientation and flatten alpha."""
    img: Image.Image = Image.open(io.BytesIO(data))
    img.load()
    return ImageOps.exif_transpose(img)


def to_rgb(img: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    """Convert to RGB, compositing any transparency over the background."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        base = Image.new("RGBA", rgba.size, (*background, 255))
        base.alpha_composite(rgba)
        return base.convert("RGB")
    return img.convert("RGB")


def fit_image(img: Image.Image, opts: RenderOptions, width: int, height: int) -> Image.Image:
    """Rotate, crop and fit an RGB image onto a width x height canvas."""
    background = BACKGROUNDS.get(opts.background, BACKGROUNDS["white"])
    if opts.rotation % 360:
        img = img.rotate(-(opts.rotation % 360), expand=True)
    if opts.crop:
        cx, cy, cw, ch = opts.crop
        iw, ih = img.size
        box = (
            round(max(0.0, cx) * iw),
            round(max(0.0, cy) * ih),
            round(min(1.0, cx + cw) * iw),
            round(min(1.0, cy + ch) * ih),
        )
        if box[2] - box[0] >= 1 and box[3] - box[1] >= 1:
            img = img.crop(box)
    iw, ih = img.size
    if opts.fit == "stretch":
        return img.resize((width, height), Image.Resampling.LANCZOS, reducing_gap=3.0)
    if opts.fit == "contain":
        scale = min(width / iw, height / ih)
        nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS, reducing_gap=3.0)
        canvas = Image.new("RGB", (width, height), background)
        canvas.paste(resized, ((width - nw) // 2, (height - nh) // 2))
        return canvas
    # cover
    scale = max(width / iw, height / ih)
    nw, nh = max(width, round(iw * scale)), max(height, round(ih * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS, reducing_gap=3.0)
    left = round(min(max(opts.focal_x * nw - width / 2, 0), nw - width))
    top = round(min(max(opts.focal_y * nh - height / 2, 0), nh - height))
    return resized.crop((left, top, left + width, top + height))


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


def render(data: bytes, opts: RenderOptions, canvas: Canvas) -> RenderResult:
    """Render encoded image bytes for a canvas. Blocking; run in an executor."""
    background = BACKGROUNDS.get(opts.background, BACKGROUNDS["white"])
    img = to_rgb(load_image(data), background)
    img = enhance(fit_image(img, opts, canvas.width, canvas.height), opts)
    rgb = np.asarray(img, dtype=np.float32)
    positions = dither(rgb, get_palette(opts.palette), opts.dither, opts.serpentine)
    return finish(positions, canvas)


def render_placeholder(title: str, lines: list[str], canvas: Canvas) -> RenderResult:
    """Render a simple text placeholder. Blocking; run in an executor."""
    img = Image.new("RGB", (canvas.width, canvas.height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    scale = min(canvas.width, canvas.height) / 480
    title_font = ImageFont.load_default(size=round(40 * scale))
    body_font = ImageFont.load_default(size=round(22 * scale))
    margin = round(40 * scale)
    draw.rectangle(
        (margin // 2, margin // 2, canvas.width - margin // 2, canvas.height - margin // 2),
        outline=(0, 0, 0),
        width=max(2, round(3 * scale)),
    )
    y = margin * 2
    draw.text((margin, y), title, fill=(0, 0, 0), font=title_font)
    y += round(70 * scale)
    for line in lines:
        draw.text((margin, y), line, fill=(0, 0, 255), font=body_font)
        y += round(36 * scale)
    positions = dither(np.asarray(img, dtype=np.float32), get_palette("pure"), "none")
    return finish(positions, canvas)


def validate_image(data: bytes) -> tuple[str, int, int]:
    """Check that bytes decode as an image; return (format, width, height)."""
    img = Image.open(io.BytesIO(data))
    img.verify()
    img = Image.open(io.BytesIO(data))
    return (img.format or "unknown", img.width, img.height)


def make_thumbnail(source: Path, target: Path, size: int = 320) -> bytes:
    """Create (or read) a cached JPEG thumbnail of an original."""
    if target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
        return target.read_bytes()
    img = to_rgb(load_image(source.read_bytes()), BACKGROUNDS["white"])
    img.thumbnail((size, size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(buf.getvalue())
    return buf.getvalue()
