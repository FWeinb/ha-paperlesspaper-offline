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
from custom_components.paperlessoffline.render.pipeline import (
    fit_image,
    load_region,
    make_thumbnail,
    open_image,
)
from custom_components.paperlessoffline.settings import resolve

from .conftest import make_jpeg


@pytest.mark.parametrize("method", list(KERNELS))
@pytest.mark.parametrize("palette", [PERCEIVED, PURE], ids=["perceived", "pure"])
@pytest.mark.parametrize("seed", [42, 7, 1234])
def test_wavefront_matches_raster(method: str, palette, seed: int) -> None:
    rng = np.random.default_rng(seed)
    img = rng.uniform(0, 255, (37, 53, 3)).astype(np.float32)
    fast = error_diffusion_wavefront(img, palette, method)
    slow = error_diffusion_scalar(img, palette, method)
    assert np.array_equal(fast, slow)


@pytest.mark.parametrize("method", list(KERNELS))
@pytest.mark.parametrize("size", [(1, 9), (5, 4), (9, 1), (3, 3)])
def test_wavefront_matches_raster_on_tiny_images(method: str, size) -> None:
    img = np.random.default_rng(3).uniform(0, 255, (*size, 3)).astype(np.float32)
    fast = error_diffusion_wavefront(img, PERCEIVED, method)
    assert np.array_equal(fast, error_diffusion_scalar(img, PERCEIVED, method))


@pytest.mark.parametrize("method", list(KERNELS))
def test_wavefront_matches_raster_on_gradients(method: str) -> None:
    """Smooth areas put many pixels close to two colours (near ties)."""
    y, x = np.mgrid[0:60, 0:90].astype(np.float32)
    img = np.dstack([128 + 100 * np.sin(x / 9), 128 + 100 * np.cos(y / 13), 2 * (x + y)])
    img = img.astype(np.float32)
    fast = error_diffusion_wavefront(img, PERCEIVED, method)
    assert np.array_equal(fast, error_diffusion_scalar(img, PERCEIVED, method))


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


def _reference_fit(data: bytes, opts: RenderOptions, width: int, height: int) -> Image.Image:
    """The full-size decode, rotate, crop and fit used before shrink-first (render v1)."""
    from PIL import ImageOps

    background = (255, 255, 255)
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
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
        img = img.crop(box)
    iw, ih = img.size
    lanczos = Image.Resampling.LANCZOS
    if opts.fit == "stretch":
        return img.resize((width, height), lanczos, reducing_gap=3.0)
    if opts.fit == "contain":
        scale = min(width / iw, height / ih)
        nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
        canvas = Image.new("RGB", (width, height), background)
        canvas.paste(
            img.resize((nw, nh), lanczos, reducing_gap=3.0), ((width - nw) // 2, (height - nh) // 2)
        )
        return canvas
    scale = max(width / iw, height / ih)
    nw, nh = max(width, round(iw * scale)), max(height, round(ih * scale))
    resized = img.resize((nw, nh), lanczos, reducing_gap=3.0)
    left = round(min(max(opts.focal_x * nw - width / 2, 0), nw - width))
    top = round(min(max(opts.focal_y * nh - height / 2, 0), nh - height))
    return resized.crop((left, top, left + width, top + height))


def _photo(size: tuple[int, int], orientation: int = 1, fmt: str = "JPEG") -> bytes:
    """A photo-like test image: smooth gradients plus an asymmetric marker."""
    w, h = size
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    rgb = np.dstack(
        [
            128 + 100 * np.sin(x / (w / 7)),
            128 + 100 * np.cos(y / (h / 5)),
            255 * (x + 2 * y) / (w + 2 * h),
        ]
    ).astype(np.uint8)
    rgb[h // 10 : h // 4, w // 12 : w // 3] = (250, 250, 20)  # top left, wider than tall
    img = Image.fromarray(rgb)
    exif = Image.Exif()
    exif[0x0112] = orientation
    buf = io.BytesIO()
    img.save(buf, fmt, quality=95, exif=exif) if fmt == "JPEG" else img.save(buf, fmt)
    return buf.getvalue()


@pytest.mark.parametrize("orientation", [1, 2, 3, 5, 6, 8])
@pytest.mark.parametrize("rotation", [0, 90, 270])
@pytest.mark.parametrize(
    ("fit", "crop", "focal"),
    [
        ("cover", None, (0.5, 0.5)),
        ("cover", (0.1, 0.2, 0.5, 0.4), (0.9, 0.1)),
        ("contain", None, (0.5, 0.5)),
        ("contain", (0.3, 0.1, 0.2, 0.6), (0.5, 0.5)),
        ("stretch", (0.0, 0.5, 0.7, 0.5), (0.5, 0.5)),
    ],
)
def test_shrink_first_matches_full_decode(orientation, rotation, fit, crop, focal) -> None:
    """Shrinking while decoding gives the same picture as fitting the full image."""
    data = _photo((2400, 1600), orientation)
    opts = RenderOptions(fit=fit, crop=crop, focal_x=focal[0], focal_y=focal[1], rotation=rotation)
    new = np.asarray(fit_image(data, opts, 200, 120), dtype=np.float32)
    old = np.asarray(_reference_fit(data, opts, 200, 120), dtype=np.float32)
    assert new.shape == old.shape
    diff = np.abs(new - old)
    assert diff.mean() < 1.0
    assert np.percentile(diff, 99) < 4


def test_shrink_first_png_and_rotation_180() -> None:
    """Non-JPEG sources are shrunk by pixel averaging, with the same result."""
    data = _photo((1800, 1200), fmt="PNG")
    opts = RenderOptions(rotation=180, crop=(0.05, 0.05, 0.6, 0.6), focal_x=0.2)
    new = np.asarray(fit_image(data, opts, 160, 240), dtype=np.float32)
    old = np.asarray(_reference_fit(data, opts, 160, 240), dtype=np.float32)
    assert np.abs(new - old).mean() < 1.0


def test_load_region_shrinks_but_keeps_twice_the_output() -> None:
    img = open_image(_photo((2400, 1600), 6))
    region, box = load_region(img, 90, (0, 0, 2400, 1600), (200, 133), (255, 255, 255))
    assert region.size[0] < 2400
    assert box[2] - box[0] >= 400 and box[3] - box[1] >= 266


def test_thumbnail_uses_upright_orientation(tmp_path) -> None:
    source = tmp_path / "p.jpg"
    source.write_bytes(_photo((2400, 1600), 6))  # stored landscape, shown portrait
    thumb = Image.open(io.BytesIO(make_thumbnail(source, tmp_path / "t.jpg", 320, 90)))
    assert thumb.size == (320, 213)
    upright = _reference_fit(
        source.read_bytes(), RenderOptions(rotation=90, fit="stretch"), 320, 213
    )
    diff = np.abs(np.asarray(thumb, dtype=np.float32) - np.asarray(upright, dtype=np.float32))
    assert diff.mean() < 3
