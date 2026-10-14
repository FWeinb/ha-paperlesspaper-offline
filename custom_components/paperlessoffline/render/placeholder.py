"""The "no photos yet" screen, designed for the six-colour panel."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Noto Sans (SIL OFL 1.1), subset to Latin; see tools/build_fonts.py.
FONT_DIR = Path(__file__).parent / "fonts"

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Illustration size at scale 1 (a 480 px short side).
ART_W, ART_H = 240, 196


@dataclass(frozen=True)
class PlaceholderText:
    """Everything the screen says."""

    title: str
    subtitle: str
    hint: str
    footer: str


@lru_cache(maxsize=32)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONT_DIR / f"NotoSans-{'Bold' if bold else 'Regular'}.ttf"
    try:
        return ImageFont.truetype(str(path), max(8, size))
    except OSError:  # pragma: no cover - bundled with the integration
        return ImageFont.load_default(size=max(8, size))


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: object, max_width: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if line and draw.textlength(candidate, font=font) > max_width:  # type: ignore[arg-type]
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def _draw_art(draw: ImageDraw.ImageDraw, x: float, y: float, s: float) -> None:
    """A framed picture (sun over hills) hanging from a nail."""

    def p(px: float, py: float) -> tuple[int, int]:
        return round(x + px * s), round(y + py * s)

    def box(x0: float, y0: float, x1: float, y1: float) -> tuple[int, int, int, int]:
        return (*p(x0, y0), *p(x1, y1))

    line = max(2, round(3 * s))
    # Nail and wire.
    draw.line([p(120, 6), p(56, 46)], fill=BLACK, width=line)
    draw.line([p(120, 6), p(184, 46)], fill=BLACK, width=line)
    draw.ellipse(box(113, 0, 127, 14), fill=BLACK)
    # Frame, mat and picture.
    draw.rounded_rectangle(box(0, 40, 240, 196), radius=round(12 * s), fill=BLACK)
    draw.rounded_rectangle(box(12, 52, 228, 184), radius=round(5 * s), fill=WHITE)
    pic = box(26, 66, 214, 170)
    draw.rectangle(pic, fill=WHITE)
    draw.ellipse(box(150, 76, 186, 112), fill=YELLOW, outline=BLACK, width=max(1, round(2 * s)))
    draw.polygon([p(26, 170), p(26, 132), p(82, 96), p(132, 134), p(132, 170)], fill=BLUE)
    draw.polygon(
        [p(70, 170), p(124, 120), p(164, 140), p(214, 110), p(214, 170)],
        fill=GREEN,
    )
    draw.rectangle(pic, outline=BLACK, width=max(1, round(2 * s)))


def draw_placeholder(width: int, height: int, text: PlaceholderText) -> Image.Image:
    """Draw the screen as an RGB image using only the panel's pure colours."""
    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"  # no anti-aliasing: every pixel is a palette colour
    s = min(width, height) / 480
    landscape = width > height * 1.25

    title_px, sub_px, hint_px, foot_px = (round(v * s) for v in (42, 27, 20, 15))
    title_font = _font(title_px, bold=True)
    sub_font = _font(sub_px)
    hint_font = _font(hint_px)
    foot_font = _font(foot_px)
    title_lh, sub_lh, hint_lh = title_px * 1.25, sub_px * 1.3, hint_px * 1.4

    margin = 36 * s
    art_scale = s * (0.9 if landscape else 1.0)
    art_w, art_h = ART_W * art_scale, ART_H * art_scale
    text_width = (width - art_w - 3 * margin) if landscape else (width - 2 * margin)

    title_lines = _wrap(draw, text.title, title_font, text_width)
    hint_lines = _wrap(draw, text.hint, hint_font, text_width * (1.0 if landscape else 0.86))
    gap = 16 * s
    title_h = title_lh * len(title_lines)
    sub_h = sub_lh
    hint_h = hint_lh * len(hint_lines)
    accent_h = 5 * s
    block_h = title_h + gap + accent_h + gap + sub_h + gap * 0.6 + hint_h

    def text_block(x: float, y: float, anchor_x: str) -> None:
        align = "m" if anchor_x == "center" else "l"
        for line in title_lines:
            draw.text((x, y), line, fill=BLACK, font=title_font, anchor=f"{align}a")
            y += title_lh
        y += gap
        bar_w = 64 * s
        bar_x = x - bar_w / 2 if anchor_x == "center" else x
        draw.rectangle((bar_x, y, bar_x + bar_w, y + accent_h), fill=RED)
        y += accent_h + gap
        draw.text((x, y), text.subtitle, fill=RED, font=sub_font, anchor=f"{align}a")
        y += sub_h + gap * 0.6
        for line in hint_lines:
            draw.text((x, y), line, fill=BLACK, font=hint_font, anchor=f"{align}a")
            y += hint_lh

    footer_y = height - margin * 0.9
    if landscape:
        content_h = max(art_h, block_h)
        top = (footer_y - content_h) / 2
        _draw_art(draw, margin * 1.4, top + (content_h - art_h) / 2, art_scale)
        text_block(margin * 2.4 + art_w, top + (content_h - block_h) / 2, "left")
    else:
        content_h = art_h + 2.2 * gap + block_h
        top = max(margin, (footer_y - content_h) / 2)
        _draw_art(draw, (width - art_w) / 2, top, art_scale)
        text_block(width / 2, top + art_h + 2.2 * gap, "center")

    draw.text((width / 2, footer_y), text.footer, fill=BLUE, font=foot_font, anchor="md")
    return img
