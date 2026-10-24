"""Regenerate the README screenshots in docs/images/.

Starts a throwaway Home Assistant with this integration, adds three frames
with sample photos from picsum.photos and a text card, simulates a wake for
each, and takes dark-mode screenshots of the panel, the photo editor and the
global defaults with tools/screenshots.mjs.

Needs the dev venv (see DEVELOPMENT.md), `npm ci` in frontend/ and Google
Chrome (set CHROME to use another Chromium binary).

Usage::

    .venv/bin/python tools/screenshots.py [--keep]

``--keep`` leaves the temporary Home Assistant config in place and prints its
path, so you can start it again with ``hass -c <path>`` to look around
(log in as dev / devpass1234).
"""

# A sequential one-off script: blocking calls inside async code are fine here.
# ruff: noqa: ASYNC220, ASYNC221, ASYNC240

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).parents[1]
IMAGES = ROOT / "docs/images"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
USER, PASSWORD = "dev", "devpass1234"
FONT = ROOT / "custom_components/paperlessoffline/render/fonts/NotoSans-Regular.ttf"
SHOWN_URL = "homeassistant.local:8123/paperlessoffline"

# (name, client ID, battery mV, minutes since last wake, [(picsum ID, photo name)])
FRAMES = [
    (
        "Living room",
        "epd13-3c71bf4a92d0",
        3910,
        4,
        [
            (10, "Coastal forest"),
            (15, "Waterfall"),
            (16, "Rocky shore"),
            (17, "Garden path"),
            (29, "Snowy peaks"),
            (49, "Santorini"),
            (110, "Sunset meadow"),
            (128, "Alpine lake"),
        ],
    ),
    (
        "Kitchen",
        "epd7-a4cf12e85b61",
        4050,
        23,
        [
            (76, "Blue shed"),
            (82, "Cherry blossom"),
            (102, "Raspberries"),
            (112, "Golden grass"),
            (57, "City street"),
            (37, "Sea cliffs"),
        ],
    ),
    ("Hallway", "epd7-dc1ed5613e74", 3720, 47, [(28, "Green gorge"), (11, "Misty valley")]),
]
EDIT_FRAME, EDIT_PHOTO = "Living room", "Sunset meadow"

# Photos' own overlays: {frame: {photo name: [overlay]}}. One on and one off show
# both states of the library's overlay badge; the edited photo shows it in the preview.
CAPTION = {
    "name": "Caption",
    "template": "{{ photo.name }}",
    "anchor": "bottom_left",
    "size": "m",
}
PHOTO_OVERLAYS = {
    "Living room": {
        "Sunset meadow": [CAPTION],
        "Santorini": [{**CAPTION, "enabled": False}],
    },
}

# A card in the middle of the living room library: (frame, name, background, overlays).
CARD_POSITION = 4
CARD = (
    "Living room",
    "Good morning",
    "white",
    [
        {
            "name": "Greeting",
            "template": "# Good morning\n{{ date_local(now(), 'long') }}",
            "anchor": "top_left",
            "size": "l",
            "backing": "none",
        },
        {
            "name": "Today",
            "template": (
                "{blue}{{ weather_icon(states('weather.home')) }}{/blue} "
                "**{{ state_attr('weather.home', 'temperature') }} °C** outside\n"
                "{red}:mdi:home-thermometer:{/red} "
                "{{ states('sensor.living_room_temperature') }} °C inside\n"
                "{green}:mdi:recycle:{/green} Paper bin out tonight\n"
                "{blue}:mdi:calendar:{/blue} Dinner with Sam at 19:00"
            ),
            "anchor": "bottom_left",
            "size": "l",
            "backing": "none",
        },
    ],
)
# Entity states the card's templates read; set again after every start.
STATES = {
    "weather.home": ("partlycloudy", {"temperature": 17, "friendly_name": "Home"}),
    "sensor.living_room_temperature": ("21.5", {"unit_of_measurement": "°C"}),
}

CONFIG = """\
homeassistant:
  name: Home
  time_zone: Europe/Berlin
  internal_url: {base}
http:
  server_port: {port}
frontend:
config:
onboarding:
auth:
lovelace:
media_source:
logger:
  default: warning
repairs:
network:
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class HomeAssistant:
    """A throwaway Home Assistant process."""

    def __init__(self, config: Path, port: int) -> None:
        self.config = config
        self.base = f"http://127.0.0.1:{port}"
        self.proc: subprocess.Popen[bytes] | None = None

    async def start(self, session: aiohttp.ClientSession) -> None:
        log = (self.config / "hass.out").open("ab")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "homeassistant", "-c", str(self.config)],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        for _ in range(180):
            if self.proc.poll() is not None:
                sys.exit(f"Home Assistant exited; see {self.config / 'hass.out'}")
            try:
                async with session.get(self.base + "/manifest.json") as r:
                    if r.status == 200:
                        await asyncio.sleep(3)  # let integrations finish loading
                        return
            except aiohttp.ClientError:
                pass
            await asyncio.sleep(1)
        sys.exit("Home Assistant didn't come up within 3 minutes")

    def stop(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            return
        # Core on macOS may crash on the way out (exit 139) after saving its state.
        self.proc.send_signal(signal.SIGTERM)
        try:
            self.proc.wait(60)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None


async def ws_calls(session: aiohttp.ClientSession, base: str, token: str, *msgs: dict) -> list:
    """Run websocket commands in order; return their results."""
    results = []
    async with session.ws_connect(base + "/api/websocket") as ws:
        await ws.receive_json()
        await ws.send_json({"type": "auth", "access_token": token})
        await ws.receive_json()
        for i, msg in enumerate(msgs, 1):
            await ws.send_json({"id": i, **msg})
            while (r := await ws.receive_json()).get("id") != i:
                pass
            results.append(r.get("result"))
    return results


async def tidy_up(session: aiohttp.ClientSession, ha: HomeAssistant, token: str) -> None:
    """Accept the HTTP settings and hide unrelated notices, so nothing covers the panel."""
    _, notes, issues = await ws_calls(
        session,
        ha.base,
        token,
        {"type": "http/config/promote"},
        {"type": "persistent_notification/get"},
        {"type": "repairs/list_issues"},
    )
    await ws_calls(
        session,
        ha.base,
        token,
        *[
            {"type": "persistent_notification/dismiss", "notification_id": n["notification_id"]}
            for n in notes or []
        ],
        *[
            {
                "type": "repairs/ignore_issue",
                "domain": i["domain"],
                "issue_id": i["issue_id"],
                "ignore": True,
            }
            for i in (issues or {}).get("issues", [])
            if not i["ignored"]
        ],
    )


async def onboard(session: aiohttp.ClientSession, base: str) -> dict:
    client_id = base + "/"
    async with session.post(
        base + "/api/onboarding/users",
        json={
            "client_id": client_id,
            "name": "Alex",
            "username": USER,
            "password": PASSWORD,
            "language": "en",
        },
    ) as r:
        code = (await r.json())["auth_code"]
    async with session.post(
        base + "/auth/token",
        data={"grant_type": "authorization_code", "code": code, "client_id": client_id},
    ) as r:
        tokens = await r.json()
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    for step, body in (
        ("core_config", {}),
        ("analytics", {}),
        ("integration", {"client_id": client_id, "redirect_uri": client_id}),
    ):
        async with session.post(f"{base}/api/onboarding/{step}", json=body, headers=auth) as r:
            r.raise_for_status()
    return {**tokens, "hassUrl": base, "clientId": client_id, "expires": 0}


async def set_states(session: aiohttp.ClientSession, base: str, token: str) -> None:
    auth = {"Authorization": f"Bearer {token}"}
    for entity_id, (state, attributes) in STATES.items():
        async with session.post(
            f"{base}/api/states/{entity_id}",
            json={"state": state, "attributes": attributes},
            headers=auth,
        ) as r:
            r.raise_for_status()


async def call_service(
    session: aiohttp.ClientSession, base: str, token: str, service: str, **data
) -> dict:
    """Call a paperlessoffline action; return its response (empty for actions without one)."""
    respond = service in ("add_card", "add_overlay", "list_photos")
    async with session.post(
        f"{base}/api/services/paperlessoffline/{service}" + ("?return_response" if respond else ""),
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    ) as r:
        r.raise_for_status()
        return (await r.json()).get("service_response") or {} if respond else {}


async def add_card(session: aiohttp.ClientSession, base: str, token: str, entry_id: str) -> None:
    """Add CARD at CARD_POSITION in the frame's order; the wake still shows the first photo."""
    _, name, background, overlays = CARD
    card = await call_service(
        session, base, token, "add_card", config_entry_id=entry_id, name=name,
        background=background,
    )  # fmt: skip
    for overlay in overlays:
        await call_service(
            session, base, token, "add_overlay",
            config_entry_id=entry_id, photo_id=card["photo_id"], **overlay,
        )  # fmt: skip
    await call_service(
        session, base, token, "move_photo",
        config_entry_id=entry_id, photo_id=card["photo_id"], position=CARD_POSITION,
    )  # fmt: skip


async def add_photo_overlays(
    session: aiohttp.ClientSession, base: str, token: str, entry_id: str, frame: str
) -> None:
    listed = await call_service(session, base, token, "list_photos", config_entry_id=entry_id)
    ids = {p["name"]: p["photo_id"] for p in listed["photos"]}
    for photo, overlays in PHOTO_OVERLAYS.get(frame, {}).items():
        for overlay in overlays:
            await call_service(
                session, base, token, "add_overlay",
                config_entry_id=entry_id, photo_id=ids[photo], **overlay,
            )  # fmt: skip


async def fetch_photos(session: aiohttp.ClientSession, cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    for _, _, _, _, photos in FRAMES:
        for pid, _ in photos:
            path = cache / f"{pid}.jpg"
            if not path.exists():
                async with session.get(f"https://picsum.photos/id/{pid}/1600/1067") as r:
                    r.raise_for_status()
                    path.write_bytes(await r.read())


async def add_frames(
    session: aiohttp.ClientSession, base: str, token: str, cache: Path
) -> dict[str, dict]:
    """Add the frames, upload their photos and simulate a wake; return entries by name."""
    auth = {"Authorization": f"Bearer {token}"}
    flows = base + "/api/config/config_entries/flow"
    entries = {}
    for name, client_id, millivolts, _, photos in FRAMES:
        async with session.post(flows, json={"handler": "paperlessoffline"}, headers=auth) as r:
            flow = await r.json()
        async with session.post(
            f"{flows}/{flow['flow_id']}",
            json={"client_id": client_id, "name": name, "url_host": "auto"},
            headers=auth,
        ) as r:
            urls = (await r.json())["description_placeholders"]
        async with session.post(f"{flows}/{flow['flow_id']}", json={}, headers=auth) as r:
            entry_id = (await r.json())["result"]["entry_id"]

        # Built by hand: aiohttp's FormData percent-encodes the filenames (photo names).
        boundary = "----paperlessoffline"
        body = (
            b"".join(
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{title}.jpg"\r\n'
                f"Content-Type: image/jpeg\r\n\r\n".encode()
                + (cache / f"{pid}.jpg").read_bytes()
                + b"\r\n"
                for pid, title in photos
            )
            + f"--{boundary}--\r\n".encode()
        )
        async with session.post(
            f"{base}/api/paperlessoffline/upload/{entry_id}",
            data=body,
            headers={**auth, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        ) as r:
            r.raise_for_status()
        if name == CARD[0]:
            await add_card(session, base, token, entry_id)
        await add_photo_overlays(session, base, token, entry_id, name)

        # A wake as the firmware does it: settings first, then the image with telemetry.
        async with session.get(urls["settings_url"]) as r:
            r.raise_for_status()
        telemetry = {
            "voltage": millivolts,
            "usb": 0,
            "charging": 0,
            "orientation": 0,
            "fw": "1.4.2",
        }
        async with session.get(urls["image_url"], params=telemetry) as r:
            r.raise_for_status()
            await r.read()
        entries[name] = {"entry_id": entry_id}
        print(f"  {name}: {len(photos)} photos" + (", 1 card" if name == CARD[0] else ""))
    return entries


def backdate(config: Path, entries: dict[str, dict]) -> None:
    """Spread the frames' last wakes, so the panel doesn't say "seconds ago" for all."""
    now = time.time()
    for name, _, _, minutes, _ in FRAMES:
        path = config / ".storage" / f"paperlessoffline.{entries[name]['entry_id']}"
        data = json.loads(path.read_text())
        state, when = data["data"]["state"], now - minutes * 60
        for key in ("last_request", "last_wake", "last_settings_fetch"):
            state[key] = when
        state["served_lm"] = int(when)
        for key in state.get("wake_read_at", {}):
            state["wake_read_at"][key] = when
        path.write_text(json.dumps(data, indent=2))


def browser_chrome(shot: Image.Image, url: str, scale: int = 2) -> Image.Image:
    """Wrap a screenshot in a stylised dark browser window with a drop shadow."""
    bar, radius, margin = 52 * scale, 12 * scale, 48 * scale
    width, height = shot.width, shot.height + bar

    window = Image.new("RGBA", (width, height), "#2a2a2d")
    window.paste(shot.convert("RGBA"), (0, bar))
    draw = ImageDraw.Draw(window)
    draw.line([(0, bar - 1), (width, bar - 1)], fill="#3c3c40", width=scale)
    for i, colour in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        cx, cy, r = (22 + 20 * i) * scale, bar // 2, 6 * scale
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=colour)

    pill_w, pill_h = width * 0.42, 30 * scale
    left, top = (width - pill_w) / 2, (bar - pill_h) / 2
    draw.rounded_rectangle(
        (left, top, left + pill_w, top + pill_h), radius=pill_h / 2, fill="#1b1b1d"
    )
    font = ImageFont.truetype(str(FONT), 13 * scale)
    host, _, path = url.partition("/")
    text_w = draw.textlength(host + "/" + path, font=font)
    x, y = (width - text_w) / 2, bar / 2
    draw.text((x, y), host, font=font, fill="#e6e6e6", anchor="lm")
    draw.text(
        (x + draw.textlength(host, font=font), y),
        "/" + path,
        font=font,
        fill="#8e8e93",
        anchor="lm",
    )

    mask = Image.new("L", window.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    outline = ImageDraw.Draw(window)
    outline.rounded_rectangle(
        (0, 0, width - 1, height - 1), radius=radius, outline="#4a4a4f", width=scale
    )

    canvas = Image.new("RGBA", (width + 2 * margin, height + 2 * margin), (0, 0, 0, 0))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (margin, margin + 8 * scale, margin + width, margin + height + 8 * scale),
        radius=radius,
        fill=(0, 0, 0, 110),
    )
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(16 * scale)))
    canvas.paste(window, (margin, margin), mask)
    return canvas


def to_webp(image: Image.Image, out: Path, width: int) -> None:
    image = image.resize(
        (width, round(image.height * width / image.width)), Image.Resampling.LANCZOS
    )
    buf = io.BytesIO()
    image.save(buf, "WEBP", quality=85, method=6)
    out.write_bytes(buf.getvalue())
    print(f"  {out.relative_to(ROOT)} ({len(buf.getvalue()) // 1024} KB)")


async def main(keep: bool) -> None:
    if not (ROOT / "frontend/node_modules").is_dir():
        sys.exit("Run `npm ci` in frontend/ first")
    print("Building the frontend")
    subprocess.run(["npm", "run", "build"], cwd=ROOT / "frontend", check=True, capture_output=True)

    work = Path(tempfile.mkdtemp(prefix="paperlessoffline-shots-"))
    config = work / "config"
    (config / "custom_components").mkdir(parents=True)
    (config / "custom_components/paperlessoffline").symlink_to(
        ROOT / "custom_components/paperlessoffline"
    )
    port = free_port()
    ha = HomeAssistant(config, port)
    (config / "configuration.yaml").write_text(CONFIG.format(base=ha.base, port=port))

    try:
        async with aiohttp.ClientSession() as session:
            print("Downloading sample photos")
            await fetch_photos(session, work / "photos")
            print(f"Starting Home Assistant on {ha.base}")
            await ha.start(session)
            tokens = await onboard(session, ha.base)
            await set_states(session, ha.base, tokens["access_token"])
            print("Adding frames")
            entries = await add_frames(session, ha.base, tokens["access_token"], work / "photos")

            print("Restarting with spread-out wake times")
            ha.stop()
            backdate(config, entries)
            await ha.start(session)
            await set_states(session, ha.base, tokens["access_token"])
            await tidy_up(session, ha, tokens["access_token"])

            print("Taking screenshots")
            living = entries[EDIT_FRAME]["entry_id"]
            shots = [
                {"path": f"/paperlessoffline/{living}", "out": str(work / "panel.png")},
                {
                    "path": f"/paperlessoffline/{living}",
                    "out": str(work / "editor.png"),
                    "edit": EDIT_PHOTO,
                },
                {"path": "/paperlessoffline/global", "out": str(work / "global.png")},
            ]
            job = {"base": ha.base, "tokens": json.dumps(tokens), "chrome": CHROME, "shots": shots}
            subprocess.run(
                ["node", str(ROOT / "tools/screenshots.mjs"), json.dumps(job)], check=True
            )
    finally:
        ha.stop()

    IMAGES.mkdir(parents=True, exist_ok=True)
    panel = browser_chrome(Image.open(work / "panel.png"), SHOWN_URL)
    to_webp(panel, IMAGES / "panel-dark.webp", 2160)
    to_webp(Image.open(work / "editor.png").convert("RGB"), IMAGES / "editor-dark.webp", 1440)
    to_webp(
        Image.open(work / "global.png").convert("RGB"), IMAGES / "global-defaults-dark.webp", 1440
    )

    if keep:
        print(f"Kept {config}")
    else:
        shutil.rmtree(work)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--keep", action="store_true", help="keep the temporary Home Assistant config"
    )
    asyncio.run(main(parser.parse_args().keep))
