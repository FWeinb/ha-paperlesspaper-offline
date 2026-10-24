"""Run a local Home Assistant with this integration, for trying it end to end.

The instance lives in .ha-dev/ (gitignored). Its config links
custom_components/paperlessoffline to the checkout, so it runs the code you
are editing. On the first run the instance is created: a user (dev /
devpass1234), onboarding marked as done, and a frame "Kitchen" with three
sample photos (no real frame needed). Later runs reuse it.

Home Assistant runs in the background: ``start`` returns once it is up, and
its output goes to .ha-dev/hass.log. Restart it after changing Python code;
after ``npm run build`` in frontend/, reloading the page is enough.

Usage::

    .venv/bin/python tools/ha_dev.py [start|stop|restart]
"""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw

ROOT = Path(__file__).parents[1]
CONFIG_DIR = ROOT / ".ha-dev/config"
PORT = 8124
BASE = f"http://127.0.0.1:{PORT}"
USER, PASSWORD = "dev", "devpass1234"
FRAME = {"client_id": "epd7-dc1ed5613e74", "name": "Kitchen"}
PHOTOS = ["Lake morning", "Mountain hike", "Golden field"]

CONFIG = f"""\
homeassistant:
  name: Dev
  time_zone: Europe/Berlin
  internal_url: {BASE}
  allowlist_external_dirs:
    - /tmp
http:
  server_port: {PORT}
frontend:
config:
onboarding:
auth:
lovelace:
media_source:
logger:
  default: warning
  logs:
    custom_components.paperlessoffline: debug
bluetooth:
repairs:
network:
"""
ONBOARDING = {
    "version": 4,
    "minor_version": 1,
    "key": "onboarding",
    "data": {"done": ["user", "core_config", "analytics", "integration"]},
}


def create() -> None:
    """Write the config, add the user and skip the onboarding wizard."""
    (CONFIG_DIR / "custom_components").mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / ".storage").mkdir(exist_ok=True)
    link = CONFIG_DIR / "custom_components/paperlessoffline"
    if not link.is_symlink():
        link.symlink_to(ROOT / "custom_components/paperlessoffline")
    subprocess.run(
        [sys.executable, "-m", "homeassistant", "--script", "auth", "--config", str(CONFIG_DIR),
         "add", USER, PASSWORD],
        check=True,
    )  # fmt: skip
    (CONFIG_DIR / ".storage/onboarding").write_text(json.dumps(ONBOARDING))
    (CONFIG_DIR / "configuration.yaml").write_text(CONFIG)


def request(method: str, path: str, data=None, *, token=None, form=False, raw=None, ctype=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    body = None
    if raw is not None:
        body, headers["Content-Type"] = raw, ctype
    elif form:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"null")


def is_up() -> bool:
    try:
        urllib.request.urlopen(BASE + "/manifest.json")
    except (urllib.error.URLError, ConnectionError):
        return False
    return True


def wait_until_up(proc: subprocess.Popen[bytes]) -> None:
    for _ in range(180):
        if proc.poll() is not None:
            sys.exit(f"Home Assistant exited; see {CONFIG_DIR.parent / 'hass.log'}")
        if is_up():
            time.sleep(3)  # let integrations finish loading
            return
        time.sleep(1)
    sys.exit("Home Assistant didn't come up within 3 minutes")


def login() -> str:
    client_id = BASE + "/"
    flow = request(
        "POST", "/auth/login_flow",
        {"client_id": client_id, "handler": ["homeassistant", None], "redirect_uri": client_id},
    )  # fmt: skip
    result = request(
        "POST", f"/auth/login_flow/{flow['flow_id']}",
        {"username": USER, "password": PASSWORD, "client_id": client_id},
    )  # fmt: skip
    tokens = request(
        "POST", "/auth/token",
        {"grant_type": "authorization_code", "code": result["result"], "client_id": client_id},
        form=True,
    )  # fmt: skip
    return tokens["access_token"]


def sample_photo(seed: int) -> bytes:
    img = Image.new("RGB", (1600, 1067))
    d = ImageDraw.Draw(img)
    for y in range(1067):
        t = y / 1067
        d.line(
            [(0, y), (1600, y)],
            fill=(
                int(80 + 150 * t * (seed % 3 == 0)),
                int(120 + 100 * (1 - t)),
                int(200 - 120 * t + 30 * seed),
            ),
        )
    d.ellipse((300 + seed * 150, 200, 600 + seed * 150, 500), fill=(250, 220 - seed * 30, 40))
    d.polygon(
        [(0, 1067), (500, 600), (900, 900), (1300, 550), (1600, 800), (1600, 1067)],
        fill=(30 + seed * 20, 90, 40),
    )
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def seed() -> None:
    """Add a frame through the config flow and upload sample photos."""
    token = login()
    flow = request(
        "POST", "/api/config/config_entries/flow", {"handler": "paperlessoffline"}, token=token
    )
    flow_url = f"/api/config/config_entries/flow/{flow['flow_id']}"
    request("POST", flow_url, FRAME, token=token)
    flow = request("POST", flow_url, {}, token=token)
    entry_id = flow["result"]["entry_id"]
    boundary = "----devboundary"
    body = (
        b"".join(
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}.jpg"\r\n'
            "Content-Type: image/jpeg\r\n\r\n".encode()
            + sample_photo(i)
            + b"\r\n"
            for i, name in enumerate(PHOTOS)
        )
        + f"--{boundary}--\r\n".encode()
    )
    request(
        "POST", f"/api/paperlessoffline/upload/{entry_id}", token=token, raw=body,
        ctype=f"multipart/form-data; boundary={boundary}",
    )  # fmt: skip
    print(f"Added frame {FRAME['name']} with {len(PHOTOS)} photos", flush=True)


def running_pid() -> int | None:
    """PID of the instance started by this script, if it still runs."""
    try:
        pid = int((CONFIG_DIR.parent / "hass.pid").read_text())
        os.kill(pid, 0)
    except (OSError, ValueError):
        return None
    return pid


def start() -> None:
    if running_pid() or is_up():
        sys.exit(f"Already running at {BASE}")
    if not (ROOT / "custom_components/paperlessoffline/frontend").is_dir():
        print(
            "No frontend build: the panel and card are missing (run `npm run build` in frontend/)"
        )
    fresh = not (CONFIG_DIR / "configuration.yaml").exists()
    if fresh:
        print(f"Creating {CONFIG_DIR}", flush=True)
        create()
    with (CONFIG_DIR.parent / "hass.log").open("ab") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "homeassistant", "--config", str(CONFIG_DIR), "--skip-pip"],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # keeps running after this script exits
        )
    (CONFIG_DIR.parent / "hass.pid").write_text(str(proc.pid))
    print("Starting Home Assistant", flush=True)
    wait_until_up(proc)
    if fresh:
        seed()
    print(f"Up at {BASE} (log in as {USER} / {PASSWORD})")


def stop() -> None:
    if (pid := running_pid()) is None:
        print("Not running")
        return
    os.kill(pid, signal.SIGTERM)
    for _ in range(60):
        if running_pid() is None:
            break
        time.sleep(1)
    else:
        os.kill(pid, signal.SIGKILL)
    (CONFIG_DIR.parent / "hass.pid").unlink(missing_ok=True)
    print("Stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", default="start", choices=["start", "stop", "restart"])
    command = parser.parse_args().command
    if command in ("stop", "restart"):
        stop()
    if command in ("start", "restart"):
        start()
