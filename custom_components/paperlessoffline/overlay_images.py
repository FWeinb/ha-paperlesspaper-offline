"""Pictures of image overlays: fetching their source and keeping snapshots on disk."""

from __future__ import annotations

import contextlib
from pathlib import Path
import re

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .cache import touch
from .const import DOMAIN
from .sources import async_download, async_entity_image

# A wake waits this long for its pictures; previews and thumbnails less.
WAKE_TIMEOUT = 10
PREVIEW_TIMEOUT = 5
_ENTITY_RE = re.compile(r"^(camera|image)\.[a-z0-9_]+$")


async def async_fetch(hass: HomeAssistant, source: str) -> bytes:
    """Bytes of the picture an image overlay's evaluated source names.

    The source is a camera or image entity id, or an http(s) URL; anything
    else raises HomeAssistantError, as do a frame's own previews (drawing one
    renders the previews again). Callers limit how long it may take.
    """
    if _ENTITY_RE.match(source):
        if (entry := er.async_get(hass).async_get(source)) and entry.platform == DOMAIN:
            raise HomeAssistantError(f"A frame's own preview can't be drawn on a frame: {source}")
        try:
            return await async_entity_image(hass, source)
        except KeyError as err:
            raise HomeAssistantError(f"{source} not found") from err
    if source.startswith(("http://", "https://")):
        return await async_download(hass, source)
    raise HomeAssistantError(f"Not a camera or image entity or an http(s) URL: {source}")


class Snapshots:
    """Dithered pictures of image overlays, ``<id>.png``. Methods are blocking."""

    def __init__(self, directory: Path) -> None:
        """Initialise."""
        self.directory = directory

    def path(self, snapshot_id: str) -> Path:
        """Path of a snapshot."""
        return self.directory / f"{snapshot_id}.png"

    def has(self, snapshot_id: str) -> bool:
        """Whether a snapshot exists (a hit counts as a use)."""
        path = self.path(snapshot_id)
        if not path.is_file():
            return False
        touch(path)
        return True

    def put(self, snapshot_id: str, png: bytes) -> None:
        """Store a snapshot atomically."""
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.path(snapshot_id)
        tmp = path.with_suffix(".png.tmp")
        tmp.write_bytes(png)
        tmp.replace(path)

    def read(self, snapshot_id: str) -> bytes | None:
        """Read a snapshot, or None if it is gone."""
        path = self.path(snapshot_id)
        with contextlib.suppress(FileNotFoundError):
            data = path.read_bytes()
            touch(path)
            return data
        return None
