"""Hardware check server (milestone M0).

Serves labelled test patterns to a real frame so we can confirm on the glass:

* which image encodings the firmware accepts (4-bit BMP with negative or
  positive height, raw 4bpp, JPEG for comparison),
* how the native buffer maps onto the physical panel (which edge is "top"),
* how the settings JSON fetch behaves (If-Modified-Since / 304, ordering).

Every wake (requests more than 60 s apart) advances to the next variant. Each
pattern prints its variant name, so note what the frame shows for each one.

Usage::

    .venv/bin/python tools/hw_spike.py --panel 13 --timeout 120

``--panel`` must match the frame: the ID on its screen / serial log starts with
``epd7-`` (7.3", 800x480) or ``epd13-`` (13.3", 1200x1600). A wrong panel size
sends a buffer the firmware misreads.

Then, in the official web UI (Bluetooth), set the frame's Settings URL to the
printed ``/settings.json`` URL and its Image URL to the printed ``/image``
URL. Press the frame's button twice to force a download at any time.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import io
import json
from pathlib import Path
import socket
import struct
import sys
import time

from aiohttp import web
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "paperlessoffline"))

from render.bmp import encode_bmp4, encode_raw4
from render.dither import nearest
from render.palette import DEVICE_INDICES, PURE
from render.pipeline import MOUNTINGS, canvas_for

PANELS = {"7": (800, 480), "13": (1200, 1600)}
VARIANTS = ("bmp_topdown", "bmp_positive_height", "raw", "jpeg")
SWATCHES = ["black", "blue", "green", "red", "yellow", "white"]


def pattern(
    width: int, height: int, variant: str, counter: int, mount: str | None = None
) -> Image.Image:
    """Draw an orientation/palette test pattern in native buffer coordinates."""
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    scale = min(width, height) / 480
    big = ImageFont.load_default(size=round(44 * scale))
    small = ImageFont.load_default(size=round(24 * scale))
    border = max(4, round(6 * scale))
    draw.rectangle((0, 0, width - 1, height - 1), outline=(0, 0, 0), width=border)
    # Red bar along the native top edge, blue along the native left edge.
    draw.rectangle((0, 0, width, round(18 * scale)), fill=(255, 0, 0))
    draw.rectangle((0, 0, round(18 * scale), height), fill=(0, 0, 255))
    pad = round(30 * scale)
    draw.text((pad, pad), "TL", fill=(0, 0, 0), font=big)
    draw.text((width - pad, pad), "TR", fill=(0, 0, 0), font=big, anchor="ra")
    draw.text((pad, height - pad), "BL", fill=(0, 0, 0), font=big, anchor="ld")
    draw.text((width - pad, height - pad), "BR", fill=(0, 0, 0), font=big, anchor="rd")
    cx, cy = width // 2, height // 2
    arrow = round(50 * scale)
    draw.polygon(
        [(cx, cy - 2 * arrow), (cx - arrow, cy - arrow), (cx + arrow, cy - arrow)],
        fill=(0, 0, 0),
    )
    draw.rectangle((cx - arrow // 3, cy - arrow, cx + arrow // 3, cy), fill=(0, 0, 0))
    draw.text(
        (cx, cy + round(12 * scale)), f"#{counter} {variant}", fill=(0, 0, 0), font=big, anchor="ma"
    )
    draw.text(
        (cx, cy + round(64 * scale)),
        f"{mount}: arrow must point UP" if mount else "UP = native top (red bar). Left = blue bar.",
        fill=(0, 0, 0),
        font=small,
        anchor="ma",
    )
    sw = (width - 7 * pad) // 6
    top = height - pad - round(95 * scale)
    for i, name in enumerate(SWATCHES):
        color = tuple(int(c) for c in PURE[i])
        x0 = round(3.5 * pad) + i * sw
        draw.rectangle(
            (x0, top, x0 + sw - 6, top + round(40 * scale)), fill=color, outline=(0, 0, 0)
        )
        draw.text(
            (x0, top + round(44 * scale)),
            f"{name}={DEVICE_INDICES[i]}" if sw >= 110 else str(DEVICE_INDICES[i]),
            fill=(0, 0, 0),
            font=small,
        )
    return img


def encode(img: Image.Image, variant: str, rot90: int = 0) -> tuple[bytes, str]:
    """Encode the pattern in the requested variant, rotated into the native buffer."""
    if rot90:
        img = Image.fromarray(np.ascontiguousarray(np.rot90(np.asarray(img), rot90)))
    if variant == "jpeg":
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=92)
        return buf.getvalue(), "image/jpeg"
    nibbles = DEVICE_INDICES[nearest(np.asarray(img, dtype=np.float32), PURE)]
    if variant == "raw":
        return encode_raw4(nibbles), "application/octet-stream"
    data = bytearray(encode_bmp4(nibbles))
    if variant == "bmp_positive_height":
        # Same top-down pixel rows, but a positive height in the header.
        struct.pack_into("<i", data, 22, nibbles.shape[0])
    return bytes(data), "image/bmp"


def http_date(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")


class Spike:
    def __init__(
        self, panel: str, timeout: int, variants: list[str], mount: str | None = None
    ) -> None:
        self.width, self.height = PANELS[panel]
        self.mount = mount
        self.timeout = timeout
        self.variants = variants
        self.index = -1
        self.last_request = 0.0
        self.seen_settings = False
        self.settings_lm = time.time()
        self.image_lm = 0.0
        self.start = time.time()

    def render(self, variant: str, counter: int) -> tuple[bytes, str]:
        """Pattern for the native buffer, or drawn upright for a mounting."""
        if not self.mount:
            return encode(pattern(self.width, self.height, variant, counter), variant)
        canvas = canvas_for(self.width, self.height, self.mount)
        img = pattern(canvas.width, canvas.height, variant, counter, self.mount)
        return encode(img, variant, canvas.rot90)

    def log(self, request: web.Request, note: str) -> None:
        elapsed = time.time() - self.start
        headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
        print(f"[{elapsed:8.1f}s] {request.method} {request.path_qs} -> {note}")
        print(f"            headers: {json.dumps(headers)}")

    def maybe_wake(self, kind: str) -> bool:
        # Settings are fetched exactly once per wake, before the image. Image
        # requests (redirect probe + download + retries) only count as a wake
        # for frames that never fetched settings.
        now = time.time()
        if kind == "settings":
            self.seen_settings = True
            wake = True
        else:
            wake = not self.seen_settings and now - self.last_request > 60
        self.last_request = now
        if wake:
            self.index = (self.index + 1) % len(self.variants)
            self.image_lm = max(now, self.image_lm + 1)
        return wake

    async def settings(self, request: web.Request) -> web.Response:
        wake = self.maybe_wake("settings")
        lm = http_date(self.settings_lm)
        if request.headers.get("If-Modified-Since") == lm:
            self.log(request, f"304 (wake={wake})")
            return web.Response(status=304, headers={"Last-Modified": lm})
        image_url = str(request.url.with_path("/image").with_query(None))
        body = {"timeout": self.timeout, "downloadUrl": image_url}
        self.log(request, f"200 {body} (wake={wake})")
        return web.json_response(body, headers={"Last-Modified": lm})

    async def image(self, request: web.Request) -> web.Response:
        wake = self.maybe_wake("image")
        variant = request.query.get("v") or self.variants[self.index]
        data, ctype = self.render(variant, self.index + 1)
        self.log(request, f"200 {variant} {len(data)} bytes (wake={wake})")
        return web.Response(
            body=data, content_type=ctype, headers={"Last-Modified": http_date(self.image_lm)}
        )


def local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("10.255.255.255", 1))
            return str(sock.getsockname()[0])
        except OSError:
            return "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--panel",
        choices=PANELS,
        required=True,
        help="7 for epd7-... frames, 13 for epd13-... frames",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=int, default=120, help="sleep seconds sent to the frame")
    parser.add_argument("--variants", default=",".join(VARIANTS), help=f"comma list of {VARIANTS}")
    parser.add_argument(
        "--mount",
        choices=MOUNTINGS,
        help="draw the pattern upright for this mounting, using the integration's rotation",
    )
    parser.add_argument("--dump", metavar="DIR", help="write every variant to DIR and exit")
    args = parser.parse_args()
    variants = [v for v in args.variants.split(",") if v]
    spike = Spike(args.panel, args.timeout, variants, args.mount)

    if args.dump:
        out = Path(args.dump)
        out.mkdir(parents=True, exist_ok=True)
        for i, variant in enumerate(variants, 1):
            data, ctype = spike.render(variant, i)
            ext = {"image/jpeg": "jpg", "image/bmp": "bmp"}.get(ctype, "bin")
            (out / f"{i}_{variant}.{ext}").write_bytes(data)
        print(f"Wrote {len(variants)} files to {out}")
        return

    app = web.Application()
    app.router.add_get("/settings.json", spike.settings)
    app.router.add_get("/image", spike.image)
    base = f"http://{local_ip()}:{args.port}"
    print(f"Settings URL: {base}/settings.json")
    print(f"Image URL:    {base}/image")
    print(f"Panel {args.panel}: {spike.width}x{spike.height}; variants per wake: {variants}")
    print(f"Expected BMP size: {118 + spike.width * spike.height // 2} bytes")
    web.run_app(app, port=args.port, print=None)


if __name__ == "__main__":
    main()
