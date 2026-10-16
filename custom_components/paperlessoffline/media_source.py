"""Browse frame libraries in the media browser."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.http.auth import async_sign_path
from homeassistant.components.media_player import BrowseError, MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .data import DATA_KEY

SIGN_EXPIRY = timedelta(hours=6)


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Set up the media source."""
    return FrameMediaSource(hass)


def preview_path(entry_id: str, photo_id: str) -> str:
    """Path of a photo's dithered preview."""
    return f"/api/{DOMAIN}/preview/{entry_id}/{photo_id}.png"


class FrameMediaSource(MediaSource):
    """Photos of each frame, shown as dithered previews."""

    name = "paperlesspaper frames"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise."""
        super().__init__(DOMAIN)
        self.hass = hass

    def _sign(self, path: str) -> str:
        return async_sign_path(self.hass, path, SIGN_EXPIRY)

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a photo to its preview URL."""
        entry_id, _, photo_id = (item.identifier or "").partition("/")
        data = self.hass.data.get(DATA_KEY)
        manager = data.entries.get(entry_id) if data else None
        if manager is None or manager.get_photo(photo_id) is None:
            raise Unresolvable("Unknown photo")
        return PlayMedia(self._sign(preview_path(entry_id, photo_id)), "image/png")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse frames and their photos."""
        data = self.hass.data.get(DATA_KEY)
        managers = data.entries if data else {}
        if not item.identifier:
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=None,
                media_class=MediaClass.DIRECTORY,
                media_content_type="",
                title=self.name,
                can_play=False,
                can_expand=True,
                children_media_class=MediaClass.DIRECTORY,
                children=[
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=entry_id,
                        media_class=MediaClass.DIRECTORY,
                        media_content_type="",
                        title=manager.display_name,
                        can_play=False,
                        can_expand=True,
                    )
                    for entry_id, manager in managers.items()
                ],
            )
        entry_id = item.identifier.split("/", 1)[0]
        if (manager := managers.get(entry_id)) is None:
            raise BrowseError("Unknown frame")
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=entry_id,
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title=manager.display_name,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.IMAGE,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{entry_id}/{photo.id}",
                    media_class=MediaClass.IMAGE,
                    media_content_type="image/png",
                    title=photo.name if photo.enabled else f"{photo.name} (disabled)",
                    can_play=True,
                    can_expand=False,
                    thumbnail=self._sign(f"/api/{DOMAIN}/thumb/{entry_id}/{photo.id}.jpg"),
                )
                for photo in manager.photos
            ],
        )
