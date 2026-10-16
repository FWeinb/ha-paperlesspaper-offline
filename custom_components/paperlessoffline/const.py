"""Constants for the paperlessoffline integration."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final

DOMAIN: Final = "paperlessoffline"
STORAGE_VERSION: Final = 1
STORAGE_DIR: Final = DOMAIN

CLIENT_ID_RE: Final = re.compile(r"^(epd7|epd13)-([0-9a-f]{12})$")

# Config entry data
CONF_CLIENT_ID: Final = "client_id"
CONF_TOKEN: Final = "token"
CONF_PANEL: Final = "panel"

# Config entry options (device / slideshow)
CONF_INTERVAL: Final = "interval"  # seconds
CONF_QUIET_ENABLED: Final = "quiet_enabled"
CONF_QUIET_START: Final = "quiet_start"  # "HH:MM:SS"
CONF_QUIET_END: Final = "quiet_end"
CONF_QUIET_SUPPRESS_MOTION: Final = "quiet_suppress_motion"
CONF_MOUNTING: Final = "mounting"
CONF_ORDER: Final = "order"
CONF_MOTION_WAKEUP: Final = "motion_wakeup"
CONF_AUTO_ROTATION: Final = "auto_rotation"
CONF_CHARGER_MODE: Final = "charger_mode"
CONF_TELEMETRY: Final = "telemetry"
CONF_AUTH_ENABLED: Final = "auth_enabled"
CONF_AUTH_USER: Final = "auth_user"
CONF_AUTH_PASSWORD: Final = "auth_password"
CONF_RENDER_DEFAULTS: Final = "render_defaults"
CONF_BLE_AUTO: Final = "ble_auto"
CONF_URL_HOST: Final = "url_host"  # "auto" or an IP/hostname for the frame's URLs

# Config entry data: what the frame was last configured with (for repairs)
CONF_PROVISIONED_TOKEN: Final = "provisioned_token"
CONF_PROVISIONED_BASE: Final = "provisioned_base_url"

ORDER_SEQUENTIAL: Final = "sequential"
ORDER_SHUFFLE: Final = "shuffle"
ORDERS: Final = (ORDER_SEQUENTIAL, ORDER_SHUFFLE)

DEFAULT_INTERVAL: Final = 3600
MIN_INTERVAL: Final = 60
MAX_INTERVAL: Final = 7 * 24 * 3600
DEFAULT_QUIET_START: Final = "22:00:00"
DEFAULT_QUIET_END: Final = "07:00:00"

WAKE_DEBOUNCE_SECONDS: Final = 60
# Don't reconnect over BLE more often than this while a frame stays in setup mode.
BLE_COOLDOWN_SECONDS: Final = 120
# A frame is overdue after missing this many expected wakes.
OFFLINE_MISSED_WAKES: Final = 3
OFFLINE_GRACE_SECONDS: Final = 300
# Frames that fetched settings within 2x their sleep + this are "settings frames".
SETTINGS_GRACE_SECONDS: Final = 300
MAX_UPLOAD_BYTES: Final = 50 * 1024 * 1024
# Decoding costs memory by pixel count (3 bytes each), not file size.
MAX_IMAGE_PIXELS: Final = 100_000_000
ALLOWED_FORMATS: Final = frozenset({"JPEG", "PNG", "WEBP", "HEIF", "MPO"})

# Render settings and which level may set them
RENDER_KEYS_SHARED: Final = (
    "dither",
    "serpentine",
    "fit",
    "brightness",
    "contrast",
    "saturation",
    "background",
)
RENDER_KEYS_FRAME_ONLY: Final = ("palette",)
RENDER_KEYS_PHOTO_ONLY: Final = ("rotation", "focal_x", "focal_y", "crop")
PALETTES: Final = ("perceived", "pure")
ROTATIONS: Final = (0, 90, 180, 270)

GLOBAL_RENDER_DEFAULTS: Final[dict[str, object]] = {
    "dither": "floyd_steinberg",
    "serpentine": False,
    "fit": "cover",
    "brightness": 1.0,
    "contrast": 1.0,
    "saturation": 1.0,
    "background": "white",
    "palette": "perceived",
}

EVENT_FRAME_WAKE: Final = f"{DOMAIN}_frame_wake"

IMAGE_PATH: Final = "/api/paperlessoffline/{token}/image.bmp"
SETTINGS_PATH: Final = "/api/paperlessoffline/{token}/settings.json"

# BLE
BLE_CHAR_DOWNLOAD_URL: Final = "10000001-0000-0000-0000-000000000001"
BLE_CHAR_IMAGE_MODE: Final = "10000002-0000-0000-0000-000000000001"
BLE_CHAR_COMMAND: Final = "10000004-0000-0000-0000-000000000001"
BLE_CHAR_TIMEOUT: Final = "10000005-0000-0000-0000-000000000001"
BLE_CHAR_AUTH_USER: Final = "10000007-0000-0000-0000-000000000001"
BLE_CHAR_AUTH_PASSWORD: Final = "10000008-0000-0000-0000-000000000001"
BLE_CHAR_MOTION_WAKEUP: Final = "10000009-0000-0000-0000-000000000001"
BLE_CHAR_CHARGER_MODE: Final = "1000000a-0000-0000-0000-000000000001"
BLE_CHAR_SETTINGS_URL: Final = "1000000b-0000-0000-0000-000000000001"
BLE_CHAR_AUTO_ROTATION: Final = "1000000c-0000-0000-0000-000000000001"
BLE_CHAR_TELEMETRY: Final = "1000000d-0000-0000-0000-000000000001"
BLE_CHAR_WIFI_CONNECTED: Final = "4c578d4c-7b0e-11ed-a1eb-0242ac120002"
BLE_CHAR_WIFI_INFO: Final = "4c578d4d-7b0e-11ed-a1eb-0242ac120002"
BLE_CHAR_SYSTEM_INFO: Final = "60000001-7b0e-11ed-a1eb-0242ac120002"
BLE_CHAR_WIFI_SSID: Final = "090b0ef2-7b0d-11ed-a1eb-0242ac120002"
BLE_CHAR_WIFI_PASSWORD: Final = "a62eed84-7b0d-11ed-a1eb-0242ac120002"


@dataclass(frozen=True)
class PanelSpec:
    """Physical panel description; width/height are the native buffer size."""

    key: str
    model: str
    width: int
    height: int
    default_mounting: str


PANELS: Final[dict[str, PanelSpec]] = {
    "epd7": PanelSpec("epd7", 'Paper 7 (7.3" Spectra 6)', 800, 480, "portrait"),
    "epd13": PanelSpec("epd13", 'Paper L (13.3" Spectra 6)', 1200, 1600, "portrait"),
}


def panel_from_client_id(client_id: str) -> PanelSpec | None:
    """Return the panel spec for a client id like ``epd7-aabbccddeeff``."""
    if (match := CLIENT_ID_RE.match(client_id)) is None:
        return None
    return PANELS[match.group(1)]


def mac_from_client_id(client_id: str) -> str | None:
    """Return the colon-separated MAC address embedded in a client id."""
    if (match := CLIENT_ID_RE.match(client_id)) is None:
        return None
    raw = match.group(2)
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2)).upper()
