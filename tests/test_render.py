"""Rendering pipeline tests (no Home Assistant needed)."""

from __future__ import annotations

import io
import struct

import numpy as np
from PIL import Image
import pytest

from custom_components.paperlessoffline.render import (
    PlaceholderText,
    RenderOptions,
    canvas_for,
    render,
    render_placeholder,
)
from custom_components.paperlessoffline.render.bmp import encode_bmp4, encode_raw4
from custom_components.paperlessoffline.render.dither import (
    DITHER_METHODS,
    KERNELS,
    dither,
    error_diffusion_scalar,
    error_diffusion_wavefront,
)
from custom_components.paperlessoffline.render.palette import DEVICE_INDICES, PERCEIVED, PURE
from custom_components.paperlessoffline.settings import resolve

from .conftest import make_jpeg


@pytest.mark.parametrize("method", list(KERNELS))
def test_wavefront_matches_raster(method: str) -> None:
    rng = np.random.default_rng(42)
    img = rng.uniform(0, 255, (37, 53, 3)).astype(np.float32)
    fast = error_diffusion_wavefront(img, PERCEIVED, method)
    slow = error_diffusion_scalar(img, PERCEIVED, method)
    assert np.array_equal(fast, slow)


@pytest.mark.parametrize("method", DITHER_METHODS)
@pytest.mark.parametrize("serpentine", [False, True])
def test_dither_outputs_palette_positions(method: str, serpentine: bool) -> None:
    rng = np.random.default_rng(1)
    img = rng.uniform(0, 255, (16, 24, 3)).astype(np.float32)
    out = dither(img, PURE, method, serpentine)
    assert out.shape == (16, 24)
    assert out.max() < len(PURE)


def test_solid_primary_stays_solid() -> None:
    img = np.zeros((8, 8, 3), dtype=np.float32)
    img[..., 0] = 255  # pure red
    out = dither(img, PURE, "floyd_steinberg")
    assert (out == 3).all()


def test_dither_unknown_method() -> None:
    with pytest.raises(ValueError):
        dither(np.zeros((2, 2, 3)), PURE, "nope")


def test_bmp_header_and_layout() -> None:
    indices = np.full((4, 8), 6, dtype=np.uint8)
    indices[0, 0] = 0
    indices[3, 7] = 3
    data = encode_bmp4(indices)
    magic, size, _, _, offset = struct.unpack_from("<2sIHHI", data, 0)
    assert magic == b"BM"
    assert size == len(data)
    _, width, height, _, bpp = struct.unpack_from("<IiiHH", data, 14)
    assert (width, height, bpp) == (8, -4, 4)
    pixels = data[offset:]
    assert len(pixels) == 4 * 4
    assert pixels[0] == 0x06  # top-left black, then white
    assert pixels[-1] == 0x63  # bottom-right red
    # Viewers decode the colour table correctly.
    img = Image.open(io.BytesIO(data)).convert("RGB")
    assert img.getpixel((0, 0)) == (0, 0, 0)
    assert img.getpixel((7, 3)) == (255, 0, 0)


def test_bmp_rejects_unaligned_width() -> None:
    with pytest.raises(ValueError):
        encode_bmp4(np.zeros((2, 6), dtype=np.uint8))


def test_raw_starts_with_magic() -> None:
    data = encode_raw4(np.zeros((2, 8), dtype=np.uint8))
    assert data[:2] == b"\x66\x66"


@pytest.mark.parametrize(
    ("native", "mounting", "expected"),
    [
        ((800, 480), "landscape", (800, 480, 0)),
        ((800, 480), "landscape_flipped", (800, 480, 2)),
        ((800, 480), "portrait", (480, 800, 3)),
        ((800, 480), "portrait_flipped", (480, 800, 1)),
        ((1200, 1600), "portrait", (1200, 1600, 0)),
        ((1200, 1600), "landscape", (1600, 1200, 3)),
    ],
)
def test_canvas_for(native, mounting, expected) -> None:
    canvas = canvas_for(*native, mounting)
    assert (canvas.width, canvas.height, canvas.rot90) == expected


@pytest.mark.parametrize("mounting", ["landscape", "portrait"])
def test_render_produces_native_buffer(mounting: str) -> None:
    canvas = canvas_for(800, 480, mounting)
    result = render(make_jpeg(size=(640, 480)), RenderOptions(), canvas)
    bmp = Image.open(io.BytesIO(result.bmp))
    assert bmp.size == (800, 480)
    preview = Image.open(io.BytesIO(result.preview_png))
    assert preview.size == (canvas.width, canvas.height)
    _, offset = (
        struct.unpack_from("<2sI", result.bmp, 0)[0],
        struct.unpack_from("<I", result.bmp, 10)[0],
    )
    nibbles = set()
    for byte in result.bmp[offset:]:
        nibbles.update((byte >> 4, byte & 0x0F))
    assert nibbles <= set(DEVICE_INDICES.tolist())


def test_portrait_rotation_maps_top_edge() -> None:
    """Portrait on a 7" frame: the canvas top lands in the buffer's last column.

    Verified on hardware: held in portrait, the frame shows the buffer's top
    edge on the left, so the canvas is rotated clockwise into the buffer.
    """
    img = Image.new("RGB", (480, 800), (255, 255, 255))
    img.paste((255, 0, 0), (0, 0, 480, 40))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    canvas = canvas_for(800, 480, "portrait")
    result = render(buf.getvalue(), RenderOptions(dither="none", palette="pure"), canvas)
    native = Image.open(io.BytesIO(result.bmp)).convert("RGB")
    assert native.getpixel((795, 240)) == (255, 0, 0)
    assert native.getpixel((5, 240)) == (255, 255, 255)


def test_contain_letterboxes() -> None:
    canvas = canvas_for(800, 480, "landscape")
    wide = make_jpeg((0, 0, 0), size=(800, 100))
    result = render(wide, RenderOptions(fit="contain", dither="none", palette="pure"), canvas)
    native = Image.open(io.BytesIO(result.bmp)).convert("RGB")
    assert native.getpixel((400, 10)) == (255, 255, 255)
    assert native.getpixel((400, 240)) == (0, 0, 0)


def test_cover_focal_point_and_crop() -> None:
    img = Image.new("RGB", (1600, 480), (0, 0, 0))
    img.paste((255, 255, 255), (800, 0, 1600, 480))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    canvas = canvas_for(800, 480, "landscape")
    opts = RenderOptions(dither="none", palette="pure", focal_x=1.0)
    right = Image.open(io.BytesIO(render(buf.getvalue(), opts, canvas).bmp)).convert("RGB")
    assert right.getpixel((400, 240)) == (255, 255, 255)
    opts = RenderOptions(dither="none", palette="pure", crop=(0.0, 0.0, 0.5, 1.0))
    left = Image.open(io.BytesIO(render(buf.getvalue(), opts, canvas).bmp)).convert("RGB")
    assert left.getpixel((400, 240)) == (0, 0, 0)


def test_transparent_png_uses_background() -> None:
    img = Image.new("RGBA", (80, 48), (0, 0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    canvas = canvas_for(800, 480, "landscape")
    opts = RenderOptions(dither="none", palette="pure", background="black")
    native = Image.open(io.BytesIO(render(buf.getvalue(), opts, canvas).bmp)).convert("RGB")
    assert native.getpixel((10, 10)) == (0, 0, 0)


@pytest.mark.parametrize(
    ("native", "mounting"),
    [((800, 480), "portrait"), ((800, 480), "landscape"), ((1200, 1600), "portrait")],
)
def test_placeholder(native, mounting) -> None:
    text = PlaceholderText(
        "Großes Wohnzimmer über der Garage",
        "Noch keine Fotos",
        "Fotos in Home Assistant unter „Bilderrahmen“ hinzufügen.",
        "epd7-dc1ed5613e74",
    )
    canvas = canvas_for(*native, mounting)
    result = render_placeholder(text, canvas)
    assert Image.open(io.BytesIO(result.bmp)).size == native
    # Text is drawn without anti-aliasing: only exact palette colours appear.
    colours = set(Image.open(io.BytesIO(result.preview_png)).convert("RGB").getdata())
    assert colours <= {tuple(int(c) for c in row) for row in PERCEIVED}
    assert len(colours) == 6  # the illustration uses every colour


def test_placeholder_font_has_umlauts() -> None:
    from custom_components.paperlessoffline.render.placeholder import _font

    font = _font(40)
    # A missing glyph renders as the same "tofu" box for different characters.
    assert font.getmask("ü").getbbox() != font.getmask("ß").getbbox()
    assert font.getmask("„").getbbox() is not None


def test_resolve_layers() -> None:
    opts = resolve(
        {"dither": "atkinson", "saturation": 1.3, "palette": "pure"},
        {"dither": "sierra2", "rotation": 90},  # rotation is photo-only: ignored
        {"saturation": 1.1, "rotation": 180, "palette": "perceived", "crop": [0, 0, 1, 1]},
    )
    assert opts.dither == "sierra2"
    assert opts.saturation == 1.1
    assert opts.rotation == 180
    assert opts.palette == "pure"  # palette is not overridable per photo
    assert opts.crop == (0, 0, 1, 1)
    assert resolve(None, None, None) == RenderOptions()
