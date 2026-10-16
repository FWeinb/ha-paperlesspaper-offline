"""Markdown text boxes drawn crisply in the panel's six colours.

A small markdown subset (headings, bold, italic, bullets, line breaks, colour
spans and ``:mdi:name:`` icons) is laid out with Pillow and drawn without
anti-aliasing onto a layer prefilled with ``SENTINEL``, using only the pure
palette colours, so it can be composited over a dithered image exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).parent / "fonts"
SENTINEL = (255, 0, 255)  # not a palette colour: marks "no overlay pixel"

COLORS: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
}
ANCHORS = (
    "top_left",
    "top_center",
    "top_right",
    "center_left",
    "center",
    "center_right",
    "bottom_left",
    "bottom_center",
    "bottom_right",
)
SIZES = {"s": 18, "m": 24, "l": 32, "xl": 44, "xxl": 72}  # px at a 480 px short side
HEADING_SCALE = {1: 1.6, 2: 1.35, 3: 1.15}
ALIGNS = ("left", "center", "right")
BACKINGS = ("box", "halo", "none")
LINE_HEIGHT = 1.3

_COLOR_NAMES = "|".join(COLORS)
_INLINE = re.compile(
    r"\\(?P<escaped>.)"
    r"|(?P<bold>\*\*)"
    r"|(?P<italic>\*)"
    r"|\{(?P<close>/)?(?P<color>" + _COLOR_NAMES + r")\}"
    r"|:mdi:(?P<icon>[a-z0-9-]+):"
)


@dataclass(frozen=True)
class OverlayStyle:
    """Where and how a text box is drawn."""

    anchor: str = "bottom_right"
    margin: float = 0.03  # fraction of the canvas' short side
    width: int | None = None  # percent of the canvas width; None = shrink to fit
    align: str = "left"
    size: str = "m"
    text_color: str = "black"
    backing: str = "box"
    backing_color: str = "white"


@dataclass
class Run:
    """A piece of text (or one icon) with uniform styling."""

    text: str
    bold: bool = False
    italic: bool = False
    color: str | None = None
    icon: str | None = None


@dataclass
class Line:
    """One source line of markdown."""

    kind: str  # "text", "heading", "bullet", "blank"
    level: int = 0
    runs: list[Run] = field(default_factory=list)


# ------------------------------------------------------------------ parsing


def parse_inline(text: str, bold: bool = False) -> list[Run]:
    """Split a line into styled runs."""
    runs: list[Run] = []
    italic = False
    colors: list[str] = []
    buffer = ""

    def flush() -> None:
        nonlocal buffer
        if buffer:
            runs.append(Run(buffer, bold, italic, colors[-1] if colors else None))
            buffer = ""

    pos = 0
    for match in _INLINE.finditer(text):
        buffer += text[pos : match.start()]
        pos = match.end()
        if match.group("escaped") is not None:
            buffer += match.group("escaped")
        elif match.group("bold"):
            flush()
            bold = not bold
        elif match.group("italic"):
            flush()
            italic = not italic
        elif match.group("color"):
            flush()
            if match.group("close"):
                if colors:
                    colors.pop()
            else:
                colors.append(match.group("color"))
        elif match.group("icon"):
            flush()
            runs.append(Run("", bold, italic, colors[-1] if colors else None, match.group("icon")))
    buffer += text[pos:]
    flush()
    return runs


def parse_markdown(text: str) -> list[Line]:
    """Parse the supported markdown subset into lines."""
    lines: list[Line] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        stripped = raw.strip()
        if not stripped:
            lines.append(Line("blank"))
        elif heading := re.match(r"^(#{1,3})\s+(.*)$", stripped):
            level = len(heading.group(1))
            lines.append(Line("heading", level, parse_inline(heading.group(2), bold=True)))
        elif bullet := re.match(r"^[-*]\s+(.*)$", stripped):
            lines.append(Line("bullet", 0, parse_inline(bullet.group(1))))
        else:
            lines.append(Line("text", 0, parse_inline(stripped)))
    # Drop leading/trailing blank lines and collapse repeats.
    out: list[Line] = []
    for line in lines:
        if line.kind == "blank" and (not out or out[-1].kind == "blank"):
            continue
        out.append(line)
    while out and out[-1].kind == "blank":
        out.pop()
    return out


# ------------------------------------------------------------------- fonts


FALLBACK_FONT = "NotoSansMath-Regular.ttf"


def _font_file(bold: bool, italic: bool) -> str:
    style = ("Bold" if bold else "") + ("Italic" if italic else "")
    return f"NotoSans-{style or 'Regular'}.ttf"


@lru_cache(maxsize=64)
def _load(file: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / file), max(6, size))


def text_font(size: int, bold: bool, italic: bool) -> ImageFont.FreeTypeFont:
    """Noto Sans in the requested style."""
    return _load(_font_file(bold, italic), size)


@lru_cache(maxsize=1)
def _coverage() -> dict[str, frozenset[int]]:
    data = json.loads((FONT_DIR / "coverage.json").read_text())
    return {name: frozenset(points) for name, points in data.items()}


def segments(
    text: str, size: int, bold: bool, italic: bool
) -> list[tuple[str, ImageFont.FreeTypeFont]]:
    """Split text into runs of characters per font, falling back for missing glyphs."""
    coverage = _coverage()
    main = _font_file(bold, italic)
    out: list[tuple[str, str]] = []
    for char in text:
        point = ord(char)
        file = main
        if point not in coverage.get(main, ()) and point in coverage.get(FALLBACK_FONT, ()):
            file = FALLBACK_FONT
        if out and out[-1][1] == file:
            out[-1] = (out[-1][0] + char, file)
        else:
            out.append((char, file))
    return [(chunk, _load(file, size)) for chunk, file in out]


@lru_cache(maxsize=16)
def icon_font(size: int) -> ImageFont.FreeTypeFont:
    """The Material Design Icons font."""
    return ImageFont.truetype(str(FONT_DIR / "MaterialDesignIcons.ttf"), max(6, size))


@lru_cache(maxsize=1)
def _codepoints() -> dict[str, int]:
    return json.loads((FONT_DIR / "mdi-codepoints.json").read_text())


def icon_char(name: str) -> str | None:
    """The character for an MDI icon name (with or without ``mdi:``), or None."""
    name = name.removeprefix("mdi:").strip().lower()
    codepoint = _codepoints().get(name)
    return chr(codepoint) if codepoint is not None else None


# ------------------------------------------------------------------ layout


@dataclass
class _Piece:
    text: str
    font: ImageFont.FreeTypeFont
    color: tuple[int, int, int]
    width: float
    space: bool
    glue: bool = False  # continues the previous word (no line break before it)


@dataclass
class _Row:
    pieces: list[_Piece]
    size: int
    indent: float
    gap_before: float

    @property
    def width(self) -> float:
        pieces = list(self.pieces)
        while pieces and pieces[-1].space:
            pieces.pop()
        return self.indent + sum(p.width for p in pieces)


def _pieces(runs: list[Run], size: int, default_color: str) -> list[_Piece]:
    """Words, spaces and icons as measured pieces."""
    pieces: list[_Piece] = []
    for run in runs:
        color = COLORS.get(run.color or default_color, COLORS["black"])
        if run.icon is not None:
            char = icon_char(run.icon)
            if char is None:
                continue
            font = icon_font(round(size * 1.1))
            pieces.append(_Piece(char, font, color, font.getlength(char), False))
            continue
        for token in re.findall(r"\s+|\S+", run.text):
            if token.isspace():
                font = text_font(size, run.bold, run.italic)
                pieces.append(_Piece(" ", font, color, font.getlength(" "), True))
                continue
            # A word may mix fonts (e.g. "7.5↓"); keep its parts together when wrapping.
            parts = segments(token, size, run.bold, run.italic)
            for index, (chunk, font) in enumerate(parts):
                pieces.append(
                    _Piece(chunk, font, color, font.getlength(chunk), False, glue=index > 0)
                )
    return pieces


def _wrap(pieces: list[_Piece], max_width: float) -> list[list[_Piece]]:
    rows: list[list[_Piece]] = [[]]
    width = 0.0
    for piece in pieces:
        if piece.space and not rows[-1]:
            continue
        if not piece.space and not piece.glue and rows[-1] and width + piece.width > max_width:
            while rows[-1] and rows[-1][-1].space:
                rows[-1].pop()
            rows.append([])
            width = 0.0
        rows[-1].append(piece)
        width += piece.width
    return rows


def layout(
    text: str, style: OverlayStyle, canvas_width: int, canvas_height: int
) -> tuple[list[_Row], float, float, float]:
    """Lay out markdown; returns rows, content width, content height and padding."""
    scale = min(canvas_width, canvas_height) / 480
    base = round(SIZES.get(style.size, SIZES["m"]) * scale)
    margin = style.margin * min(canvas_width, canvas_height)
    padding = round(base * 0.5) if style.backing == "box" else round(base * 0.15)
    if style.width:
        box_width = canvas_width * min(100, max(5, style.width)) / 100
    else:
        box_width = canvas_width - 2 * margin
    max_text = max(base * 2.0, box_width - 2 * padding)

    rows: list[_Row] = []
    pending_gap = 0.0
    for line in parse_markdown(text):
        if line.kind == "blank":
            pending_gap = base * 0.6
            continue
        size = round(base * HEADING_SCALE.get(line.level, 1.0)) if line.kind == "heading" else base
        runs = line.runs
        indent = 0.0
        if line.kind == "bullet":
            bullet_font = text_font(size, False, False)
            indent = bullet_font.getlength("•  ")
        pieces = _pieces(runs, size, style.text_color)
        wrapped = _wrap(pieces, max_text - indent)
        for index, row_pieces in enumerate(wrapped):
            gap = pending_gap if index == 0 else 0.0
            if index == 0 and line.kind == "bullet":
                color = row_pieces[0].color if row_pieces else COLORS[style.text_color]
                bullet = _Piece("•", text_font(size, False, False), color, 0.0, False)
                rows.append(_Row([bullet, *row_pieces], size, indent, gap))
            else:
                rows.append(_Row(row_pieces, size, indent, gap))
            pending_gap = 0.0
    if not rows:
        return [], 0.0, 0.0, padding
    content_width = box_width - 2 * padding if style.width else max(r.width for r in rows)
    content_height = sum(r.size * LINE_HEIGHT + r.gap_before for r in rows)
    return rows, content_width, content_height, padding


# ----------------------------------------------------------------- drawing


def _halo_color(text_color: str) -> tuple[int, int, int]:
    return COLORS["black"] if text_color in ("white", "yellow") else COLORS["white"]


def draw_overlay(
    layer: Image.Image, text: str, style: OverlayStyle
) -> tuple[int, int, int, int] | None:
    """Draw one text box onto ``layer``; returns its bounding box, or None if empty."""
    width, height = layer.size
    rows, content_w, content_h, padding = layout(text, style, width, height)
    if not rows:
        return None
    margin = style.margin * min(width, height)
    box_w = content_w + 2 * padding
    box_h = content_h + 2 * padding
    vertical, _, horizontal = style.anchor.partition("_")
    if style.anchor == "center":
        vertical = horizontal = "center"
    x = {"left": margin, "center": (width - box_w) / 2, "right": width - margin - box_w}.get(
        horizontal, margin
    )
    y = {"top": margin, "center": (height - box_h) / 2, "bottom": height - margin - box_h}.get(
        vertical, margin
    )
    draw = ImageDraw.Draw(layer)
    draw.fontmode = "1"
    box = (round(x), round(y), round(x + box_w), round(y + box_h))
    if style.backing == "box":
        radius = round(min(rows[0].size, 40) * 0.3)
        draw.rounded_rectangle(
            box, radius=radius, fill=COLORS.get(style.backing_color, COLORS["white"])
        )

    halo = style.backing == "halo"
    halo_color = _halo_color(style.text_color)
    halo_px = 1 if rows[0].size < 28 else 2
    cursor_y = y + padding
    for row in rows:
        cursor_y += row.gap_before
        line_h = row.size * LINE_HEIGHT
        baseline = cursor_y + row.size * 1.02
        row_w = row.width
        if style.align == "center":
            cursor_x = x + padding + (content_w - row_w) / 2
        elif style.align == "right":
            cursor_x = x + padding + content_w - row_w
        else:
            cursor_x = x + padding
        first = True
        for piece in row.pieces:
            if first and row.indent:
                # Bullet sits in the indent; the text starts after it.
                pos = (round(cursor_x), round(baseline))
                if halo:
                    _draw_halo(draw, pos, piece, halo_color, halo_px)
                draw.text(pos, piece.text, font=piece.font, fill=piece.color, anchor="ls")
                cursor_x += row.indent
                first = False
                continue
            first = False
            if not piece.space:
                pos = (round(cursor_x), round(baseline))
                if halo:
                    _draw_halo(draw, pos, piece, halo_color, halo_px)
                draw.text(pos, piece.text, font=piece.font, fill=piece.color, anchor="ls")
            cursor_x += piece.width
        cursor_y += line_h
    return box


def _draw_halo(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    piece: _Piece,
    color: tuple[int, int, int],
    px: int,
) -> None:
    for dx in range(-px, px + 1):
        for dy in range(-px, px + 1):
            if dx or dy:
                draw.text(
                    (pos[0] + dx, pos[1] + dy), piece.text, font=piece.font, fill=color, anchor="ls"
                )


def new_layer(width: int, height: int) -> Image.Image:
    """An empty overlay layer."""
    return Image.new("RGB", (width, height), SENTINEL)
